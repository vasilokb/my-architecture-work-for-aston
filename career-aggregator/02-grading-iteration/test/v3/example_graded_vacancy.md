# Пример результата грейдирования вакансии

## Формат итоговых данных (ориентир)

```json
{
  "vacancy": {
    "hh_id": "132120507",
    "job_title": "Системный аналитик",
    "overall_level": "senior",
    "salary_min": null,
    "salary_max": null,
    "is_remote": 0,
    "url": "https://hh.ru/vacancy/132120507"
  },
  "requirements": [
    {
      "competency": "SQL",
      "required_level": "middle",
      "is_mandatory": true,
      "confidence": 0.9,
      "evidence": "Знание SQL баз данных"
    },
    {
      "competency": "REST API",
      "required_level": "middle",
      "is_mandatory": true,
      "confidence": 0.85,
      "evidence": "проектирование API интерфейсов"
    },
    {
      "competency": "BPMN",
      "required_level": "senior",
      "is_mandatory": true,
      "confidence": 0.8,
      "evidence": "описание бизнес процессов BPMN"
    },
    {
      "competency": "Apache Kafka",
      "required_level": "middle",
      "is_mandatory": false,
      "confidence": 0.75,
      "evidence": "опыт работы с Kafka"
    }
  ]
}
```

## Пояснения

- **overall_level = senior** — потому что BPMN на уровне senior
- **is_mandatory** — true = обязательный навык, false = желательный
- **confidence** — уверенность LLM в анализе (0.0-1.0)
- **evidence** — цитата из текста вакансии подтверждающая навык

## Таблицы БД

- `parsed_vacancies` — вакансия (верхний уровень JSON)
- `parsed_requirements` — навыки (массив requirements)
- Связь через `parsed_vacancies.id = parsed_requirements.parsed_vacancy_id`
- Навык привязан к справочнику через `parsed_requirements.competency_id = competencies.id`

## SQL для проверки

```sql
-- Все вакансии с навыками
SELECT pv.hh_id, pv.job_title, pv.overall_level, c.name AS competency, pr.required_level, pr.is_mandatory, pr.confidence, pr.evidence
FROM parsed_vacancies pv
JOIN parsed_requirements pr ON pv.id = pr.parsed_vacancy_id
JOIN competencies c ON pr.competency_id = c.id
ORDER BY pv.id, c.name;
```
