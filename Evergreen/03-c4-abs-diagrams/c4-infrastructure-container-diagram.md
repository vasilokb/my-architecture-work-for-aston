# Контейнерная диаграмма — Инфраструктура и сквозные сервисы (целевая архитектура)

## 1. Назначение диаграммы

Диаграмма описывает **инфраструктурный слой** Облачной АБС (SaaS) и сквозные сервисы, обеспечивающие безопасность, интеграцию, логирование и хранение данных. Это **полная системная картина** — все бизнес-домены и инфраструктура. Текущий скоуп MVP (что реализуется в первом релизе) вынесен в `mvp-abs/c4-mvp-container-diagram.md`.

Источники истины для отдельных решений:
- Multi-tenancy: `D:\Астон\evergreen\git\abs\docs\rls-implementation.md`
- Auth/Authz flow: `D:\Астон\evergreen\git\abs\docs\meetings\19062026.md` и `D:\Астон\evergreen\git\abs\docs\meetings\saas-onboarding-flow.md`
- IAM-операции: `D:\Астон\evergreen\git\abs\docs\meetings\iam-deploy-runbook.md`

---

## 2. Структура слоев

### 2.1 Слой входа и безопасности

| Компонент | Назначение |
|-----------|------------|
| **Ingress Gateway (Istio)** | Единая точка входа для внешнего трафика. TLS termination, маршрутизация, DDoS-защита на уровне инфраструктуры. |
| **API Gateway (Kong OSS)** | Rate limiting, валидация JWT через JWKS (per-kid cache в Redis), проверка blacklist в Redis, вызов OPA для авторизации (timeout 50 мс, fail-closed), проксирование в backend. Custom Lua plugin для blacklist + JWKS lookup. |
| **Keycloak** | Аутентификация. Realm `abs`, выпуск JWT сотрудникам банков по OAuth 2.0 Authorization Code + PKCE. Keycloak Admin API для IAM CRUD. Service-account `admin-service` (client_credentials) для Admin Service. |
| **OPA (PDP)** | Авторизация по Rego-политике `abs.rbac.authz` + динамическому `data.json` bundle. Решение allow/deny за ≤ 50 мс. **Fail-closed** при недоступности. HA: 2-3 реплики. |
| **OPA Bundle Server** | Сборка `data.json` из `admin_db.role_permissions`, push в OPA. Sync trigger от Admin Service + cron-джоб fallback раз в 5 минут. |

**Поток запроса:**
```
Внешний запрос → Ingress (TLS) → Kong:
  1. verify JWT (JWKS из Redis, lazy refresh при miss)
  2. EXISTS blacklist:user, blacklist:tenant в Redis
  3. POST /v1/data/abs.rbac.authz/allow → OPA (timeout 50 мс)
  4. allow → проксирование в Backend
     deny / timeout → 401/403/503 (без проксирования)
```

### 2.2 Слой бизнес-логики

В диаграмме представлен **агрегированно** как единый блок. Детальная структура бизнес-доменов (ядро, расчеты, карты, кредиты, депозиты) — на диаграмме. Внутри каждого домена — Command/Query хендлеры (CQRS-готовность).

**Бизнес-домены:**
- Ядро: модули учёта клиентов (CIF), счетов, бухгалтерский
- Расчёты: модуль платежей
- Тарифы: тарифный модуль + учёт доходов будущих периодов
- Карточный: модуль пластиковых карт
- Лимиты: модуль лимитов и стоп-листов
- Кредитный: кредитный учёт (базовый) + надстройка «Кредитный конвейер»
- Депозитный: депозитный учёт

### 2.3 Слой администрирования

| Компонент | Назначение |
|-----------|------------|
| **Admin Service** (Java / Spring Boot) | IAM CRUD: тенанты (банки-клиенты), роли (Keycloak client-роли для банков), сотрудники, биллинг. Service-account в Keycloak. Sync trigger в OPA Bundle Server при изменении `role_permissions`. Массовые операции — асинхронно через Kafka + DLQ со статусом по `task_id`. |

### 2.4 Слой интеграции

| Компонент | Назначение |
|-----------|------------|
| **Интеграционный модуль** | Адаптеры для внешних систем. Трансформация протоколов (ISO8583, SWIFT, SFTP, HTTPS), управление очередями, retry-политики, circuit breaker. |
| **Egress Gateway (Istio)** | Единая точка выхода для исходящего трафика. mTLS с внешними системами, контроль доступа, мониторинг. |

**Внешние системы:**
- Платёжная инфраструктура (процессинг)
- СБП (Система быстрых платежей)
- Межбанковские расчёты (ЦБ РФ, SWIFT, СПФС)
- Кредитные бюро

### 2.5 Слой данных

