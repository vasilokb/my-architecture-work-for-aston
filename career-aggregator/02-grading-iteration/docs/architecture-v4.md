# Архитектура test/v4 — Career Aggregator

## Обзор

Платформа для автоматизированного грейдирования вакансий и матчинга кандидатов. Поддержка SQLite (dev) и PostgreSQL (prod) с первого дня.

---

## Структура проекта

```
test/v4/
│
├── main.py                      # FastAPI app, lifespan (scheduler, cache warm, DI wiring)
├── config.py                    # DATABASE_URL, API_KEY, LLM_PROVIDER, rate limits
├── exceptions.py                # NotFoundError, ValidationError, GradingError, AuthError, LLMProviderError
│
├── models/                      # SQLAlchemy ORM (общие для всех слоёв)
│   ├── __init__.py              # Base, export all models
│   ├── vacancy.py               # Vacancy
│   ├── competency.py            # Competency, CompetencyCategory, CompetencyVariant, CategoryLink
│   ├── raw.py                   # RawCompetency (+ processed flag), UnknownCompetency
│   ├── parsed.py                # ParsedVacancy, ParsedRequirement
│   ├── user.py                  # User, Role (employee/consultant/admin, expires_at)
│   ├── matching.py              # CandidateProfile (→ User), MatchingResult
│   └── joblog.py                # JobLog (id, job_type, started_at, finished_at, status, error_message)
│
├── schemas/                     # Pydantic request/response (валидация API)
│   ├── __init__.py
│   ├── competency.py            # CategoryRead, CompetencyRead, CompetencyCreate, VariantRead
│   ├── vacancy.py               # VacancyExtractRequest, ExtractStatus, VacancyRawRead, VacancyGradedRead
│   ├── grading.py               # GradingRunRequest, GradingStatus, SkillRead
│   ├── auth.py                  # LoginRequest, RegisterRequest, Token, UserRead
│   └── admin.py                 # ScheduleUpdate, JobLogRead
│
├── ports/                       # Абстрактные интерфейсы (Dependency Inversion)
│   ├── __init__.py
│   ├── grading_provider.py      # IGradingProvider.grade(text) -> dict
│   ├── dictionary.py            # IDictionary.lookup(name) -> competency_id
│   └── embedding.py             # IEmbeddingProvider.embed(text) -> list[float] (future: матчинг)
│
├── adapters/                    # Реализации портов (конкретные LLM)
│   ├── __init__.py
│   ├── perplexity_provider.py   # Perplexity SDK + retry/backoff (429)
│   └── qwen_provider.py         # Qwen SDK + retry/backoff (429)
│
├── repositories/                # DB CRUD (общие, используются всеми слоями)
│   ├── __init__.py
│   ├── vacancy_repo.py          # get_all_raw(), get_by_id(), delete(), count_ungraded()
│   ├── competency_repo.py       # get_tree(), search(), create(), update(), delete()
│   ├── raw_repo.py              # get_unprocessed(), mark_processed(batch_ids) — атомарно
│   ├── parsed_repo.py           # get_graded(), get_skills(vacancy_id), save_result()
│   ├── user_repo.py             # create(), get_by_id(), check_expiry()
│   └── joblog_repo.py           # create_job(), update_job_status(), get_jobs()
│
├── auth/                        # Авторизация и роли
│   ├── __init__.py
│   ├── dependencies.py          # get_current_user(), require_role(role)
│   ├── jwt_handler.py           # create_token(), verify_token()
│   └── password.py              # hash_password(), verify_password()
│
├── ml_pipeline/                 # BATCH: извлечение и нормализация (асинхронно)
│   ├── __init__.py
│   ├── extractor.py             # HH.ru API → vacancies (raw snippets)
│   ├── raw_competency_extractor.py  # vacancies → raw_competencies (LLM)
│   └── normalizer.py            # raw_competencies → competencies dict (atomic: update dict + mark_processed)
│
├── product/                     # REAL-TIME: бизнес-логика приложения
│   ├── __init__.py
│   ├── dictionary_service.py    # IDictionary impl: in-memory cache (cachetools.TTLCache), TTL reload
│   ├── grading_service.py       # vacancies + IDictionary → parsed (LLM + task runner)
│   ├── matching_service.py      # (stub) candidate profile vs graded vacancies
│   └── profile_service.py       # (stub) CRUD profiles
│
├── api/                         # FastAPI routers (тонкие контроллеры)
│   ├── __init__.py
│   ├── auth.py                  # POST /login, /register
│   ├── competencies.py          # CRUD справочник → после изменений: dictionary_service.reload()
│   ├── vacancies.py             # raw list, graded list, extract trigger
│   ├── grading.py               # grading run, status
│   └── admin.py                 # scheduler config, manual ML trigger, user management, job logs
│
├── infrastructure/              # Внешние зависимости (БД, LLM, кэш, шедулер)
│   ├── __init__.py
│   ├── database.py              # engine (SQLite/PostgreSQL), session, create_all
│   ├── llm_factory.py           # create_provider(name) -> IGradingProvider
│   ├── cache.py                 # cachetools.TTLCache wrapper
│   └── scheduler.py             # APScheduler: add_job(), update_grading_schedule(cron), remove_job()
│
└── scripts/                     # CLI обёртки над сервисами (PYTHONPATH=. python scripts/...)
    ├── init_db.py               # → infrastructure.database.create_all()
    ├── extract.py               # → ml_pipeline.extractor
    ├── extract_competencies.py  # → ml_pipeline.raw_competency_extractor
    ├── normalize.py             # → ml_pipeline.normalizer
    └── grade.py                 # → product.grading_service
```

---

## Архитектурные решения

