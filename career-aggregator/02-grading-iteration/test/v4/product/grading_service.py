import re
import json
from sqlalchemy.orm import Session
from repositories.vacancy_repo import VacancyRepo
from repositories.competency_repo import CompetencyRepo
from repositories.parsed_repo import ParsedRepo
from ports.grading_provider import IGradingProvider
from ports.dictionary import IDictionary
from exceptions import GradingError

SENIOR_BOOST_CATEGORIES = {"Architecture", "Security", "Integration", "DevOps & CI/CD", "AI & Machine Learning"}

def _normalize_level(level: str) -> str:
    valid = {"junior", "middle", "senior", "lead", "expert"}
    if not level:
        return "middle"
    lvl = level.lower().strip()
    return lvl if lvl in valid else "middle"

def _calculate_overall_level(requirements_data: list[dict], categories_cache: dict) -> str:
    if not requirements_data:
        return "middle"
    level_score = {"junior": 1, "middle": 2, "senior": 3, "lead": 4, "expert": 5}
    max_score = 0
    has_senior = False
    has_lead = False
    boost = False
    for req in requirements_data:
        score = level_score.get(req["level"], 2)
        max_score = max(max_score, score)
        if req["level"] == "senior":
            has_senior = True
        elif req["level"] == "lead":
            has_lead = True
        if req["level"] == "senior":
            cats = categories_cache.get(req["competency_id"], [])
            if any(c in SENIOR_BOOST_CATEGORIES for c in cats):
                boost = True
    if has_lead:
        return "lead"
    if boost or has_senior:
        return "senior"
    if max_score >= 3:
        return "senior"
    if max_score >= 2:
        return "middle"
    return "junior"

def _clean_text(text: str) -> str:
    import re
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    for marker in [r'Мы предлагаем.*', r'Условия работы.*', r'Что мы предлагаем.*']:
        text = re.split(marker, text, flags=re.IGNORECASE | re.DOTALL)[0]
    return text.strip()

async def grade_vacancies(session: Session, provider: IGradingProvider, dictionary: IDictionary, limit: int = 100) -> dict:
    vacancy_repo = VacancyRepo(session)
    parsed_repo = ParsedRepo(session)
    competency_repo = CompetencyRepo(session)

    vacancies, _ = vacancy_repo.get_all_raw(page=1, limit=limit)
    vacancies = [v for v in vacancies if not parsed_repo.is_processed(v.id)]

    processed = 0
    failed = 0
    tree_text = dictionary.get_tree_text()

    for vac in vacancies:
        try:
            desc = f"{vac.requirement} {vac.responsibility}"
            user_content = (
                "Ты извлекаешь навыки из вакансий. Используй ТОЛЬКО компетенции из предоставленного списка. Возвращай только JSON.\n\n"
                f"Из представленного ниже списка компетенций выбери те, что явно упомянуты в тексте вакансии.\n\n"
                f"СПИСОК КОМПЕТЕНЦИЙ (ТОЛЬКО ИЗ ЭТОГО СПИСКА):\n{tree_text}\n\n"
                "ПРАВИЛА:\n1. Используй ТОЛЬКО id из списка выше\n2. НЕ придумывай новые названия\n3. НЕ добавляй то чего нет в списке\n"
                "4. Для каждой компетенции укажи level: junior/middle/senior, mandatory: true/false, confidence: 0.0-1.0, evidence: цитата из текста\n\n"
                'Верни ТОЛЬКО JSON-массив без пояснений: [{ "requirements": [{"id": 1, "level": "middle", "mandatory": true, "confidence": 0.9, "evidence": "цитата"}]}]\n\n'
                f"Вакансии:\n=== Вакансия 1 ===\nНазвание: {vac.name}\nОписание:\n{_clean_text(desc)}"
            )

            llm_response = provider.grade(user_content)
            json_match = re.search(r'\[[\s\S]*\]', llm_response)
            if json_match:
                llm_response = json_match.group(0)
            all_grades = json.loads(llm_response)
            grade_data = all_grades[0] if all_grades else {"requirements": []}

            from models.parsed import ParsedVacancy, ParsedRequirement
            from models.competency import Competency

            pv = ParsedVacancy(
                vacancy_id=vac.id, job_title=vac.name, overall_level="pending",
                salary_min=vac.salary_from, salary_max=vac.salary_to, currency=vac.salary_currency,
                is_remote=False, requirement_raw=vac.requirement, responsibility_raw=vac.responsibility,
                url=vac.url, status="completed",
            )

            reqs = []
            reqs_data = []
            comp_set = set()
            for cat in competency_repo.get_categories():
                for comp in cat.competencies:
                    comp_set.add(comp.id)

            cats_cache = {}
            for cat in competency_repo.get_categories():
                for comp in cat.competencies:
                    cats_cache[comp.id] = [cat.name]

            for req in grade_data.get("requirements", []):
                comp_id = int(req.get("id", 0))
                if comp_id not in comp_set:
                    continue
                level = _normalize_level(req.get("level"))
                pr = ParsedRequirement(
                    competency_id=comp_id, required_level=level,
                    is_mandatory=bool(req.get("mandatory", False)),
                    confidence=req.get("confidence", 1.0),
                    evidence=req.get("evidence", ""),
                )
                reqs.append(pr)
                reqs_data.append({"level": level, "competency_id": comp_id})

            overall = _calculate_overall_level(reqs_data, cats_cache) if reqs_data else "middle"
            pv.overall_level = overall
            parsed_repo.save_result(pv, reqs)
            session.commit()
            processed += 1
        except Exception as e:
            session.rollback()
            failed += 1

    return {"processed": processed, "failed": failed, "total": len(vacancies)}
