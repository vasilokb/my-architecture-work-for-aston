# MVP API Endpoints

## 1. Справочник компетенций (CRUD)

| Эндпоинт | Request Body | Response Body | Таблицы |
|---|---|---|---|
| `GET /api/competency-categories` | — | `[{ "id": 37, "name": "AI & Machine Learning" }, { "id": 38, "name": "Design (Нотации)" }, { "id": 39, "name": "UI & Prototyping" }, { "id": 40, "name": "Methodologies" }, { "id": 41, "name": "DevOps & CI/CD" }]` | `competency_categories` |
| `POST /api/competency-categories` | `{ "name": "New Category" }` | `{ "id": 42, "name": "New Category" }` | `competency_categories` |
| `PUT /api/competency-categories/{id}` | `{ "name": "Renamed" }` | `{ "id": 37, "name": "Renamed" }` | `competency_categories` |
| `DELETE /api/competency-categories/{id}` | — | `{ "deleted": true }` | `competency_categories` |
| `GET /api/competencies` | `?q=postgres&category_id=42` — поиск по имени, синонимам, категории | `[{ "id": 240, "name": "PostgreSQL", "category": { "id": 42, "name": "Data (OLTP)" }, "variants": ["postgres", "pg", "psql"] }, { "id": 239, "name": "MSSQL", "category": { "id": 42, "name": "Data (OLTP)" }, "variants": ["sql server", "ms sql"] }]` | `competencies`, `competency_categories`, `competency_category_link`, `competency_variants` |
| `GET /api/competencies/{id}` | — | `{ "id": 240, "name": "PostgreSQL", "category": { "id": 42, "name": "Data (OLTP)" }, "variants": ["postgres", "pg", "psql"] }` | `competencies`, `competency_categories`, `competency_category_link`, `competency_variants` |
| `GET /api/competencies/{id}/variants` | — | `[{ "id": 5, "competency_id": 240, "variant_name": "postgres" }, { "id": 6, "competency_id": 240, "variant_name": "pg" }]` | `competency_variants` |
| `POST /api/competencies` | `{ "name": "GraphQL", "category_ids": [42] }` | `{ "id": 305, "name": "GraphQL", "categories": [{ "id": 42, "name": "Data (OLTP)" }] }` | `competencies`, `competency_category_link` |
| `PUT /api/competencies/{id}` | `{ "name": "GraphQL API", "category_ids": [43] }` | `{ "id": 305, "name": "GraphQL API", "categories": [{ "id": 43, "name": "API Tools" }] }` | `competencies`, `competency_category_link` |
| `DELETE /api/competencies/{id}` | — | `{ "deleted": true }` | `competencies`, `competency_category_link`, `competency_variants` |
| `POST /api/competencies/{id}/variants` | `{ "variant_name": "pg" }` | `{ "id": 10, "competency_id": 240, "variant_name": "pg" }` | `competency_variants` |
| `PUT /api/competencies/{id}/variants/{variant_id}` | `{ "variant_name": "postgresql" }` | `{ "id": 5, "competency_id": 240, "variant_name": "postgresql" }` | `competency_variants` |
| `DELETE /api/competencies/{id}/variants/{variant_id}` | — | `{ "deleted": true }` | `competency_variants` |

---

## 2. Пайплайн: Извлечение вакансий (Scheduler → HH.ru)

