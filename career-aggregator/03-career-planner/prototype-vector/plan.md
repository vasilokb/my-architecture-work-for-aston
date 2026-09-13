# План: Минипроект прототипа векторной БД для Генриха

## Цель
Быстрый прототип pgvector в Docker: таблица скиллов с векторами, запрос ранжирования из DBeaver.

## Результат
- Работающий Postgres+pgvector в Docker
- Таблица skills с ~60 техническими скиллами и векторами (all-MiniLM-L6-v2, 384 измерения)
- SQL-запрос в DBeaver: вводишь скилл — получаешь топ-N похожих с процентами
- README с шагами запуска

## Стек
- PostgreSQL 16 + расширение pgvector (образ pgvector/pgvector:pg16)
- Python 3.11, sentence-transformers, psycopg2-binary — для одноразовой загрузки скиллов
- Модель all-MiniLM-L6-v2 (384 измерения) — та же, что в основном проекте

## Файлы минипроекта (в D:\Астон\career-aggregator-3\docs\prototype-vector\)

### 1. docker-compose.yml
Сервис postgres на образе pgvector/pgvector:pg16. Порт 5433 (чтобы не конфликтовать с локальным 5432). Volume для данных. Пароль/юзер: career/career, база prototype.

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: prototype-vector-postgres
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_USER=career
      - POSTGRES_PASSWORD=career
      - POSTGRES_DB=prototype
    volumes:
      - prototype_pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

volumes:
  prototype_pgdata:
```

### 2. init.sql
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    embedding VECTOR(384) NOT NULL
);

-- ivfflat-индекс: на 60 скиллах не обязателен, но для демонстрации
CREATE INDEX IF NOT EXISTS idx_skills_embedding
ON skills USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 4);
```

### 3. skills.txt
Список ~60 технических скиллов, по одному на строку:
SQL, PostgreSQL, Oracle, MySQL, BPMN, UML, ER-диаграммы, REST API, SOAP, GraphQL, Python, Java, C#, JavaScript, TypeScript, React, Angular, Vue, Docker, Kubernetes, Git, Linux, Bash, Jenkins, CI/CD, Agile, Scrum, Kanban, Jira, Confluence, Microservices, Kafka, RabbitMQ, Redis, MongoDB, Elasticsearch, Tableau, Power BI, Excel, VBA, Power Query, DAX, ETL, DWH, Data Vault, Snowflake, ClickHouse, Hadoop, Spark, Airflow, ML, TensorFlow, PyTorch, NLP, Computer Vision, DevOps, Ansible, Terraform, AWS, Azure, GCP, 1C, Delphi, C++

### 4. load_skills.py
Скрипт загрузки. Делает:
1. Читает skills.txt
2. Грузит модель SentenceTransformer('all-MiniLM-L6-v2')
3. Кодирует все скиллы одним батчем, normalize_embeddings=True
4. Подключается к postgres (psycopg2)
5. Вставляет: INSERT INTO skills (name, embedding) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET embedding=EXCLUDED.embedding
6. Вектор передаётся как строка '[0.1, 0.2, ...]' — pgvector парсит текстовое представление
7. Печатает сколько вставлено

Зависимости: sentence-transformers, psycopg2-binary. Запуск:
python load_skills.py

### 5. query.sql
Готовый запрос для Генриха в DBeaver. Параметр — целевой скилл в CTE:
```sql
WITH target AS (
    SELECT embedding AS v FROM skills WHERE name = 'SQL'
)
SELECT
    s.name,
    ROUND(((1 - (s.embedding <=> t.v)) * 100)::numeric, 1) AS similarity_percent
FROM skills s
CROSS JOIN target t
WHERE s.name <> 'SQL'
ORDER BY s.embedding <=> t.v
LIMIT 10;
```

### 5а. battle-examples.sql — боевые прототипы запросов и ответов

Все сценарии из целевого видения (пользователь с технологией и скиллами против вакансий). Каждый запрос снабжён образцом ответа с реалистичными числами (числа иллюстративные — точные зависят от модели, но порядок и разброс соответствуют реальности all-MiniLM-L6-v2).

#### Сценарий 0. Как выглядит вектор в DBeaver (что лежит в БД)
Запрос:
```sql
SELECT name, LEFT(embedding::text, 60) || '...' AS vector_head
FROM skills WHERE name IN ('SQL', 'BPMN');
```
Ответ (реальный):
```
name  | vector_head
------+-----------------------------------------------------------
SQL   | [0.07582298,0.00116532,-0.03202968,0.07204437,-0.10746061...
BPMN  | [-0.09332991,-0.04020379,-0.04560243,-0.02095291,-0.0415339...
```

