# MVP АБС — Архитектурное решение: Диаграмма контейнеров (Level 2)

## 1. Контекст и ключевые решения
Документ фиксирует структуру контейнеров SaaS-платформы АБС, обеспечивающую изоляцию тенантов и безопасность банковских операций в соответствии со стандартом **Gateway API**.

| Решение | Описание |
| :--- | :--- |
| **Multi-tenancy** | Изоляция на уровне **PostgreSQL RLS**. Единый кластер БД для бизнес-данных + отдельная `admin_db` для IAM-конфигурации. |
| **Traffic Control** | Использование **Kong** как реализации **Gateway API** для управления Ingress-трафиком. |
| **Service Mesh** | Внедрение **Istio** для обеспечения **mTLS** и наблюдаемости (Observability) внутри периметра. |
| **Policy Decision** | **OPA (Open Policy Agent)** как PDP. Rego-политики обобщённые (RBAC, с целевым переходом на ABAC), данные — динамический `data.json` через **OPA Bundle Server** из `admin_db`. |
| **IAM** | **Admin Service** владеет всей IAM-конфигурацией (тенанты, роли, сотрудники), ходит в **Keycloak** через Admin API с service-account (client_credentials). |
| **Defense in Depth** | Изоляция на 3 уровнях: client-роли (Keycloak) + tenant-check + role mapping (OPA) + RLS по `tenant_id` (PostgreSQL). |

---

## 2. Каталог контейнеров

### 2.1 Edge Layer
*   **API Gateway (Kong)**
    *   **Технологии:** Kong OSS + custom Lua plugin (`lua-resty-redis` встроенный).
    *   **Ответственность:** Единый вход, проверка JWT-подписи через JWKS (кэш в Redis, TTL 5 мин, lazy refresh), проверка blacklist в Redis, вызов OPA для авторизации (timeout 50 мс), прокидывание `X-User-Id` и `X-User-Roles` в upstream, проксирование.

### 2.2 Security Layer (IAM + AuthZ)
*   **Keycloak**
    *   **Технологии:** Keycloak (realm: `abs`).
    *   **Ответственность:** Identity Provider. Выпуск JWT сотрудникам банков, аутентификация, Keycloak Admin API для IAM CRUD. Service-account `admin-service` (client_credentials grant) для Admin Service.
*   **OPA (PDP)**
    *   **Технологии:** Open Policy Agent.
    *   **Ответственность:** Принятие решений allow/deny по Rego-политике `abs.rbac.authz` и динамическому `data.json` (in-memory). Не имеет своей БД — данные поступают через Bundle Server.
*   **OPA Bundle Server**
    *   **Технологии:** Java / Spring Boot.
    *   **Ответственность:** Сборка `data.json` из `admin_db.role_permissions`, push bundle в OPA (`PUT /v1/policies/bundle`). Sync trigger от Admin Service при изменении ролей + fallback cron-джоб раз в 5 минут.

### 2.3 Core Business Layer (The Mesh)
*Все контейнеры этого слоя взаимодействуют через **Istio Sidecars (Envoy)** по протоколам mTLS / REST.*

*   **Transaction Service**
    *   **Ответственность:** Оркестрация проводок, контроль целостности операций, выполнение лимитных проверок. Является основным "Master"-сервисом для записи.
*   **Account Service**
    *   **Ответственность:** Управление жизненным циклом счетов. Инкапсулирует логику формирования 20-значных номеров (ЦБ РФ) и контроль балансов.
*   **Client Service (CIF)**
    *   **Ответственность:** Мастер-система данных клиентов (Individuals / Legal entities) и их комплаенс-статусов.
*   **CQRS Read Service**
    *   **Ответственность:** Предоставление высокопроизводительного API для вычитки данных, построения выписок и отчетов.
*   **Admin Service**
    *   **Технологии:** Java / Spring Boot.
    *   **Ответственность:** IAM CRUD: тенанты, роли (Keycloak client-роли для банков), сотрудники, биллинг. Service-account в Keycloak. Sync trigger в OPA Bundle Server при изменении `role_permissions`. Массовые операции — асинхронно через Kafka + DLQ со статусом по `task_id`.
    *   **Вызывается:** через Kong от `bank_admin` (управление ролями и сотрудниками своего банка) и `platform_admin` (управление тенантами, биллинг). Kong → Admin Service: REST + mTLS.

### 2.4 Cross-cutting Services
*   **Audit Service**
    *   **Ответственность:** Централизованный сбор и неизменяемое хранение журналов всех бизнес-событий (Audit Trail).
*   **Compliance & NSI Services**
    *   **Ответственность:** Внешние по отношению к ядру системы проверки (AML / Sanctions) и справочники (БИК, Валюты).

---

## 3. Слой данных и интеграций

### 3.1 Persistence
*   **PostgreSQL (Master):** Основное хранилище для операций записи бизнес-данных. Доступ ограничен RLS-политиками по `tenant_id` (последний рубеж защиты).
*   **PostgreSQL (Replica):** Источник данных для **CQRS Read Service**.
*   **admin_db (отдельная PostgreSQL):** Таблица `role_permissions` (роль → allowed_methods) и `tenant_keycloak_clients` (tenant_id → client_uuid). Логически отделена от бизнес-данных. Читают только Admin Service (для UI) и OPA Bundle Server (для `data.json`). При обработке запросов к этой БД никто не ходит — это исключает деградацию performance под нагрузкой.
*   **Redis:** Blacklist JWT (TTL 1 час для user, без TTL для tenant — последний барьер Kong при немедленной блокировке) + JWKS cache (per-`kid` ключи с TTL 5 мин, lazy refresh). Blacklist — fast-path, не единственный механизм: источник правды — `enabled=false` в Keycloak. JWKS key rotation обрабатывается через grace period Keycloak (Active keys timeout ≥ 10 мин) + force refresh Kong при cache miss.
*   **Kafka (audit topic `auth-audit`):** Kong пишет туда async (fire-and-forget) каждое auth-решение: `allow/deny + tenant_id + user_id + roles + method + path + reason + latency`. Audit Service потребляет, хранит в ClickHouse. Без блокировки основного запроса. Регуляторное требование (152-ФЗ, стандарты ЦБ РФ).