| Компонент | Назначение |
|-----------|------------|
| **PostgreSQL Cluster** | Бизнес-данные (клиенты, счета, проводки, тарифы, лимиты). **Shared Schema + RLS по `tenant_id`** через `SET LOCAL app.current_tenant`. RLS — последний рубеж защиты. Подробнее: `rls-implementation.md`. |
| **admin_db (отдельная PostgreSQL)** | `role_permissions` (роль → allowed_methods) + `tenant_keycloak_clients` (tenant_id → client_uuid). **Логически отделена** от бизнес-данных. Читают только Admin Service (UI) и OPA Bundle Server (data.json). Никто не ходит в эту БД при обработке запросов — это исключает деградацию performance под нагрузкой. |
| **Redis Cluster** | (1) Blacklist JWT: `blacklist:user:{user_id}` (TTL 1 час, = JWT TTL) + `blacklist:tenant:{tenant_id}` (без TTL — fast-path, source of truth в OPA через `data.tenants.status`). (2) JWKS cache: per-`kid` ключи, TTL 5 мин, lazy refresh при cache miss. |

### 2.6 Шина логирования (Log Stream)

| Компонент | Назначение |
|-----------|------------|
| **Kafka** | Центральная очередь событий. Топики: `auth-audit` (high-volume, allow/deny), `business-events`, `integration-events`, `admin-events`. Async, не блокирует основной запрос. |
| **Audit Service** (Java / Spring Boot) | Вычитывает из Kafka, обогащает метаданными (tenant_id, request_id, correlation_id), пишет в хранилище. |
| **ClickHouse / Elasticsearch** | Хранилище логов и audit-событий. Быстрый поиск, аналитика, длительное хранение. ClickHouse предпочтительнее для high-volume `auth-audit`. |

**Поток логирования:**
```
Все сервисы → Kafka (async) → Audit Service → ClickHouse / Elasticsearch
```

---

## 3. Ключевые архитектурные решения

### 3.1 Слой входа и безопасности

| Решение | Обоснование |
|---------|-------------|
| **Kong OSS вместо NGINX / Enterprise Kong** | OSS поддерживает custom Lua plugin (`lua-resty-redis` встроенный). Enterprise Kong не нужен. Один custom плагин покрывает blacklist + JWKS + OPA integration. |
| **Per-`kid` JWKS cache с lazy refresh** | При ротации ключей Keycloak Active keys timeout ≥ 10 мин. Kong force refresh при cache miss. Подробнее: `iam-deploy-runbook.md`, раздел 3.7. |
| **Fail-closed при недоступности OPA** | Для banking default-deny обязателен (152-ФЗ, PCI-DSS). Альтернативы (allow / cached decision) отклонены. Защита — HA OPA (2-3 реплики, SLA 99.95%). |
| **Blacklist в Redis (fast-path) + Keycloak `enabled=false` (source of truth)** | Redis даёт 1 мс latency, Keycloak блокирует выдачу новых токенов. При падении Redis — OPA всё равно блокирует через `data.tenants[bank_id].status`. |

### 3.2 Egress Gateway для исходящего трафика

| Решение | Обоснование |
|---------|-------------|
| **Единая точка выхода** | Контроль всех исходящих соединений, единые политики безопасности, мониторинг. |
| **mTLS с внешними системами** | Шифрование и аутентификация при обмене с процессингом, СБП, межбанком. |

### 3.3 Kafka как шина логирования

| Решение | Обоснование |
|---------|-------------|
| **Асинхронная запись** | Не блокирует основной запрос. Ошибка Kafka → fallback в локальный лог (Kong auth-audit). |
| **Auth-audit как отдельный топик** | High-volume событие, отдельный pipeline. Источник: Kong Lua plugin пишет `allow/deny + tenant + user + roles + method + path + reason + latency`. |
| **Audit Service с обогащением** | Добавляет correlation_id, нормализует формат, маршрутизирует по типу события. |
| **ClickHouse для высоконагруженного audit** | Колоночное хранение, быстрые аналитические запросы, дешевле Elasticsearch для long-term. |

### 3.4 Изоляция тенантов (Defense in Depth)

| Уровень | Механизм | Что даёт |
|---------|----------|----------|
| **IAM** | Keycloak client-роли per bank (client_id), platform + bank scope | Банки не видят чужие роли |
| **Authz** | OPA Rego `abs.rbac.authz` с `is_tenant_active` + `data.tenants[bank_id]` | Запросы проходят только от активных тенантов с правильными ролями |
| **Data** | PostgreSQL **Shared Schema + RLS** по `tenant_id` через `SET LOCAL app.current_tenant` | Даже при ошибке OPA банк физически не видит чужие строки |

### 3.5 Admin Service + OPA Bundle Server — разделение логики и данных

| Что | Где |
|-----|-----|
| Логика (Rego) | Git-репозиторий, CI → OPA bundle (редко) |
| Данные маппингов (роль → метод) | `admin_db.role_permissions` через Admin Service UI (часто) |
| Дистрибуция в OPA | OPA Bundle Server: sync trigger от Admin Service + cron 5 мин |
| Аутентификация пользователей | Keycloak (per OAuth 2.0) |
| Аутентификация Admin Service | Keycloak client_credentials grant |

### 3.6 Поддержка CQRS

