# C4 Component Diagram — Банк «Эвергрин» × ABS MVP

- **Версия:** v1.0
- **Дата:** 2026-08-25
- **Scope:** MVP (3 синхронных REST-эндпоинта, общая БД, без Kafka, без webhook'ов)
- **Источники:**
  - `docs/mvp-architecture.md` v1.0 (24.08.2026) — зафиксированное архитектурное решение
  - `docs/24082026.md` — протокол встречи 24.08.2026

## Явные допущения / non-факты

1. **Между микросервисами АБС нет синхронных вызовов.** Обмен данными — через общую БД (RLS по `tenant_id`). На диаграмме это сознательное отсутствие связей `credit-decision ↔ loan-issuance`, `credit-decision ↔ loan-signing`, `loan-issuance ↔ loan-signing`.
2. **SLA на всю цепочку** запрос→ответ — 300 мс (гипотеза, замер после реализации — задача P1 плана работ).
3. **Мультитенантность:** изоляция через PostgreSQL RLS + поле `tenant_id` во всех таблицах. На MVP — один тенант «Эвергрин», архитектура готова ко второму.
4. **Стоп-листы** — внешний сервис (mock). Скоринг — внутренний модуль АБС.
5. **Банк выполняет собственную верификацию клиента** (compliance на минималках). АБС этим не занимается.
6. **Аутентификация банка** на API Gateway — API-ключ (или mTLS, выбор — Этап 2 по `docs/mvp-architecture.md` §6).
7. **В MVP Kafka не используется.** Этап 3 — переход на событийную архитектуру (`docs/mvp-architecture.md` §9).

```mermaid
C4Component
    title Component Diagram — Банк «Эвергрин» × ABS MVP

    Person(client, "Клиент банка", "Подаёт заявку, соглашается на предложение, подписывает договор")

    System_Ext(stoplist_ext, "Внешний стоп-лист сервис", "Проверка клиента по стоп-листам (на MVP — mock)")

    Boundary(bank, "Банк «Эвергрин»") {
        ContainerDb(bank_db, "Bank DB", "PostgreSQL банка", "Хранение черновиков заявок и профилей клиентов")

        Container(credit_service, "credit-service", "Java 21 / Spring Boot", "Банковский backend: оркестрация кредитного конвейера") {
            Component(credit_ctrl, "CreditController", "Spring MVC", "REST API мобильного приложения банка")
            Component(credit_mock_ctrl, "CreditMockController", "Spring MVC", "Mock-эндпоинты для интеграционных тестов")
            Component(credit_service_bean, "CreditService", "Spring Bean", "Оркестрация шагов: валидация, compliance, создание заявки, вызов ABS")
            Component(loan_creator, "LoanCreatorService", "Spring Bean", "Маппинг доменной модели банка в DTO запроса ABS")
            Component(bank_compliance, "BankComplianceService", "Spring Bean", "Собственная верификация клиента (compliance на минималках)")
            Component(abs_client, "AbsClient", "RestTemplate / WebClient", "HTTP-клиент к трём эндпоинтам АБС")
            Component(loan_draft_repo, "LoanDraftRepository", "Spring Data JPA", "CRUD по черновикам заявок")
            Component(loan_draft_entity, "LoanDraft", "JPA Entity", "Черновик заявки: id, product, amount, term, status, absApplicationId")
        }
    }

    Boundary(abs_platform, "ABS Platform (мультитенант)") {
        Container(api_gateway, "API Gateway", "Kong + OPA", "Аутентификация, rate-limit, маршрутизация") {
            Component(auth_filter, "Auth Filter", "Kong + OPA", "Валидация API-ключа (или mTLS), запрос решения в OPA")
            Component(tenant_resolver, "Tenant Resolver", "Kong plugin", "Извлекает tenant_id из ключа в заголовок X-Tenant-Id")
            Component(rate_limiter, "Rate Limiter", "Kong plugin + Redis", "Лимиты на банк (RPS/сутки), per-tenant конфиг")
        }

        Container(credit_decision, "credit-decision", "Java 21 / Spring Boot", "Шаг 1: приём заявки, стоп-листы, скоринг, формирование предложения") {
            Component(app_ctrl, "ApplicationController", "Spring MVC", "POST /api/v1/applications")
            Component(app_service, "ApplicationService", "Spring Bean", "Оркестрация: стоп-листы, скоринг, формирование предложения")
            Component(stoplist_client, "StopListClient", "RestTemplate", "Запрос к внешнему стоп-лист сервису")
            Component(scoring_engine, "ScoringEngine", "Spring Bean", "Расчёт кредитоспособности (внутренний, готов к подключению внешнего)")
            Component(offer_generator, "CreditOfferGenerator", "Spring Bean", "Формирование кредитного предложения на основе скоринга")
            Component(decision_repo, "DecisionRepository", "Spring Data JPA", "CRUD по заявкам и предложениям")
        }

        Container(loan_issuance, "loan-issuance", "Java 21 / Spring Boot", "Шаг 2: открытие счетов, генерация черновика договора") {
            Component(issue_ctrl, "LoanIssueController", "Spring MVC", "POST /api/v1/loans/issue")
            Component(issue_service, "LoanIssuanceService", "Spring Bean", "Открытие счетов и генерация черновика договора")
            Component(account_opener, "AccountOpener", "Spring Bean", "Открытие кредитного и операционного счетов (требование ЦБ)")
            Component(doc_generator, "DocumentDraftGenerator", "Spring Bean", "Генерация черновика договора (формат — открытый вопрос)")
            Component(issuance_repo, "IssuanceRepository", "Spring Data JPA", "CRUD по счетам и документам")
        }

        Container(loan_signing, "loan-signing", "Java 21 / Spring Boot", "Шаг 3: подписание, привязка документов, перечисление средств") {
            Component(signing_ctrl, "SigningController", "Spring MVC", "POST /api/v1/loans/sign")
            Component(signing_service, "LoanSigningService", "Spring Bean", "Подписание, привязка документов, перечисление средств")
            Component(doc_binder, "DocumentBinder", "Spring Bean", "Привязка подписанных документов к кредитному счёту")
            Component(funds_transfer, "FundsTransferService", "Spring Bean", "Перевод средств с операционного счёта на кредитный")
            Component(signing_repo, "SigningRepository", "Spring Data JPA", "CRUD по подписям и проводкам")
        }

        ContainerDb(abs_db, "ABS Shared DB", "PostgreSQL + RLS", "Общая БД, изоляция по tenant_id через RLS-политики") {
            ComponentDb(schema_decision, "decision schema", "PostgreSQL", "Заявки, скоринг, кредитные предложения")
            ComponentDb(schema_issuance, "issuance schema", "PostgreSQL", "Счета, черновики договоров")
            ComponentDb(schema_signing, "signing schema", "PostgreSQL", "Подписи, проводки")
            ComponentDb(schema_tenants, "tenants schema", "PostgreSQL", "Справочник банков, API-ключи, лимиты")
        }
    }

    Rel(client, credit_ctrl, "Подаёт заявку", "HTTPS / JSON")
    Rel(credit_ctrl, credit_service_bean, "Делегирует")
    Rel(credit_service_bean, bank_compliance, "Проверка клиента (compliance)")
    Rel(credit_service_bean, loan_creator, "Создание заявки")
    Rel(loan_creator, loan_draft_repo, "Сохраняет черновик")
    Rel(loan_draft_repo, bank_db, "Читает / пишет", "JDBC")
    Rel(credit_service_bean, abs_client, "Отправляет запрос в ABS")
    Rel(loan_creator, abs_client, "Маппит DTO")
    Rel(abs_client, auth_filter, "POST /api/v1/applications", "HTTPS / API key")
    Rel(abs_client, auth_filter, "POST /api/v1/loans/issue", "HTTPS / API key")
    Rel(abs_client, auth_filter, "POST /api/v1/loans/sign", "HTTPS / API key")

    Rel(auth_filter, tenant_resolver, "Валидация ключа", "tenant_id")
    Rel(auth_filter, rate_limiter, "Проверка лимитов")
    Rel(auth_filter, app_ctrl, "Маршрут: tenant=evergreen", "HTTP")
    Rel(auth_filter, issue_ctrl, "Маршрут: tenant=evergreen", "HTTP")
    Rel(auth_filter, signing_ctrl, "Маршрут: tenant=evergreen", "HTTP")

    Rel(app_ctrl, app_service, "Делегирует")
    Rel(app_service, stoplist_client, "Проверка по стоп-листам")
    Rel(stoplist_client, stoplist_ext, "Запрос проверки клиента", "HTTPS")
    Rel(app_service, scoring_engine, "Расчёт кредитоспособности")
    Rel(app_service, offer_generator, "Генерация предложения")
    Rel(offer_generator, decision_repo, "Сохраняет предложение")
    Rel(decision_repo, schema_decision, "RLS по tenant_id", "JDBC")

    Rel(issue_ctrl, issue_service, "Делегирует")
    Rel(issue_service, account_opener, "Открытие счетов")
    Rel(issue_service, doc_generator, "Генерация черновика договора")
    Rel(account_opener, issuance_repo, "Сохраняет счета")
    Rel(doc_generator, issuance_repo, "Сохраняет документ")
    Rel(issuance_repo, schema_issuance, "RLS по tenant_id", "JDBC")

    Rel(signing_ctrl, signing_service, "Делегирует")
    Rel(signing_service, doc_binder, "Привязка документов к счёту")
    Rel(signing_service, funds_transfer, "Перечисление средств")
    Rel(doc_binder, signing_repo, "Сохраняет привязку")
    Rel(funds_transfer, signing_repo, "Сохраняет проводку")
    Rel(signing_repo, schema_signing, "RLS по tenant_id", "JDBC")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```