### Паттерн: Ports & Adapters (Hexagonal)
- **Ports** (`ports/`) — абстрактные интерфейсы, от которых зависит бизнес-логика
- **Adapters** (`adapters/`) — конкретные реализации (Perplexity, Qwen)
- Приложение зависит от интерфейсов, не от реализаций. Новый LLM — новый адаптер + регистрация в фабрике.

### DI (Dependency Injection)
- `main.py` при старте создаёт `DictionaryService` (загружает кэш из БД)
- `DictionaryService` передаётся в `GradingService` через конструктор (не через репозиторий напрямую)
- FastAPI `Depends()` для API-роутов: `get_session()`, `get_provider()`, `get_current_user()`
- Скрипты (`scripts/`) — тонкие обёртки: импортируют сервисы и вызывают их напрямую

### Разделение Batch и Real-time
- **`ml_pipeline/`** — батч-процессы: извлечение вакансий, сырые компетенции, нормализация. Работают по расписанию или вручную.
- **`product/`** — real-time сервисы: грейдирование по запросу, кэшированный справочник, матчинг.

### Двойная поддержка БД
- **SQLite** (dev): `NullPool`, `PRAGMA foreign_keys=ON`, `check_same_thread=False`
- **PostgreSQL** (prod): `QueuePool`, `pool_size=10`, `pool_pre_ping=True`
- Модели SQLAlchemy одинаковы. Переключение через `DATABASE_URL` в `config.py`.
- **Alembic** для миграций. `autogenerate` только в dev. В prod — только явные миграции.

### Кэширование справочника
- `product/dictionary_service.py` — in-memory кэш (`cachetools.TTLCache`)
- Загружается при старте приложения, TTL-перезагрузка каждые 5 минут
- `IDictionary.lookup(name)` — O(1), без запросов к БД
- **Инвалидация**: после каждого CRUD через `api/competencies.py` вызывается `dictionary_service.reload()` (синхронно)

### Авторизация
- JWT-токены, 3 роли: `employee`, `consultant`, `admin`
- Ограничение доступа уволенных: `expires_at` (2 месяца)
- `auth/dependencies.py` — `get_current_user()`, `require_role()`

### Шедулер (динамическое расписание)
- `infrastructure/scheduler.py` — APScheduler
- `update_grading_schedule(cron_expression)` — удаляет старую задачу, добавляет новую (без рестарта)
- Настройка хранится в БД (таблица `JobLog` или отдельная `ScheduleConfig`)
- Админ меняет расписание через `POST /admin/schedule`

### Обработка ошибок LLM
- Адаптеры (`adapters/`) — retry + exponential backoff для 429 (rate limit)
- `exceptions.py` — `GradingError`, `LLMProviderError`

### Транзакционность нормализации
- `ml_pipeline/normalizer.py` — атомарная операция:
  1. Загружает unprocessed `RawCompetency`
  2. Обновляет справочник (competencies, variants, categories, links)
  3. `raw_repo.mark_processed(batch_ids)` — одним SQL-запросом
- Если шаг 2 или 3 упал — транзакция откатывается, `RawCompetency` остаются unprocessed

### Отслеживание задач (JobLog)
- Таблица `JobLog`: `id`, `job_type` (extract/normalize/grade), `started_at`, `finished_at`, `status`, `error_message`
- Админ видит статус через `GET /admin/jobs` и `GET /admin/jobs/{id}`
- Для MVP достаточно логов в консоль + JobLog для истории

---

## Тонкие различия SQLite vs PostgreSQL

| Аспект | Решение |
|---|---|
| Автоинкремент PK | `Integer, primary_key=True` — SQLAlchemy подставит правильный тип |
| Булев тип | Без `CheckConstraint` на булевы поля |
| Внешние ключи | SQLite: `PRAGMA foreign_keys=ON` после connect |
| LIKE (регистронезависимо) | Не `ilike()` (не работает в SQLite), использовать `func.lower()` |
| Массивы | Не `ARRAY` (нет в SQLite). Варианты компетенций — отдельная таблица |
| JSON | `Text` или `JSON` (не `JSONB`), универсально |

---

## Зависимости

```
fastapi
uvicorn
sqlalchemy
alembic
pydantic
perplexityai          # SDK для Perplexity
qwen-sdk              # SDK для Qwen (placeholder)
python-jose[cryptography]  # JWT
passlib[bcrypt]       # хеширование паролей
APScheduler           # планировщик
cachetools            # TTLCache для in-memory кэша
requests              # HH.ru API
beautifulsoup4        # парсинг HTML (fallback)
```

---

## Тестирование

- **Юнит-тесты**: in-memory SQLite (`sqlite:///:memory:`) с `PRAGMA foreign_keys=ON`
- **Интеграционные тесты**: PostgreSQL (Docker)
- **Мок LLM**: `ports/grading_provider.py` → фиктивный адаптер
- **Скрипты**: вызывать через `PYTHONPATH=. python scripts/extract.py`

---

## Соответствие C4 диаграмме (mvp-container-v5.puml)

| C4 компонент | Реализация |
|---|---|
| Web Application (Streamlit) | Отдельный проект, общается с API по REST |
| Auth Service | `auth/` + `api/auth.py` |
| Competency Extractor | `ml_pipeline/extractor.py` |
| Competency Normalizer | `ml_pipeline/normalizer.py` |
| Competency Dictionary | `product/dictionary_service.py` (in-memory cache, IDictionary) |
| Vacancy Grading | `product/grading_service.py` + `infrastructure/scheduler.py` |
| Candidate Matching | `product/matching_service.py` (stub, модели `CandidateProfile`, `MatchingResult`) |
| Profile Manager | `product/profile_service.py` (stub) |
| Database | SQLite / PostgreSQL через `infrastructure/database.py` |
| LLM Provider | `adapters/perplexity_provider.py`, `adapters/qwen_provider.py` |