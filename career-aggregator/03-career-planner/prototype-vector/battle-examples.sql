-- ============================================================================
-- БОЕВЫЕ ПРИМЕРЫ ЗАПРОСОВ И ОТВЕТОВ (pgvector)
-- Перед выполнением: docker-compose up -d; python load_skills.py; python seed_demo.py
-- Все ответы ниже — РЕАЛЬНЫЕ, снятые с работающего прототипа
-- (модель all-MiniLM-L6-v2, 95 скиллов, 20 вакансий, демо-пользователь demo).
-- ВАЖНО: везде каст ::numeric — в Postgres нет ROUND(double precision, int),
-- а операторы расстояния возвращают именно double.
-- ============================================================================

-- ============================================================================
-- ГЛАВНЫЙ ЗАПРОС: вакансия, компания, скиллы, процент.
-- Меняются только две строки ВХОД.
-- ============================================================================
WITH input AS (
    SELECT 'Системный аналитик' AS position,               -- ВХОД: позиция
           ARRAY['SQL','BPMN','UML','REST API'] AS skills  -- ВХОД: скиллы
),
my AS (
    SELECT s.name, s.embedding
    FROM skills s JOIN input i ON s.name = ANY (i.skills)
),
m AS (
    SELECT vs.vacancy_id, vs.skill,
           MAX(1 - (vs.embedding <=> my.embedding)) AS best
    FROM vacancy_skills vs CROSS JOIN my
    GROUP BY vs.vacancy_id, vs.skill
)
SELECT v.name AS vacancy,
       v.employer AS company,
       STRING_AGG(m.skill, ', ' ORDER BY m.skill) AS skills,
       ROUND((AVG(m.best) * 100)::numeric, 1) AS match_percent
FROM m JOIN vacancies v ON v.id = m.vacancy_id CROSS JOIN input i
WHERE v.technology = i.position
GROUP BY v.id, v.name, v.employer
ORDER BY match_percent DESC;
-- РЕАЛЬНЫЙ ОТВЕТ:
-- vacancy                          | company    | skills                                                              | match_percent
-- ---------------------------------+------------+---------------------------------------------------------------------+--------------
-- Аналитик (методолог)             | Альфа-Банк | BPMN, Excel, SQL, UML, Use Case, User Story                         | 67.2
-- Ведущий системный аналитик       | Тинькофф   | Agile, BPMN, OpenAPI, Postman, REST API, SQL, Swagger, UML          | 65.1
-- Системный аналитик (интеграции)  | РЖД        | JSON, REST API, SOAP, SQL, Swagger, UML, XML                        | 63.6
-- Системный аналитик (платежи)     | Озон       | ArchiMate, BPMN, Camunda, Confluence, REST API, SQL                 | 61.2
-- Системный аналитик (ERP)         | Сбер       | BPMN, Confluence, Jira, SQL, UML, Use Case, Visio                   | 57.2
-- Аналитик бизнес-процессов        | X5 Group   | Agile, BPMN, Celonis, Confluence, Excel, Process Mining, UML, Visio | 48.5
-- Системный аналитик               | Совкомбанк | BPMN, DFD, ER-диаграммы, IDEF0, Jira, SQL                           | 48.4

