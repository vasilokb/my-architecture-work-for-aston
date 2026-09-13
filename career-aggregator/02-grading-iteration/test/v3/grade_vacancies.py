import os
import sqlite3
import json
import re
import time
from perplexity import Perplexity

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import os
API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

CONFIG = {
    'retry_attempts': 3,
    'retry_base_delay': 10,
    'delay_between_batches': 10,
    'rate_limit_requests_per_minute': 10,
}

client = Perplexity(api_key=API_KEY)

conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

COMPETENCY_TREE = []
COMPETENCY_SET = set()
COMPETENCY_NAMES = {}

cursor.execute('''
    SELECT cc.name, c.id, c.name
    FROM competency_categories cc
    JOIN competency_category_link cl ON cc.id = cl.category_id
    JOIN competencies c ON cl.competency_id = c.id
    ORDER BY cc.name, c.name
''')

rows = cursor.fetchall()
current_group = None
for group_name, comp_id, comp_name in rows:
    if group_name != current_group:
        COMPETENCY_TREE.append(f"\n{group_name}:")
        current_group = group_name
    COMPETENCY_TREE.append(f"    {comp_id}. {comp_name}")
    COMPETENCY_SET.add(comp_id)
    COMPETENCY_NAMES[comp_id] = comp_name

COMPETENCY_TREE_TEXT = "\n".join(COMPETENCY_TREE)
print(f"Загружено компетенций: {len(COMPETENCY_SET)}")

COMPETENCY_CATEGORIES_CACHE = {}
cursor.execute("""
    SELECT cl.competency_id, c.name
    FROM competency_category_link cl
    JOIN competency_categories c ON cl.category_id = c.id
""")
for row in cursor.fetchall():
    comp_id = row[0]
    cat_name = row[1]
    if comp_id not in COMPETENCY_CATEGORIES_CACHE:
        COMPETENCY_CATEGORIES_CACHE[comp_id] = []
    COMPETENCY_CATEGORIES_CACHE[comp_id].append(cat_name)

SENIOR_BOOST_CATEGORIES = {'Architecture', 'Security', 'Integration', 'DevOps & CI/CD', 'AI & Machine Learning'}

def normalize_level(level):
    valid = {'junior', 'middle', 'senior', 'lead', 'expert'}
    if not level:
        return 'middle'
    lvl = level.lower().strip()
    return lvl if lvl in valid else 'middle'

def calculate_overall_level(requirements_data):
    if not requirements_data:
        return 'middle'
    level_score = {'junior': 1, 'middle': 2, 'senior': 3, 'lead': 4, 'expert': 5}
    max_score = 0
    has_senior_skill = False
    has_lead_skill = False
    boost_to_senior = False
    for req in requirements_data:
        lvl = req['level']
        score = level_score.get(lvl, 2)
        max_score = max(max_score, score)
        if lvl == 'senior':
            has_senior_skill = True
        elif lvl == 'lead':
            has_lead_skill = True
        if lvl == 'senior':
            comp_id = req['competency_id']
            cats = COMPETENCY_CATEGORIES_CACHE.get(comp_id, [])
            if any(cat in SENIOR_BOOST_CATEGORIES for cat in cats):
                boost_to_senior = True
    if has_lead_skill:
        return 'lead'
    if boost_to_senior or has_senior_skill:
        return 'senior'
    if max_score >= 3:
        return 'senior'
    if max_score >= 2:
        return 'middle'
    return 'junior'

class RateLimiter:
    def __init__(self, requests_per_minute):
        self.interval = 60.0 / requests_per_minute
        self.last_request_time = 0
    def wait(self):
        now = time.time()
        if now - self.last_request_time < self.interval:
            wait = self.interval - (now - self.last_request_time)
            print(f"      Rate limit: {wait:.1f} sec")
            time.sleep(wait)
        self.last_request_time = time.time()

rate_limiter = RateLimiter(CONFIG['rate_limit_requests_per_minute'])

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    cut_markers = [
        r'Мы предлагаем.*',
        r'Условия работы.*',
        r'Что мы предлагаем.*',
        r'Бонусы и компенсации.*',
        r'Наши преимущества.*'
    ]
    for marker in cut_markers:
        text = re.split(marker, text, flags=re.IGNORECASE | re.DOTALL)[0]
    return text.strip()

