# Индекс артефактов — Карьерный агрегатор (три итерации)

Копия артефактов из `D:\Астон\career-aggregator-2`, `D:\Астон\career-aggregator`,
`D:\Астон\career-aggregator-3`.
**Роль Василия: полная — архитектура, документы и код.**
Код писался **для проверки гипотез** (spike-подход): сначала прототип
самостоятельно → затем выводы и артефакты передавались команде.

Продукт: агрегация вакансий + матчинг кандидатов (HH.ru, LLM-грейдинг,
векторный поиск). Одна линия развития, три итерации за полгода.

## Сводка

| Папка | Период | Файлов | Итерация продукта |
|---|---|---|---|
| 01-mvp-search | 29.03.2026 (+24.06 деплой) | 45 | MVP семантического поиска вакансий |
| 02-grading-iteration | 07.04 — 11.05.2026 | 93 | Грейдирование вакансий: ТЗ → 5 версий диаграмм → код hexagonal |
| 03-career-planner | 24.07 — 10.09.2026 | 23 | Career Planner: модульный монолит + pgvector, прототип векторного поиска |
| 04-consulting | 01–10.09.2026 | 3 | C8: Цербер vs HH.ru; C9: pgvector-прототип; C10: финал — решение «вьюхи» в день стопа доп. активности |

## Хронология (даты файлов)

```
2026-03-29   Итерация 1 (aggregator-2): полный MVP — FastAPI + DeepSeek LLM +
             embeddings + Streamlit + Redis + HH.ru; Docker-стек (3 профиля
             compose), Makefile, юнит- и интеграционные тесты, README (452 стр.),
             AVD, компонентная/потоковая/деплой-диаграммы
2026-06-24   deployment.puml — актуализация схемы развёртывания

2026-04-07   Итерация 2 (aggregator): контекст + первая контейнерная схема
2026-04-08   mvp-container v1→v2, проработка 3 вариантов векторизации
             (OpenRouter / Sentence-Transformers / комбинированный)
2026-04-11   mvp-container v3; тест LLM v2
2026-04-13   normalize_competencies.py
2026-04-14   extract_competencies.py — извлечение компетенций
2026-04-18   init_db.py — схема БД
2026-04-19   mvp-container v4, v5 + requirements.md (ТЗ)
2026-05-10   grade_vacancies.py и обвязка — грейдирование на реальных данных
2026-05-11   test/v4 — hexagonal: ports / adapters / repositories / product;
             architecture-v4.md, mvp-api-endpoints.md

2026-07-24   Итерация 3: встреча (расшифровка 89 КБ)
2026-07-27   За 3 дня после встречи: architecture-and-data-spec.md, протоколы
             (minutes, minutes-full), architecture.drawio, proposed-flow.puml,
             ui-mockup.html, skill-hierarchy.html, google-sheets-example.html
2026-08-07   architecture_v1.1.0.puml
2026-08-08   matching-flow-no-llm.puml — матчинг без LLM
2026-09-03   prototype-vector/: init.sql, docker-compose, load_skills.py
2026-09-04   battle-examples.sql, seed_demo.py, README — рабочий прототип
2026-09-07   fill_ctx.py, plan.md (17 КБ) — проверка на реальных данных
2026-09-10   architecture.md + architecture_v1.2.0.puml — обновление по
             дорожной карте (Confluence CA) и итогам встречи с PO
```

## Состав папок

### 01-mvp-search — MVP семантического поиска (март)
Документы: `README.md` (452 стр.), `avd.md` (архитектурное видение),
`components.puml`, `flow.puml`, `deployment.puml`.
Инфраструктура: 3 профиля `docker-compose*.yml`, 4 `Dockerfile.*`, `Makefile`,
`requirements*.txt`, bat-скрипты запуска, `scripts/` (quick_start, полный
тест-флоу).
Код: `app/` (api: search/filters/cache/health; services: hh/llm/embeddings/cache;
models; ui), `tests/` (unit: hh_service, models; integration: api_endpoints),
`test-api.py`, `test-simple.py`.