| Решение | Обоснование |
|---------|-------------|
| **Разделение Command/Query внутри сервисов** | В каждом бизнес-сервисе логика записи и чтения изолирована. |
| **Kafka для синхронизации** | CDC из PostgreSQL отправляет изменения в Kafka, из которой обновляются read-модели. **Не используется** для security state. |
| **Перспектива выделения read-сервисов** | Query-компоненты могут быть вынесены в отдельные микросервисы без изменения API-контрактов при росте нагрузки. |

---

## 4. Взаимодействие компонентов

### 4.1 Входящий трафик (аутентифицированный запрос)
```
Потребители → Ingress (TLS) → Kong:
  1. verify JWT (JWKS per-kid, lazy refresh)
  2. EXISTS blacklist:user, blacklist:tenant в Redis
  3. POST /v1/data/abs.rbac.authz/allow → OPA (timeout 50 мс)
  4. allow → проксирование в Backend (+X-User-Id, +X-User-Roles)
     deny / timeout → 401/403/503
  5. async: пишем auth-audit event в Kafka
```

### 4.2 Логин сотрудника (Auth Code + PKCE)
```
UI → redirect → Keycloak auth endpoint (code_challenge)
Сотрудник вводит пароль В Keycloak
Keycloak → redirect с code
UI → POST /token с code + code_verifier
Keycloak → JWT (TTL 1 час) + refresh_token
```

### 4.3 Управление ролями (банк-клиент)
```
bank_admin → UI → Kong → Admin Service
Admin Service → Keycloak (client-роль, POST /clients/{uuid}/roles)
Admin Service → admin_db (INSERT role_permissions)
Admin Service → OPA Bundle Server (POST /trigger)
OPA Bundle Server → admin_db (SELECT) → формирует data.json
OPA Bundle Server → OPA (PUT /v1/policies/bundle)
```

### 4.4 Исходящий трафик
```
Интеграционный модуль → Egress Gateway → Внешние системы (mTLS)
```

### 4.5 Логирование
```
Все сервисы → Kafka (async, по топикам) → Audit Service → ClickHouse
Kong → Kafka topic auth-audit (отдельно, high-volume)
```

### 4.6 Доступ к данным
```
Backend → PostgreSQL (write + read через RLS по tenant_id)
Admin Service → PostgreSQL БД АБС (тенанты + настройки)
Admin Service → admin_db (role_permissions + tenant_keycloak_clients)
OPA Bundle Server → admin_db (SELECT для data.json)
```

---

## 5. Нефункциональные требования

| Требование | Реализация |
|------------|------------|
| **Доступность** | Istio с балансировкой нагрузки, кластеризация PostgreSQL, Redis, Kafka, ClickHouse. OPA в HA (2-3 реплики). |
| **Безопасность** | mTLS между сервисами (Istio Service Mesh), TLS termination на Ingress, JWT (Auth Code + PKCE) с JWKS rotation grace period, изоляция тенантов через 3 уровня (client-роли / OPA / RLS), blacklist в Redis + Keycloak `enabled=false`. |
| **Производительность** | JWKS cache в Redis (TTL 5 мин), blacklist в Redis (TTL 1 час, без TTL для tenant), OPA in-memory bundle, async audit logging, ClickHouse для аналитики. |
| **Наблюдаемость** | Auth-audit в Kafka → ClickHouse, метрики в Prometheus (через Istio), трейсинг в Jaeger/Tempo, structured logs всех сервисов. |
| **Масштабируемость** | Горизонтальное масштабирование stateless-сервисов (Kong, бизнес-сервисы, OPA, OPA Bundle Server), кластеризация баз данных, Kafka partitioning по `tenant_id`. |

---

## 6. Связь с другими C4-диаграммами

| Диаграмма | Фокус | Аудитория |
|------------|-------|-----------|
| **Бизнес-домены** (`c4-container-diagram.*`) | Логическая структура: ядро, расчёты, тарифы, карты, кредиты, депозиты. Внутренние связи между модулями. | Бизнес-аналитики, разработчики |
| **MVP контейнеры** (`mvp-abs/c4-mvp-container-diagram.*`) | Текущий ско реализации MVP: выбранные контейнеры, IAM-потоки, auth-audit. | Команда MVP, стейкхолдеры релиза |
| **Инфраструктура и сквозные** (этот документ) | Полная физическая организация: все слои, security, интеграции, данные, логирование. | Архитекторы, DevOps, security |

Три диаграммы вместе дают полное представление об архитектуре на разных уровнях детализации.

---

*Версия документа: 2.0 (полный rewrite под целевую архитектуру: Kong + OPA + Bundle Server, admin_db как отдельная БД, ClickHouse для логов, Auth Code + PKCE, fail-closed OPA, Defense in Depth)*
*Дата: 2026-07-01*
*Согласовано с: `19062026.md`, `saas-onboarding-flow.md`, `iam-deploy-runbook.md`, `c4-mvp-container-diagram.md`, `rls-implementation.md`*