-- ---------------------------------------------------------------------------
-- Сценарий 0. Как выглядит вектор в DBeaver (что лежит в БД)
-- ---------------------------------------------------------------------------
SELECT name, LEFT(embedding::text, 60) || '...' AS vector_head
FROM skills WHERE name IN ('SQL', 'BPMN');
-- РЕАЛЬНЫЙ ОТВЕТ:
-- name  | vector_head
-- ------+-----------------------------------------------------------
-- SQL   | [0.07582298,0.00116532,-0.03202968,0.07204437,-0.10746061...
-- BPMN  | [-0.09332991,-0.04020379,-0.04560243,-0.02095291,-0.0415339...

-- ---------------------------------------------------------------------------
-- Сценарий 1. Топ похожих скиллов (базовый)
-- ---------------------------------------------------------------------------
WITH target AS (
    SELECT embedding AS v FROM skills WHERE name = 'SQL'
)
SELECT s.name,
       ROUND(((1 - (s.embedding <=> t.v)) * 100)::numeric, 1) AS similarity_percent
FROM skills s
CROSS JOIN target t
WHERE s.name <> 'SQL'
ORDER BY s.embedding <=> t.v
LIMIT 10;
-- РЕАЛЬНЫЙ ОТВЕТ:
-- name         | similarity_percent
-- -------------+--------------------
-- MySQL        | 68.7
-- Oracle       | 62.1
-- PostgreSQL   | 50.9
-- Power Query  | 46.6
-- GraphQL      | 44.8
-- Excel        | 44.5
-- Google Sheets| 44.3
-- VBA          | 36.2
-- Tableau      | 33.3
-- Java         | 32.2
-- СУТЬ: MySQL/Oracle/PostgreSQL в топе. Проценты ниже, чем ждут неспециалисты,
-- потому что модель сравнивает короткие голые токены. Для прод скиллы надо
-- кодировать с контекстом (см. «Ограничение» в конце файла).

-- ---------------------------------------------------------------------------
-- Сценарий 2. Контроль: демо-пользователь против ВСЕХ технологий (без предфильтра)
-- ---------------------------------------------------------------------------
WITH me AS (
    SELECT id, technology FROM users WHERE login = 'demo'
),
my_skills AS (
    SELECT skill, embedding FROM user_skills WHERE user_id = (SELECT id FROM me)
),
skill_matches AS (
    SELECT vs.vacancy_id,
           MAX(1 - (vs.embedding <=> ms.embedding)) AS best_sim
    FROM vacancy_skills vs
    CROSS JOIN my_skills ms
    GROUP BY vs.vacancy_id, vs.skill
)
SELECT v.technology,
       ROUND((AVG(sm.best_sim) * 100)::numeric, 1) AS avg_match_percent
FROM skill_matches sm
JOIN vacancies v ON v.id = sm.vacancy_id
GROUP BY v.technology
ORDER BY avg_match_percent DESC;
-- РЕАЛЬНЫЙ ОТВЕТ:
-- technology         | avg_match_percent
-- -------------------+-------------------
-- Системный аналитик | 58.7
-- Data Engineer      | 42.0
-- Java-разработчик   | 38.2
-- СУТЬ: даже без предфильтра вектор различает области на 15-20 пунктов,
-- но 38-42% по чужой технологии — это всё ещё «какие-то проценты»,
-- поэтому предфильтр + порог нужны оба.

-- ---------------------------------------------------------------------------
-- Сценарий 3. Порог релевантности (что показывать пользователю)
-- То же, что главный запрос, но вакансии с покрытием ниже 55% скрываются.
-- ---------------------------------------------------------------------------
WITH me AS (
    SELECT id, technology FROM users WHERE login = 'demo'
),
my_skills AS (
    SELECT skill, embedding FROM user_skills WHERE user_id = (SELECT id FROM me)
),
skill_matches AS (
    SELECT vs.vacancy_id,
           MAX(1 - (vs.embedding <=> ms.embedding)) AS best_sim
    FROM vacancy_skills vs
    CROSS JOIN my_skills ms
    GROUP BY vs.vacancy_id, vs.skill
)
SELECT v.id, v.name, v.employer,
       ROUND((AVG(sm.best_sim) * 100)::numeric, 1) AS match_percent
FROM skill_matches sm
JOIN vacancies v ON v.id = sm.vacancy_id
WHERE v.technology = (SELECT technology FROM me)
GROUP BY v.id, v.name, v.employer
HAVING AVG(sm.best_sim) >= 0.55
ORDER BY match_percent DESC;
-- РЕАЛЬНЫЙ ОТВЕТ: из 7 вакансий остались 5:
-- Аналитик (методолог) 67.2 / Ведущий системный аналитик 65.1 /
-- Системный аналитик (интеграции) 63.6 / Системный аналитик (платежи) 61.2 /
-- Системный аналитик (ERP) 57.2. Скрыты: Аналитик бизнес-процессов 48.5,
-- Системный аналитик (Совкомбанк) 48.4.

-- ---------------------------------------------------------------------------
-- Сценарий 4. Разные меры расстояния — как меняется процент
-- ---------------------------------------------------------------------------
SELECT s.name,
       ROUND(((1 - (s.embedding <=> t.v)) * 100)::numeric, 1)     AS cosine_pct,
       ROUND(((-(s.embedding <#> t.v)) * 100)::numeric, 1)        AS inner_product_pct,
       ROUND(((1 - (s.embedding <-> t.v) / 2) * 100)::numeric, 1) AS l2_pct
FROM skills s
CROSS JOIN (SELECT embedding AS v FROM skills WHERE name = 'SQL') t
WHERE s.name <> 'SQL'
ORDER BY s.embedding <=> t.v
LIMIT 5;
-- РЕАЛЬНЫЙ ОТВЕТ:
-- name        | cosine_pct | inner_product_pct | l2_pct
-- ------------+------------+-------------------+--------
-- MySQL       | 68.7       | 68.7              | 60.5
-- Oracle      | 62.1       | 62.1              | 56.5
-- PostgreSQL  | 50.9       | 50.9              | 50.4
-- Power Query | 46.6       | 46.6              | 48.3
-- GraphQL     | 44.8       | 44.8              | 47.5
-- СУТЬ: вектора нормализованы, поэтому косинус и внутреннее произведение
-- дают ОДИНАКОВЫЕ числа (доказано на прототипе), L2-derived — чуть ниже.
-- НЮАНС ФОРМУЛЫ: <#> возвращает МИНУС произведение, поэтому знак разворачивается.
-- Для прод выбран косинус (<=>) — стандарт для текстовых эмбеддингов.

-- ---------------------------------------------------------------------------
-- Сценарий 5. Что вернёт API-слой (итог сборки главного запроса + порога в JSON)
-- ---------------------------------------------------------------------------
-- {
--   "user": {"login": "demo", "technology": "Системный аналитик"},
--   "total_found": 5,
--   "vacancies": [
--     {"name": "Аналитик (методолог)", "employer": "Альфа-Банк", "match_percent": 67.2, "hh_url": "https://hh.ru/vacancy/106"},
--     {"name": "Ведущий системный аналитик", "employer": "Тинькофф", "match_percent": 65.1, "hh_url": "https://hh.ru/vacancy/102"},
--     {"name": "Системный аналитик (интеграции)", "employer": "РЖД", "match_percent": 63.6, "hh_url": "https://hh.ru/vacancy/104"},
--     {"name": "Системный аналитик (платежи)", "employer": "Озон", "match_percent": 61.2, "hh_url": "https://hh.ru/vacancy/107"},
--     {"name": "Системный аналитик (ERP)", "employer": "Сбер", "match_percent": 57.2, "hh_url": "https://hh.ru/vacancy/101"}
--   ]
-- }

-- ============================================================================
-- ОГРАНИЧЕНИЕ, ВЫЯВЛЕННОЕ НА ПРОТОТИПЕ (важно для Генриха)
-- На коротких голых токенах модель работает в основном как сравнение строк:
--   SQL -> MySQL 68.7, Oracle 62.1 (пересечение токенов — работает)
--   BPMN -> C++ 32.6, RabbitMQ 31.0 (шум), а профильные UML 22.9, ER 12.5
-- В боевом матчинге это компенсируется: точные совпадения скиллов дают 100%,
-- наборы скиллов вакансий пересекаются с набором пользователя.
-- ВЫВОД ДЛЯ ПРОД: скиллы кодировать с контекстом (расшифровка из справочника
-- Цербера, например "BPMN — моделирование бизнес-процессов"), либо брать модель
-- крупнее, либо опираться на предфильтр по технологии + точные совпадения,
-- а вектор использовать как ранжирование внутри.
-- ============================================================================