### 02-grading-iteration — грейдирование вакансий (апрель–май)
Документы (`docs/`, 21 файл): `requirements.md` (ТЗ), `context.md/.puml`,
5 версий контейнерной диаграммы (`mvp-container` → `v5`), `archive/`
(ранние версии + `conversation.md`), `vectorization-options.md` + 3 диаграммы
вариантов, `architecture-v4.md`, `mvp-api-endpoints.md`.
Код (`test/v1 → v4` — эволюция за месяц):
- v1–v2: `test_llm.py` — проверка LLM-гипотез
- v3: рабочие скрипты — extract/normalize компетенций, грейдирование,
  скрейпинг, инициализация БД (на реальной БД вакансий 2,2 МБ — БД не копируется)
- v4: **hexagonal architecture** — `ports/` (IGradingProvider, IDictionary,
  IEmbeddingProvider), `adapters/` (Perplexity, Qwen + retry/backoff),
  `repositories/`, `product/` (domain-сервисы), `api/`, `auth/` (JWT),
  `models/`, `schemas/`, `infrastructure/` (scheduler, cache, LLM-factory)

### 03-career-planner — Career Planner (июль–сентябрь)
Встреча и её выход (24–27.07): `meetings/24072026.md` (расшифровка 89 КБ),
`24072026/` — architecture-and-data-spec.md, minutes + minutes-full,
architecture.drawio, proposed-flow.puml, ui-mockup.html, skill-hierarchy.html,
google-sheets-example.html.
Архитектура: `architecture.md` (v1.2: модульный монолит FastAPI +
PostgreSQL/pgvector; домены access / profile / taxonomy / vacancies / matching /
analytics; инварианты границ; ADR-001..004 по выборам), `architecture_v1.1.0.puml`,
`architecture_v1.2.0.puml`, `matching-flow-no-llm.puml`.
Прототип (`prototype-vector/`): docker-compose + init.sql + загрузка данных +
`battle-examples.sql` + `plan.md` — проверка векторного поиска на реальных
данных за 5 дней (03–07.09).

## Что доказывает пакет

1. **Скорость проверки гипотез:** код писался как spike — от идеи до рабочего
   прототипа: встреча 24.07 → спецификация + мокапы за 3 дня; прототип
   pgvector за 5 дней; MVP-поиск (агрегатор-2) — полный стек с тестами.
2. **Эволюция качества кода:** v1 (тест LLM, 11.04) → v4 (hexagonal с портами
   и адаптерами, 11.05) — месячный цикл самообучения и рефакторинга.
3. **Инженерная дисциплина:** варианты решений прорабатывались и
   документировались ДО кода (3 варианта векторизации с диаграммами);
   каждая итерация диаграмм версионируется (v1→v5, v1.1→v1.2).
4. **Передача знаний команде:** «кодил чтобы проверить гипотезы, потом делился
   информацией» — результаты spikes становились спецификациями, диаграммами
   и прототипами для команды (spec 27.07 — после встречи; обновление
   архитектуры 10.09 — по дорожной карте и встрече с PO).
5. **Непрерывность продукта:** три итерации одной линии за 6 месяцев,
   последняя активность — 10.09.2026 (за 2 дня до настоящего разбора).

## Примечания об источниках

- `D:\Астон\candidate_matching_service` — код чужой (форк стороннего сервиса);
  документы встречи побайтово идентичны `career-aggregator-3/docs/24072026`
  (проверено хэшами), поэтому не копировались во избежание дублирования.
- Не копировались: `.env*` (содержат LLM_API_KEY — секреты), `.venv`, `venv`,
  `logs`, `__pycache__`, `vacancies.db` (данные, 2,2 МБ), пустой `memory.md`,
  `.$*.bkp`.