def grade_vacancy_batch(vacancies_data):
    if not vacancies_data:
        return False

    batch_text = ""
    vac_infos = []
    for i, vac in enumerate(vacancies_data, 1):
        text = f"Название: {vac['name']}\nОписание:\n{vac['description']}"
        batch_text += f"\n=== Вакансия {i} ===\n{clean_text(text)}\n"
        vac_infos.append(vac)

    user_content = (
        "Ты извлекаешь навыки из вакансий. Используй ТОЛЬКО компетенции из предоставленного списка. Возвращай только JSON.\n\n"
        f"Из представленного ниже списка компетенций выбери те, что явно упомянуты в тексте вакансии.\n\n"
        f"СПИСОК КОМПЕТЕНЦИЙ (ТОЛЬКО ИЗ ЭТОГО СПИСКА):\n{COMPETENCY_TREE_TEXT}\n\n"
        "ПРАВИЛА:\n"
        "1. Используй ТОЛЬКО id из списка выше\n"
        "2. НЕ придумывай новые названия\n"
        "3. НЕ добавляй то чего нет в списке\n"
        "4. Для каждой компетенции укажи level: junior/middle/senior, mandatory: true/false, confidence: 0.0-1.0, evidence: цитата из текста\n\n"
        "Верни ТОЛЬКО JSON-массив без пояснений:\n"
        '[\n  {\n    "requirements": [\n      {"id": 1, "level": "middle", "mandatory": true, "confidence": 0.9, "evidence": "цитата"}\n    ]\n  }\n]\n\n'
        f"Вакансии:\n{batch_text}"
    )

    for attempt in range(CONFIG['retry_attempts']):
        try:
            rate_limiter.wait()
            completion = client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )
            llm_response = completion.choices[0].message.content

            json_match = re.search(r'\[[\s\S]*\]', llm_response)
            if json_match:
                llm_response = json_match.group(0)

            all_grades = json.loads(llm_response)

            conn.execute("BEGIN")
            for idx, grade_data in enumerate(all_grades):
                if idx < len(vac_infos):
                    insert_parsed_data(vac_infos[idx], grade_data.get('requirements', []))
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            wait_time = CONFIG['retry_base_delay'] * (2 ** attempt)
            print(f"      Попытка {attempt+1} не удалась: {e}")
            if attempt < CONFIG['retry_attempts'] - 1:
                time.sleep(wait_time)
    return False

def insert_parsed_data(vac_data, requirements):
    cursor.execute("SELECT id FROM parsed_vacancies WHERE hh_id = ?", (vac_data['hh_id'],))
    if cursor.fetchone():
        print(f"      Вакансия {vac_data['hh_id']} уже обработана, пропуск")
        return

    cursor.execute('''
        INSERT INTO parsed_vacancies (
            hh_id, job_title, overall_level,
            salary_min, salary_max, currency,
            is_remote, requirement_raw, responsibility_raw,
            url, status, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
    ''', (
        vac_data['hh_id'],
        vac_data['name'],
        'pending',
        vac_data['salary_from'],
        vac_data['salary_to'],
        vac_data['salary_currency'],
        vac_data['is_remote'],
        vac_data['description'],
        vac_data['description'],
        vac_data['url']
    ))
    parsed_id = cursor.lastrowid

    requirements_data = []
    for req in requirements:
        comp_id = req.get('id')
        try:
            comp_id = int(comp_id)
        except (TypeError, ValueError):
            print(f"      LLM вернул невалидный id '{comp_id}', пропуск")
            continue
        if comp_id not in COMPETENCY_SET:
            print(f"      LLM вернул неизвестный id {comp_id}, пропуск")
            continue
        level = normalize_level(req.get('level'))
        is_mandatory = 1 if req.get('mandatory', False) else 0
        confidence = req.get('confidence', 1.0)
        evidence = req.get('evidence', '')
        cursor.execute('''
            INSERT INTO parsed_requirements (
                parsed_vacancy_id, competency_id, required_level, is_mandatory, confidence, evidence
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (parsed_id, comp_id, level, is_mandatory, confidence, evidence))
        requirements_data.append({
            'level': level,
            'competency_id': comp_id
        })

    overall = calculate_overall_level(requirements_data) if requirements_data else 'middle'
    cursor.execute("UPDATE parsed_vacancies SET overall_level = ? WHERE id = ?", (overall, parsed_id))
    print(f"      OK {vac_data['hh_id']}: {overall}, {len(requirements_data)} skills")

def grade_all_vacancies():
    print("1. Загружаем вакансии из базы данных...")
    cursor.execute('''
        SELECT v.hh_id, v.name, v.requirement, v.responsibility, v.url,
               v.salary_from, v.salary_to, v.salary_currency
        FROM vacancies v
        LEFT JOIN parsed_vacancies pv ON v.hh_id = pv.hh_id
        WHERE pv.id IS NULL
        ORDER BY v.id
        LIMIT 10
    ''')
    rows = cursor.fetchall()
    print(f"   Новых вакансий для грейдирования: {len(rows)}")

    if not rows:
        print("   Нет новых вакансий. Выход.")
        return

    full_vacancies = []
    for row in rows:
        full_vacancies.append({
            'hh_id': row[0],
            'name': row[1],
            'description': f"{row[2]} {row[3]}",
            'url': row[4],
            'salary_from': row[5],
            'salary_to': row[6],
            'salary_currency': row[7],
            'is_remote': 0
        })

    print(f"2. Грейдирование: {len(full_vacancies)} вакансий...")
    consecutive_failures = 0
    max_consecutive_failures = 3
    for i, vac in enumerate(full_vacancies, 1):
        print(f"\n   [{i}/{len(full_vacancies)}] {vac['name']} ({vac['hh_id']})...")
        success = grade_vacancy_batch([vac])
        if not success:
            consecutive_failures += 1
            print(f"      FAIL ({consecutive_failures}/{max_consecutive_failures})")
            if consecutive_failures >= max_consecutive_failures:
                print(f"\n   {max_consecutive_failures} fails - API unavailable. Stop.")
                break
        else:
            consecutive_failures = 0
        time.sleep(CONFIG['delay_between_batches'])

    print("   Done.")

def main():
    print("Запуск грейдирования вакансий")
    print(f"   Справочник компетенций: {len(COMPETENCY_SET)}")
    grade_all_vacancies()

    cursor.execute("SELECT COUNT(*) FROM parsed_vacancies")
    cnt = cursor.fetchone()[0]
    print(f"\n   Всего обработанных вакансий: {cnt}")

    conn.close()
    print("\nDONE.")

if __name__ == "__main__":
    main()