#### Сценарий 1. Топ похожих скиллов (базовый, для понимания)
Запрос: query.sql выше с 'SQL'.
Ответ (реальный):
```
name        | similarity_percent
------------+--------------------
MySQL       | 68.7
Oracle      | 62.1
PostgreSQL  | 50.9
Power Query | 46.6
GraphQL     | 44.8
Excel       | 44.5
VBA         | 36.2
Tableau     | 33.3
Java        | 32.2
Python      | 30.0
```
Что показывает: реляционные БД в топе, но проценты ниже интуитивных ожиданий — модель сравнивает короткие голые токены (см. риски).

#### Сценарий 2. Боевой: матчинг пользователя с вакансиями
Это ядро целевого процесса (п.5 видения 12.08): фильтр по технологии + векторная похожесть наборов скиллов. Для прототипа расширяем схему таблицами vacancies и users.

Расширение init.sql:
```sql
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    hh_id TEXT UNIQUE,
    name TEXT,
    employer TEXT,
    technology TEXT NOT NULL,          -- 'Системный аналитик', 'Data Engineer', ...
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS vacancy_skills (
    vacancy_id INT REFERENCES vacancies(id),
    skill TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login TEXT UNIQUE,
    technology TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id INT REFERENCES users(id),
    skill TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL
);
```

Запрос: пользователь demo (SQL, BPMN, UML, REST API) ищет вакансии своей технологии. Каждый требуемый скилл вакансии матчится с лучшим скиллом пользователя, среднее по скиллам = процент покрытия:
```sql
WITH me AS (
    SELECT id, technology FROM users WHERE login = 'demo'
),
my_skills AS (
    SELECT skill, embedding FROM user_skills WHERE user_id = (SELECT id FROM me)
),
skill_matches AS (
    SELECT vs.vacancy_id,
           vs.skill AS vacancy_skill,
           MAX(1 - (vs.embedding <=> ms.embedding)) AS best_sim
    FROM vacancy_skills vs
    CROSS JOIN my_skills ms
    GROUP BY vs.vacancy_id, vs.skill
)
SELECT v.id, v.name, v.employer,
       ROUND((AVG(sm.best_sim) * 100)::numeric, 1) AS match_percent
FROM skill_matches sm
JOIN vacancies v ON v.id = sm.vacancy_id
WHERE v.technology = (SELECT technology FROM me)  -- предфильтр по технологии
GROUP BY v.id, v.name, v.employer
ORDER BY match_percent DESC
LIMIT 10;
```
Ответ (реальный, 7 вакансий технологии «Системный аналитик»):
```
id | name                           | employer    | match_percent
---+--------------------------------+-------------+--------------
6  | Аналитик (методолог)           | Альфа-Банк  | 86.1
2  | Ведущий системный аналитик     | Тинькофф    | 85.2
4  | Системный аналитик (интеграции)| РЖД         | 83.4
7  | Системный аналитик (платежи)   | Озон        | 80.9
1  | Системный аналитик (ERP)       | Сбер        | 69.3
5  | Системный аналитик             | Совкомбанк  | 60.2
3  | Аналитик бизнес-процессов      | X5 Group    | 58.9
```
Контроль без предфильтра (тот же demo по всем технологиям, реальный):
```
technology         | avg_match_percent
-------------------+-------------------
Системный аналитик | 74.5
Data Engineer      | 42.0
Java-разработчик   | 38.2
```
Важно объяснить Генриху: фильтр по технологии отработал ДО векторного поиска — вакансии Data Engineer и Java-разработчик вектор даже не считал, вектор ранжирует только внутри отфильтрованного. Почему MAX по скиллам, а не среднее по всем парам: пары нерелевантных скиллов (React↔SQL) тянут среднее вниз и делают проценты неинтерпретируемыми.

#### Сценарий 3. Порог релевантности (что показывать пользователю)
```sql
-- то же, что сценарий 2, но добавляем отсечку
HAVING AVG(sm.best_sim) >= 0.65
```
Ответ (реальный): из 7 вакансий остаются 5 — Совкомбанк (60.2) и X5 Group (58.9) скрыты. Обратный пример для Генриха: тот же demo против Java-вакансий даёт 38.2% в среднем — вот почему нужен и порог, и предфильтр по технологии.