### 3.2 Messaging & CDC
*   **Apache Kafka:** Транспорт для межсервисных событий, Audit-логов, bulk-операций (импорт сотрудников, блокировка тенанта) с DLQ.
*   **Debezium:** Реализация **CDC** (Change Data Capture) для синхронизации данных между Master и Replica / Search Index. **Не используется** для управления состоянием безопасности (только аналитика).

---

## 4. Сценарий взаимодействия: Проведение платежа

1.  **Ingress:** запрос поступает на **Kong**.
2.  **Authentication:** Kong валидирует подпись JWT через JWKS (кэш в Redis, TTL 5 мин). Проверяет blacklist в Redis (`blacklist:user:{user_id}`, `blacklist:tenant:{tenant_id}`).
3.  **AuthZ:** Kong запрашивает у **OPA** решение `allow` для конкретного `tenant_id` + ролей + метода. OPA проверяет in-memory bundle (`data.tenants` + `data.roles`). Timeout 50 мс.
4.  **Proxying:** Kong проксирует запрос в **Transaction Service**, прокидывая `X-User-Id` и `X-User-Roles` из JWT.
5.  **Orchestration:** **Transaction Service** координирует вызовы к **Client** и **Account** сервисам через **mTLS**-каналы. Прокидывает `X-User-Id` и `X-User-Roles` из JWT — внутри mTLS-периметра Istio OPA не вызывается (per решение #9 протокола 19.06.2026). Для критичных операций (переводы) — доп. проверка tenant_id + role внутри сервиса как defense in depth.
6.  **Persistence:** Запись транзакции в **PostgreSQL Master** под контролем RLS (`SET LOCAL app.current_tenant = 'bank-007'`). Даже при ошибке OPA банк физически не увидит чужие данные.
7.  **Audit:** Асинхронная отправка события в **Audit Service** через Kafka.
8.  **Auth-audit:** параллельно Kong пишет событие auth-решения (allow/deny + контекст) в Kafka-топик `auth-audit` — async, не блокирует запрос.
9.  **Read:** **CQRS Service** отдает обновленное состояние из **Replica**.

---

## 5. Сценарий: Управление ролями (банк-клиент)

1.  Владелец банка (роль `bank_admin`) в UI админки банка отмечает галочками, какие методы АБС разрешены для роли `senior_operator`.
2.  UI → Kong → **Admin Service** (валидация JWT, проверка `bank_admin` в OPA, проксирование).
3.  **Admin Service** создаёт `senior_operator` как client-роль в Keycloak (`POST /admin/realms/abs/clients/{bank-uuid}/roles`).
4.  **Admin Service** сохраняет маппинг `senior_operator → [методы]` в `admin_db.role_permissions`.
5.  **Admin Service** синхронно вызывает **OPA Bundle Server** (`POST /internal/v1/bundle/trigger`).
6.  **OPA Bundle Server** (async worker) читает `admin_db.role_permissions`, формирует актуальный `data.json`, делает `PUT /v1/policies/bundle` в OPA.
7.  Следующий запрос от сотрудника банка с ролью `senior_operator` — Kong вызывает OPA, OPA отвечает `allow` (новые правила применились). Kong параллельно пишет auth-аудит в Kafka (топик `auth-audit`).

---

## 6. Auth-audit: логирование auth-решений

**Регуляторное требование (152-ФЗ, стандарты ЦБ РФ):** каждое решение allow/deny по доступу логируется с полным контекстом для аудита, fraud-detection и регуляторных отчётов.

**Источник:** Kong custom Lua plugin пишет в Kafka **async** (fire-and-forget, не блокирует основной запрос). При недоступности Kafka — fallback в локальный лог Kong (queued для повторной отправки).

**Топик:** `auth-audit` в существующем Kafka-кластере. Audit Service (тот же, что для бизнес-аудита) потребляет и пишет в ClickHouse.

**Событие:**

```json
{
  "ts": "2026-07-01T14:58:46Z",
  "request_id": "uuid-...",
  "tenant_id": "bank-007",
  "user_id": "uuid-...",
  "roles": ["senior_operator"],
  "method": "POST",
  "path": "/api/v1/credits/123/approve",
  "opa_decision": "allow",
  "opa_latency_ms": 12,
  "blacklist_hit": false,
  "kong_decision": "allow",
  "kong_reason": null
}
```

Для `deny` поле `kong_reason` обязательно: `opa_denied`, `blacklist_user`, `blacklist_tenant`, `jwt_invalid`, `opa_timeout` (fail-closed при недоступности OPA).

**Реализация в Kong** (псевдокод):

```lua
-- kong/plugins/auth-audit/handler.lua (в access-фазе, после authz)
local producer = require "resty.kafka.producer"
local event = { ts = os.time(), tenant_id = ..., user_id = ..., ... }
local ok, err = producer:produce("auth-audit", nil, cjson.encode(event))
-- ошибка Kafka НЕ блокирует запрос, Kong продолжает
```