| Эндпоинт | Request Body | Response Body | Таблицы |
|---|---|---|---|
| `POST /api/vacancies/extract` | `{ "query": "системный аналитик", "pages": 20 }` | `{ "task_id": "ext-20260511-001", "status": "running", "estimated": 1000 }` | `vacancies` (write) |
| `GET /api/vacancies/extract/status/{task_id}` | — | `{ "task_id": "ext-20260511-001", "status": "running", "loaded": 347, "failed": 2, "total": 1000 }` | — (memory) |
| `GET /api/vacancies/raw` | `?page=1&limit=50&q=аналитик` | `{ "items": [{ "id": 1, "hh_id": "131771794", "name": "Системный аналитик", "employer": "Russ", "city": "Москва", "salary_from": null, "salary_to": null, "salary_currency": null, "url": "https://hh.ru/vacancy/131771794", "graded": false }, { "id": 3, "hh_id": "132053577", "name": "Системный аналитик", "employer": "Розенталь Групп", "city": "Москва", "salary_from": 200000, "salary_to": 200000, "salary_currency": "RUR", "url": "https://hh.ru/vacancy/132053577", "graded": true }], "total": 1143, "page": 1, "limit": 50 }` | `vacancies`, `parsed_vacancies` (read) |
| `GET /api/vacancies/raw/{id}` | — | `{ "id": 1, "hh_id": "131771794", "name": "Системный аналитик", "requirement": "Обладаете знанием методологий анализа и проектирования систем...", "responsibility": "Направление работы: — Собирать и анализировать бизнес-требования...", "employer": "Russ", "city": "Москва", "salary_from": null, "salary_to": null, "salary_currency": null, "url": "https://hh.ru/vacancy/131771794" }` | `vacancies` (read) |
| `DELETE /api/vacancies/raw/{id}` | — | `{ "deleted": true }` | `vacancies` (delete) |

---

## 3. Пайплайн: Грейдирование + Просмотр результатов

| Эндпоинт | Request Body | Response Body | Таблицы |
|---|---|---|---|
| `POST /api/grading/run` | `{ "provider": "perplexity", "limit": 100 }` | `{ "task_id": "grd-20260511-001", "status": "running", "queued": 100 }` | `vacancies` (read), `competencies` (read), `competency_categories` (read), `competency_category_link` (read), `parsed_vacancies` (write), `parsed_requirements` (write) |
| `GET /api/grading/status/{task_id}` | — | `{ "task_id": "grd-20260511-001", "status": "running", "processed": 47, "failed": 3, "total": 100 }` | — (memory) |
| `GET /api/vacancies/graded` | `?page=1&limit=50&q=аналитик&level=middle` | `{ "items": [{ "id": 47, "hh_id": "132053577", "title": "Системный аналитик", "level": "middle", "salary_from": 200000, "salary_to": 200000, "salary_currency": "RUR", "skills_count": 9, "url": "https://hh.ru/vacancy/132053577" }, { "id": 46, "hh_id": "132071639", "title": "Системный аналитик", "level": "middle", "salary_from": null, "salary_to": null, "salary_currency": null, "skills_count": 3, "url": "https://hh.ru/vacancy/132071639" }], "total": 7, "page": 1, "limit": 50 }` | `parsed_vacancies` (read) |
| `GET /api/vacancies/graded/{id}` | — | `{ "id": 47, "hh_id": "132053577", "title": "Системный аналитик", "level": "middle", "salary_from": 200000, "salary_to": 200000, "salary_currency": "RUR", "requirement": "Опыт работы системным аналитиком от 3 лет...", "responsibility": "Backend — Go, PHP. Frontend – React...", "url": "https://hh.ru/vacancy/132053577" }` | `parsed_vacancies` (read) |
| `GET /api/vacancies/graded/{id}/skills` | — | `[{ "competency_id": 245, "name": "Go", "level": "middle", "mandatory": true, "confidence": 1.0, "evidence": "Backend — Go" }, { "competency_id": 246, "name": "PHP", "level": "middle", "mandatory": true, "confidence": 1.0, "evidence": "Backend — Go, PHP" }, { "competency_id": 248, "name": "Kotlin", "level": "middle", "mandatory": true, "confidence": 1.0, "evidence": "Mobile – Swift, Kotlin" }, { "competency_id": 240, "name": "PostgreSQL", "level": "middle", "mandatory": true, "confidence": 1.0, "evidence": "Infra – PostgreSQL" }, { "competency_id": 241, "name": "Docker", "level": "middle", "mandatory": true, "confidence": 1.0, "evidence": "Infra – PostgreSQL, Docker" }]` | `parsed_requirements`, `competencies` (read) |