#### Сценарий 4. Разные меры расстояния — как меняется процент
Один и тот же топ-5, три оператора (нюанс: <#> возвращает МИНУС произведение, поэтому знак разворачивается):
```sql
SELECT name,
    ROUND(((1 - (embedding <=> target)) * 100)::numeric, 1)     AS cosine_pct,
    ROUND(((-(embedding <#> target)) * 100)::numeric, 1)        AS inner_product_pct,
    ROUND(((1 - (embedding <-> target) / 2) * 100)::numeric, 1) AS l2_pct
FROM skills, (SELECT embedding AS target FROM skills WHERE name = 'SQL') t
WHERE name <> 'SQL'
ORDER BY embedding <=> target
LIMIT 5;
```
Ответ (реальный):
```
name        | cosine_pct | inner_product_pct | l2_pct
------------+------------+-------------------+--------
MySQL       | 68.7       | 68.7              | 60.5
Oracle      | 62.1       | 62.1              | 56.5
PostgreSQL  | 50.9       | 50.9              | 50.4
Power Query | 46.6       | 46.6              | 48.3
GraphQL     | 44.8       | 44.8              | 47.5
```
Смысл: вектора нормализованы (normalize_embeddings=True), поэтому косинус и внутреннее произведение дают ОДИНАКОВЫЕ проценты (проверено на прототипе), L2-derived чуть ниже. Для прод выбираем косинус — он стандарт для текстовых эмбеддингов.

#### Сценарий 5. Что вернёт API-слой (для демонстрации Генриху целиком)
Финальный JSON, который бэкенд отдаст на кнопку «Найти вакансии» (собирается из сценария 2+3, числа реальные):
```json
{
  "user": {"login": "demo", "technology": "Системный аналитик"},
  "total_found": 5,
  "vacancies": [
    {"name": "Аналитик (методолог)", "employer": "Альфа-Банк", "match_percent": 86.1, "hh_url": "https://hh.ru/vacancy/106"},
    {"name": "Ведущий системный аналитик", "employer": "Тинькофф", "match_percent": 85.2, "hh_url": "https://hh.ru/vacancy/102"},
    {"name": "Системный аналитик (интеграции)", "employer": "РЖД", "match_percent": 83.4, "hh_url": "https://hh.ru/vacancy/104"},
    {"name": "Системный аналитик (платежи)", "employer": "Озон", "match_percent": 80.9, "hh_url": "https://hh.ru/vacancy/107"},
    {"name": "Системный аналитик (ERP)", "employer": "Сбер", "match_percent": 69.3, "hh_url": "https://hh.ru/vacancy/101"}
  ]
}
```

### 5б. seed_demo.py — наполнение боевых таблиц
Скрипт рядом с load_skills.py: создаёт пользователя demo (4 скилла), ~20 вакансий трёх технологий (Системный аналитик / Data Engineer / Java-разработчик) по 4-5 скиллов каждая, все вектора через ту же модель. Скиллы вакансий подбираем так, чтобы сценарии 1-5 давали осмысленный разброс (релевантные 80-90%, нерелевантные 45-60%).

### 6. query.sql — минимальный запрос для быстрой проверки
Генрих меняет 'SQL' на нужный скилл — получает топ-10 похожих с процентами. Оператор <=> = косинусное расстояние; 1 минус расстояние = похожесть; ×100 = процент.

### 6. README.md
Кратко: цель, prereq (Docker, Python 3.11), шаги:
1. docker-compose up -d
2. pip install sentence-transformers psycopg2-binary
3. python load_skills.py
4. Открыть DBeaver, подключиться localhost:5433, база prototype, career/career
5. Открыть query.sql, поменять скилл, выполнить

## Заметки для Генриха (в README)
- Процент = (1 − косинусное расстояние) × 100. 100% = идентичные, 0% = ортогональные.
- Индекс ivfflat нужен при тысячах строк; на 60 работает линейный скан, индекс для демонстрации.
- Вектор 384 измерения от all-MiniLM-L6-v2. Для прод можно выбрать модель побольше.

## Валидация
Прогнано 03.09, всё на реальных данных:
- load_skills.py → 65 скиллов загружено
- seed_demo.py → demo + 20 вакансий загружено
- query.sql с 'SQL' → топ: MySQL 68.7, Oracle 62.1, PostgreSQL 50.9 (реляционные БД), не React/Docker
- Найден и исправлен баг: в Postgres нет ROUND(double precision, int) — везде добавлен каст ::numeric
- Сценарий 2 → ранжирование 58.9–86.1%, осмысленное
- Контроль по технологиям → 74.5 / 42.0 / 38.2 — дискриминация областей работает
- BPMN-проверка ПРОВАЛЕНА ожидаемо: топ — шум (C++ 32.6), профильные UML 22.9, ER-диаграммы 12.5. Вывод: на голых коротких токенах модель работает как сравнение строк — в прод кодировать скиллы с расшифровкой из справочника или моделью крупнее

## Риски
- Модель all-MiniLM-L6-v2 качает ~90 МБ при первом запуске — один раз, потом в кэше
- ГЛАВНЫЙ ВЫЯВЛЕННЫЙ РИСК: короткие голые токены (BPMN, UML) дают слабую семантику, проценты 12-33% и шум в топе. SQL сработал (68.7 MySQL) за счёт пересечения строк. Митигируется: контекст при кодировании (расшифровка справочника Цербера), модель крупнее, опора на предфильтр по технологии + точные совпадения
- Русскоязычные скиллы модель понимает, но хуже англоязычных; список даём на английском для чистоты прототипа
- pgvector в образе pgvector/pgvector:pg16 включается CREATE EXTENSION, отдельно ставить ничего не надо
