# Runbook: деплой политик и пользователей (IAM)

**Аудитория:** архитектор / DevOps / разработчик ABS
**Область:** как добавлять новые роли/политики в OPA, как заводить пользователей и роли в Keycloak, как делать bulk-импорт сотрудников банка, как работает blacklist на Kong.
**Источники истины:** `D:\Астон\evergreen\git\abs\docs\meetings\19062026.md` (протокол RBAC), `D:\Астон\evergreen\git\abs\docs\meetings\saas-onboarding-flow.md` (флоу), `D:\Астон\evergreen\git\abs\docs\mvp-abs\c4-mvp-container-diagram.md` (архитектура MVP), переписка с Софией Минаевой 14–15.05.2026.

---

## 0. Общая схема (что где)

| Компонент | Что хранит | Как обновляется |
|-----------|------------|-----------------|
| **OPA** (PDP) | Rego-политики `abs.rbac.authz` + динамические данные (`data.tenants`, `data.roles`) из bundle | **Логика** (`.rego`) — из Git через CI. **Данные** (`data.json`) — из `admin_db` через OPA Bundle Server. |
| **OPA Bundle Server** | Ничего не хранит. Сборщик bundle. | Получает sync-триггер от Admin Service + cron-джоб fallback раз в 5 минут. Читает `admin_db`, формирует `data.json`, делает `PUT /v1/policies/bundle` в OPA. |
| **Keycloak** (realm `abs`) | Пользователи, realm-роли (5 базовых), client-роли (per bank), пароли, сессии | Только через Keycloak Admin API. Никаких прямых записей в БД Keycloak. **CDC запрещён** для IAM. |
| **Admin Service** | Ничего не хранит. Координатор IAM-операций. | Синхронный вызов Keycloak Admin API + sync-триггер OPA Bundle Server при изменении `role_permissions`. |
| **admin_db** (PostgreSQL) | `role_permissions` (роль → методы), `tenant_keycloak_clients` (tenant_id → client_uuid) | Чтение: Admin Service (UI) + OPA Bundle Server (для `data.json`). Запись: только Admin Service. Никто другой в БД не ходит при обработке запросов. |
| **Kong** (API Gateway) | Custom Lua plugin: blacklist `blacklist:user:{user_id}` (TTL 1 час) и `blacklist:tenant:{tenant_id}` (без TTL). JWKS cache (TTL 5 мин, lazy refresh). | Blacklist пишет Admin Service синхронно при блокировке. JWKS — сам из Keycloak. |
| **Redis** | Blacklist + JWKS cache | См. Kong выше. |
| **PostgreSQL (бизнес-данные)** | Клиенты, счета, проводки + RLS по `tenant_id` (последний рубеж защиты) | Backend-сервисы через DataSource. К IAM не относится. |

### Ключевое разграничение

- **Логика** (Rego: новая парадигма, новый матчинг endpoint'ов, новый flow) → Git-репозиторий, редкие изменения
- **Данные** (конкретные роли конкретного банка, конкретные разрешения) → `admin_db` через UI Admin Service, частые изменения
- **Аутентификация и пользователи** → Keycloak через Keycloak Admin API, по факту события (создание/увольнение/смена роли)

---

## 1. OPA — политика авторизации и деплой данных

### 1.1. Архитектура деплоя

```
Логика (Rego):                    Данные (роли → методы):
Git → CI → OPA Bundle             admin_db → OPA Bundle Server → OPA
(редкие изменения,                 (частые изменения,
только для новых парадигм)        через UI Admin Service)
```

OPA Bundle Server — это **отдельный микросервис**, не сам OPA. Он собирает актуальный `data.json` из `admin_db.role_permissions` и кладёт его в OPA через `PUT /v1/policies/bundle`.

### 1.2. Структура Git-репозитория `policies-repo`

Только для **логики** (Rego). Данные в `data/` НЕ редактируются вручную — они генерируются из `admin_db`.

```
policies-repo/
├── policies/
│   ├── abs/
│   │   └── rbac/
│   │       └── authz.rego        # пакет abs.rbac.authz
│   └── abs/
│       └── rbac/
│           └── authz_test.rego   # unit-тесты рядом с политикой
├── .github/workflows/
│   └── opa-bundle.yml             # CI: opa test + opa build + PUT bundle
└── Makefile
```

> **Важно:** `data/roles.json` и `data/tenants.json` в Git — НЕ редактируются. Это устаревший подход. Актуальные данные генерируются OPA Bundle Server из `admin_db`. Если в Git-репо лежат такие файлы — их нужно удалить.

### 1.3. Rego-политика `policies/abs/rbac/authz.rego`

```rego
package abs.rbac.authz

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    input.tenant_id in data.tenants.active
    some user_role in input.user_roles
    allowed_endpoints := data.tenants[input.tenant_id].roles[user_role].allowed_methods
    some endpoint in allowed_endpoints
    match_endpoint(endpoint, input.method, input.path)
}

# Точное совпадение "METHOD path"
match_endpoint(endpoint, method, path) if {
    endpoint == sprintf("%s %s", [method, path])
}

# Catch-all
match_endpoint("*", _, _) if true

# Wildcard: "GET /api/v1/accounts/*" → "GET /api/v1/accounts/123"
match_endpoint(endpoint, method, path) if {
    endswith(endpoint, "*")
    prefix := trim_suffix(endpoint, "*")
    startswith(sprintf("%s %s", [method, path]), prefix)
}
```

URL для вызова: `POST /v1/data/abs.rbac.authz/allow`.

### 1.4. Unit-тесты `policies/abs/rbac/authz_test.rego`

```rego
package abs.rbac.authz

test_operator_can_open_account if {
    allow with input as {"tenant_id": "bank-007", "user_roles": ["operator"],
                        "method": "POST", "path": "/api/v1/accounts"}
}

test_operator_cannot_approve_credit if {
    not allow with input as {"tenant_id": "bank-007", "user_roles": ["operator"],
                             "method": "POST", "path": "/api/v1/credits/123/approve"}
}

test_senior_operator_can_approve_credit if {
    allow with input as {"tenant_id": "bank-007", "user_roles": ["senior_operator"],
                        "method": "POST", "path": "/api/v1/credits/123/approve"}
}

test_unknown_tenant_denied if {
    not allow with input as {"tenant_id": "bank-XXX", "user_roles": ["manager"],
                             "method": "GET", "path": "/api/v1/accounts"}
}
```

### 1.5. CI/CD для Git (только новая логика)

```yaml
# .github/workflows/opa-bundle.yml
name: OPA Bundle (logic)
on:
  push:
    branches: [main]
    paths: ['policies/**']

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install OPA
        run: curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static && chmod +x opa
      - name: Unit tests
        run: ./opa test policies/ -v
      - name: Build bundle
        run: ./opa build -b . -o bundle.tar.gz
      - name: Publish to OPA
        run: |
          curl -X PUT --data-binary @bundle.tar.gz \
              -H "Content-Type: application/gzip" \
              ${{ secrets.OPA_URL }}/v1/policies/abs/bundle
```

### 1.6. Как добавить новую роль (senior_operator) — основной сценарий

**Задача:** владелец банка хочет, чтобы роль `senior_operator` могла делать `POST /api/v1/credits/:id/approve` для банка `bank-007`.

**4 шага:**

1. Владелец банка в UI администратора (`/v1/banks/bank-007/roles`) отмечает галочкой метод `POST /api/v1/credits/:id/approve` для роли `senior_operator`. Нажимает «Сохранить».
2. Admin Service делает:
   - `POST /admin/realms/abs/clients/{bank-uuid}/roles` → создаёт `senior_operator` как client-роль в Keycloak (если ещё не создана)
   - `INSERT INTO admin_db.role_permissions (tenant_id='bank-007', role='senior_operator', method='POST /api/v1/credits/:id/approve')`
   - `POST /internal/v1/bundle/trigger` → синхронно будит OPA Bundle Server
3. OPA Bundle Server (асинхронный воркер):
   - `SELECT * FROM admin_db.role_permissions`
   - Формирует `data.json`
   - `PUT /v1/policies/bundle` → OPA
4. Следующий запрос Kong → OPA: новая роль уже работает.

**Время:** ~1–2 секунды end-to-end. Никакого Git, никаких ручных коммитов.

### 1.7. Когда что использовать

| Задача | Куда писать |
|--------|-------------|
| Добавить новую роль банку или новые разрешения для существующей роли | UI Admin Service → `admin_db` → trigger Bundle Server |
| Изменить логику Rego (новая парадигма: атрибуты, время, IP-фильтры) | Git → CI → OPA |
| Добавить новый endpoint в АБС | Сначала регистрация в `admin_db` (через миграцию), потом владелец банка ставит галочку в UI. Rego менять не нужно. |
| Изменить tenant-status (банк заблокирован) | Admin Service → `data.tenants[bank-007].status = 'blocked'` (через триггер Bundle Server) |

### 1.8. Проверка и отладка

```bash
# Какая версия bundle сейчас в OPA
curl https://opa.abs.internal/v1/policies/abs | jq

# Тестовый запрос к OPA (имитация вызова от Kong)
curl -X POST https://opa.abs.internal/v1/data/abs.rbac.authz/allow \
     -H "Content-Type: application/json" \
     -d '{
       "input": {
         "tenant_id": "bank-007",
         "user_roles": ["senior_operator"],
         "method": "POST",
         "path": "/api/v1/credits/123/approve"
       }
     }'
# {"result": true}  ← политика применилась

# Проверить данные в admin_db (для отладки)
psql -h admin-db -U admin -d admin_db \
     -c "SELECT * FROM role_permissions WHERE tenant_id='bank-007';"
```

### 1.9. Откат Rego-логики (новая парадигма сломала production)

```bash
git revert <commit-sha>
git push origin main
# CI пересоберёт bundle и опубликует предыдущую версию
```

⚠️ Это **не откатывает данные** в `admin_db` — для них нет Git-истории. Если проблема в данных — откатывать нужно через Admin Service (reverse trigger Bundle Server со старым `data.json`).

---

## 2. Keycloak — пользователи, роли, аутентификация

### 2.1. Realm `abs` (настраивается один раз)

- **Realm:** `abs`
- **Client для UI банков:** `bank-{bank_id}` (confidential, Auth Code + PKCE)
- **Client для Admin Service:** `admin-service` (confidential, client_credentials grant)
- **5 базовых realm-ролей** (общие для всех банков): `operator`, `manager`, `credit_manager`, `auditor`, `bank_admin`
- **Client-роли банков:** создаёт владелец банка через UI (см. `saas-onboarding-flow.md`, шаг 2)

### 2.2. Аутентификация Admin Service в Keycloak

Admin Service использует **client_credentials grant** с собственным `client_id` и `client_secret`:

```bash
ADMIN_TOKEN=$(curl -s -X POST \
    https://keycloak.abs.internal/realms/abs/protocol/openid-connect/token \
    -d "grant_type=client_credentials" \
    -d "client_id=admin-service" \
    -d "client_secret=$ADMIN_SERVICE_SECRET" \
    | jq -r .access_token)
```

- `client_secret` хранится в секрет-менеджере (Vault / k8s sealed-secrets), **не в коде и не в env-файлах в репо**
- Токен TTL ~5 минут, Admin Service обновляет сам. Refresh token не нужен (его нет в client_credentials)
- **Права минимальные:** `manage-users`, `manage-clients`, `manage-events`, `view-realm`, `view-clients`, `view-users`. **НЕ** `realm-admin` (полный доступ не нужен)

### 2.3. Создание сотрудника вручную (UI → Admin Service → Keycloak)

```http
POST /api/v1/admin/banks/{bank_id}/employees
Authorization: Bearer <JWT владельца банка, роль=bank_admin>
Content-Type: application/json

{
  "email": "ivanov@bank-007.ru",
  "full_name": "Иванов Иван",
  "role_name": "senior_operator"
}
```

**Внутри Admin Service:**
1. `POST /admin/realms/abs/clients/{bank-uuid}/roles` — убедиться, что client-роль `senior_operator` создана (если нет)
2. `POST /admin/realms/abs/users` — создать пользователя
3. `GET /admin/realms/abs/users?email=...` — получить `user_id` (Keycloak не возвращает ID в POST response)
4. `POST /admin/realms/abs/users/{user_id}/role-mappings/clients/{bank-uuid}` — назначить client-роль
5. `PUT /admin/realms/abs/users/{user_id}/execute-actions-email` с телом `["UPDATE_PASSWORD"]` — Keycloak сам шлёт сотруднику email со ссылкой на установку пароля (TTL ссылки 1 час)

**Платформа не генерирует и не хранит пароли.** Keycloak сам шлёт сотруднику письмо.

### 2.4. Bulk-импорт сотрудников (CSV)

```http
POST /api/v1/admin/banks/{bank_id}/employees/import
Authorization: Bearer <JWT владельца банка, роль=bank_admin>
Content-Type: multipart/form-data

file: employees.csv (email,full_name,role_name)
```

**Admin Service:**
1. `202 Accepted` + `task_id` сразу (без блокировки UI)
2. Фоновый воркер читает CSV
3. Для каждой строки — те же шаги что в 2.3
4. Ошибки (дубликаты email, несуществующая роль) — **продолжает обработку**, фиксирует в статусе задачи
5. По окончании — отчёт по `task_id`:
   ```
   GET /api/v1/admin/banks/{bank_id}/employees/import/tasks/{task_id}
   → { "created": 998, "failed": 2, "errors": [{row: 17, reason: "duplicate email"}, ...] }
   ```

Идемпотентность: ошибки НЕ прерывают обработку, успешно созданные учётки сразу работают. **НЕ используются распределённые транзакции** — Keycloak их не поддерживает.

### 2.5. Увольнение сотрудника

```http
DELETE /api/v1/admin/banks/{bank_id}/employees/{user_id}
Authorization: Bearer <JWT владельца банка, роль=bank_admin>
```

**Admin Service (синхронно):**
1. `SET blacklist:user:{user_id} true EX 3600` в Redis (TTL = JWT TTL, автоочистка)

**Admin Service (асинхронно):**
2. `PUT /admin/realms/abs/users/{user_id}` с `{enabled: false}` — Keycloak прекращает выдачу новых токенов

**Эффект:**
- Следующий запрос Kong: blacklist в Redis → 401 (мгновенно)
- Уже выданный JWT у уволенного — протухнет сам через ≤ 1 час
- Новых токенов этому user_id Keycloak больше не выдаст

### 2.6. Смена роли сотрудника

```http
PATCH /api/v1/admin/banks/{bank_id}/employees/{user_id}/role
Authorization: Bearer <JWT владельца банка, роль=bank_admin>
Content-Type: application/json

{ "role_name": "manager" }
```

**Admin Service:**
1. `DELETE /admin/realms/abs/users/{user_id}/role-mappings/clients/{bank-uuid}` с `[{name: "senior_operator"}]` — снять старую роль
2. `POST /admin/realms/abs/users/{user_id}/role-mappings/clients/{bank-uuid}` с `[{name: "manager"}]` — назначить новую
3. **НЕ** трогать Redis blacklist (сотрудник не уволен, только роль поменялась)

Новый JWT при авто-refresh подтянет обновлённый массив ролей.

### 2.7. Сводная таблица Keycloak Admin API операций

| Действие | Метод | URL | Тело |
|----------|-------|-----|------|
| Создать пользователя | POST | `/admin/realms/abs/users` | `{username, email, enabled, emailVerified}` (пароль не передаём — UPDATE_PASSWORD через email) |
| Назначить client-роль | POST | `/admin/realms/abs/users/{id}/role-mappings/clients/{client_uuid}` | `[{name: "senior_operator"}]` |
| Назначить realm-роль | POST | `/admin/realms/abs/users/{id}/role-mappings/realm` | `[{name: "operator"}]` |
| Снять роль | DELETE | `/admin/realms/abs/users/{id}/role-mappings/clients/{client_uuid}` | `[{name: "old_role"}]` |
| Заблокировать | PUT | `/admin/realms/abs/users/{id}` | `{enabled: false}` |
| Разблокировать | PUT | `/admin/realms/abs/users/{id}` | `{enabled: true}` |
| Отправить «установите пароль» | PUT | `/admin/realms/abs/users/{id}/execute-actions-email` | `["UPDATE_PASSWORD"]` |
| Удалить | DELETE | `/admin/realms/abs/users/{id}` | — |
| Создать client-роль | POST | `/admin/realms/abs/clients/{client_uuid}/roles` | `{name: "..."}` |

### 2.8. Запрещено

- ❌ Писать напрямую в БД Keycloak (`UPDATE keycloak.user_entity …`) — ломает внутренние кэши Keycloak
- ❌ Использовать CDC / Kafka для синхронизации пользователей и ролей — асинхронно, окно уязвимости. **CDC — только для аналитики** (read-реплики, DWH)
- ❌ Генерировать и хранить пароли на нашей стороне — Keycloak шлёт сотруднику email сам через `execute-actions-email UPDATE_PASSWORD`
- ❌ Принимать токены от внешних Keycloak'ов банков — у нас один Keycloak на платформу, токены от чужих IdP мы не доверяем и не проверяем (нет публичного ключа для JWKS)

---

## 3. Kong — blacklist уже выданных JWT

### 3.1. Структура ключей в Redis

```
blacklist:user:{user_id}        → "1", TTL = 3600 (1 час, = JWT TTL)
blacklist:tenant:{tenant_id}    → "1", TTL = нет (постоянно, пока не снимем)
```

**Только user_id, не jti.** Почему:
- Уволен сотрудник — заблокированы ВСЕ его токены (текущие и будущие). Один ключ `user_id` покрывает это.
- jti-точность нужна, если хотим отозвать один конкретный токен с TTL 5 минут. У нас такого сценария нет.
- При падении Redis защиту держит `enabled=false` в Keycloak (новых токенов не будет, старые протухнут за 1 час).

### 3.1.1. Tenant blacklist в Redis — fast-path, не source of truth

`blacklist:tenant:{tenant_id}` в Redis — **оптимизация для снижения latency** (1 мс), а не единственный механизм блокировки тенанта. **Source of truth** — OPA через `data.tenants[bank_id].status` в bundle.

**Сценарий потери данных Redis** (FLUSHDB, OOM kill, network partition, AOF corruption):

1. Kong пытается `EXISTS blacklist:tenant:bank-008` → возвращает `false` (ключ потерян)
2. Kong **не блокирует** запрос, а передаёт его в OPA: `POST /v1/data/abs.rbac.authz/allow`
3. Rego-политика `abs.rbac.authz` проверяет `is_tenant_active`:
   ```rego
   is_tenant_active {
       data.tenants[input.tenant_id].status == "active"
   }
   ```
4. Для `bank-008` (заблокированного) `data.tenants["bank-008"].status == "blocked"` → `is_tenant_active` = false → `allow` = false
5. Kong возвращает 403

**Итог:** легитимные запросы задерживаются на ~50 мс (OPA round-trip вместо ~1 мс Redis EXISTS), но **безопасность не нарушается**. Восстанавливать blacklist в Redis вручную или по расписанию **не нужно** — OPA уже всё держит.

Реализовано в `policies/abs/rbac/authz.rego` (раздел 1.3) и в сценарии 5 `auth-flow-sequence.puml` (fail-closed при недоступности OPA — здесь обратный случай: если Kong не может спросить OPA, deny; если OPA недоступен, deny; **если Redis потерял данные, OPA всё равно блокирует**).

### 3.2. При увольнении сотрудника

```python
# Синхронно
redis.setex(f"blacklist:user:{user_id}", 3600, "1")

# Асинхронно (в фоне, не блокирует API)
requests.put(
    f"{KC_BASE}/admin/realms/abs/users/{user_id}",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"enabled": False}
)
```

### 3.3. При блокировке банка

```python
# Синхронно (без TTL — постоянная блокировка)
redis.set(f"blacklist:tenant:{tenant_id}", "1")

# Асинхронно — в Kafka/RabbitMQ задача на полную блокировку сущностей
# (деактивация client'а и обход пользователей). eventual consistency
# через DLQ + retry, даже если Keycloak временно недоступен.
```

### 3.4. Lua-плагин на Kong (упрощённо)

```lua
-- kong/plugins/blacklist-guard/handler.lua
local redis = require "resty.redis"
local red = redis:new()
red:set_timeout(100)  -- 100 мс
local ok = red:connect("redis-master", 6379)

local jwt = require "resty.jwt"
local claims = jwt:verify("keycloak_jwks", kong.request.get_header("Authorization"):sub(8))

if not claims or not claims.verified then
    return kong.response.exit(401, { message = "Invalid token" })
end

local user_id = claims.payload.sub
local tenant_id = claims.payload.tenant_id

local blocked = red:exists(
    "blacklist:user:" .. user_id,
    "blacklist:tenant:" .. tenant_id
)
if blocked > 0 then
    return kong.response.exit(401, { message = "Token revoked" })
end
```

Это **один custom Lua plugin** (`lua-resty-redis` — встроенный модуль Kong OSS). Enterprise Kong не нужен.

### 3.5. Что если Redis упадёт

**Приемлемый trade-off** в пользу availability:

| Уровень | Что делает | Если Redis упал |
|---------|-----------|-----------------|
| Keycloak `enabled=false` (асинхронно) | Блокирует выдачу новых токенов | **Работает** (не зависит от Redis) |
| TTL токена 1 час | Ограничивает окно | Старые токены протухают сами |
| Tenant blacklist (без TTL) | Мгновенный рубеж на Kong | Если Redis упал, Keycloak блокирует новые логины, существующие токены — ≤ 1 час |

**Hardening (DevOps):** Redis Sentinel или Cluster с репликами + AOF persistence. Это инфраструктурный вопрос, не архитектурный.

### 3.6. Auth-audit: логирование решений allow/deny

**Регуляторное требование (152-ФЗ, стандарты ЦБ РФ):** каждое auth-решение (allow/deny) логируется с полным контекстом для аудита, fraud-detection и регуляторных отчётов.

**Источник:** Kong custom Lua plugin пишет в Kafka **async** (fire-and-forget, не блокирует основной запрос).

**Топик:** `auth-audit` (тот же Kafka-кластер, что для бизнес-аудита). Audit Service потребляет и пишет в ClickHouse.

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

**`kong_reason` для den'ов** (обязательное поле):

| `kong_decision` | `kong_reason` |
|-----------------|---------------|
| `deny` | `jwt_invalid` |
| `deny` | `blacklist_user` |
| `deny` | `blacklist_tenant` |
| `deny` | `opa_denied` |
| `deny` | `opa_timeout` (fail-closed при недоступности OPA) |

**Lua-плагин (псевдокод):**

```lua
-- kong/plugins/auth-audit/handler.lua (access-фаза, после authz)
local cjson = require "cjson.safe"
local producer = require "resty.kafka.producer"

local event = {
    ts = ngx.now(),
    request_id = kong.request.get_header("X-Request-ID"),
    tenant_id = jwt_claims.tenant_id,
    user_id = jwt_claims.sub,
    roles = jwt_claims.realm_access.roles,
    method = kong.request.get_method(),
    path = kong.request.get_path(),
    opa_decision = opa_result.allow and "allow" or "deny",
    opa_latency_ms = opa_latency,
    blacklist_hit = blacklist_blocked,
    kong_decision = final_decision,
    kong_reason = final_decision == "allow" and cjson.null or reason
}

-- Async, ошибка НЕ блокирует основной запрос
local ok, err = producer:produce("auth-audit", nil, cjson.encode(event))
if not ok then
    kong.log.err("auth-audit produce failed: ", err)
    -- Fallback: записать в локальный файл, отправит отдельный коллектор
    local f = io.open("/var/log/kong/auth-audit-queue.log", "a")
    f:write(cjson.encode(event), "\n")
    f:close()
end
```

**Гарантии:**

- Async: ошибка Kafka **не блокирует** основной запрос
- Fallback: при недоступности Kafka — локальный файл, отправляет отдельный batch-коллектор при восстановлении
- Не ломает auth/authz path: лучше потерять 0.01% событий аудита, чем задержать 100% запросов

**Запросы к auth-аудиту (для комплаенса и безопасности):**

```sql
-- Все отказы доступа за последний час, сгруппированные по причине
SELECT kong_reason, count(*)
FROM auth_audit
WHERE kong_decision = 'deny'
  AND ts > now() - interval '1 hour'
GROUP BY kong_reason
ORDER BY count DESC;

-- Все действия конкретного пользователя (для расследования инцидента)
SELECT ts, method, path, opa_decision, kong_decision
FROM auth_audit
WHERE user_id = ?
ORDER BY ts DESC
LIMIT 100;
```

---

### 3.7. JWKS lookup с lazy refresh + grace period

**Проблема:** Keycloak периодически ротирует ключи подписи JWT. У Kong в кэше — старые ключи. Если новый JWT приходит с новым `kid`, а в кэше его нет — нужно синхронно сходить в Keycloak за свежим JWKS.

**Решение:** стандартный паттерн «lazy refresh» — берём из кэша, при промахе — force refresh.

**Ключевые настройки:**

| Параметр | Значение | Где настраивается |
|----------|----------|-------------------|
| Keycloak grace period для старого ключа после ротации | **≥ 10 минут** (рекомендуется). По умолчанию Keycloak держит 10 мин через `Active keys timeout` | Keycloak realm settings → Keys → Active |
| TTL ключа в Redis (per `kid`) | **5 минут** | Kong Lua plugin |
| Force refresh при промахе | Синхронно, без кэширования | Kong Lua plugin |
| Фоновый refresh JWKS-документа | Каждые 5 минут (опционально, для уменьшения латентности первого запроса) | Kong Lua plugin |

**Алгоритм:**

```
1. Kong получает JWT с kid="key-v3"
2. Redis: GET jwks:key:key-v3 → null (cache miss)
3. Kong делает force refresh:
   GET https://keycloak.abs.internal/realms/abs/protocol/openid-connect/certs
4. Keycloak возвращает ВСЕ активные ключи (key-v2 ещё активен в grace period + key-v3 новый)
5. Kong кладёт каждый ключ в Redis:
   SET jwks:key:key-v2 EX 300 <key-v2-json>
   SET jwks:key:key-v3 EX 300 <key-v3-json>
6. Kong проверяет подпись JWT ключом key-v3 → OK
7. Следующие запросы с kid=key-v3 — берутся из Redis (без HTTP к Keycloak)
```

**Lua-плагин (псевдокод):**

```lua
-- kong/plugins/jwt-verify/handler.lua
local cjson = require "cjson.safe"
local redis = require "resty.redis"
local http = require "resty.http"

local function fetch_jwks()
    local httpc = http.new()
    local res = assert(httpc:request({
        method = "GET",
        url = "https://keycloak.abs.internal/realms/abs/protocol/openid-connect/certs",
        timeout = 2000  -- 2 сек max на force refresh
    }))
    local body = res:read_body()
    res:close()
    return cjson.decode(body)
end

local function cache_jwks(jwks)
    local red = redis:new()
    red:set_timeout(100)
    red:connect("redis-master", 6379)
    for _, key in ipairs(jwks.keys) do
        red:setex("jwks:key:" .. key.kid, 300, cjson.encode(key))
    end
    red:close()
end

local function get_key(kid)
    local red = redis:new()
    red:set_timeout(100)
    red:connect("redis-master", 6379)
    local cached = red:get("jwks:key:" .. kid)
    red:close()
    if cached then
        return cjson.decode(cached)
    end
    -- Cache miss: force refresh
    local jwks = fetch_jwks()
    cache_jwks(jwks)
    for _, key in ipairs(jwks.keys) do
        if key.kid == kid then
            return key
        end
    end
    return nil  -- kid не найден даже после refresh
end

-- В access-фазе Kong
local jwt_str = kong.request.get_header("Authorization"):sub(8)
local jwt = parse_jwt(jwt_str)
local key = get_key(jwt.header.kid)

if not key then
    return kong.response.exit(401, { message = "Unknown signing key" })
end

local ok = verify_jwt_signature(jwt, key)
if not ok then
    return kong.response.exit(401, { message = "Invalid signature" })
end
```

**Edge cases:**

- **Keycloak недоступен в момент force refresh + ключа нет в кэше (cold start):** Kong отвечает 503. После восстановления Keycloak кэш заполнится.
- **Keycloak ротирует ключи слишком часто** (чаще чем grace period): будут частые force refresh'и. Решение — увеличить `Active keys timeout` в Keycloak до 10+ минут.
- **Keycloak вообще недоступен, но в кэше есть старый ключ:** Kong использует старый ключ — это OK в пределах grace period. Запросы с новым `kid` пройдут только после восстановления Keycloak + force refresh.
- **Холодный старт Kong:** все запросы с kid, для которого нет ключа, пойдут через force refresh. Нагрузка на Keycloak временно вырастет. Лечится предзагрузкой JWKS при старте Kong.

**Связь с `iam-deploy-runbook.md`, раздел 0:**

| Компонент | Что |
|-----------|-----|
| **Redis (JWKS cache)** | Per-kid ключи с TTL 5 мин. Не хранится весь JWKS-документ — каждый `kid` отдельно. |
| **Kong** | Lazy lookup: cache → fallback к Keycloak при miss. Force refresh синхронный. |
| **Keycloak** | Active keys timeout ≥ 10 мин — держит старый ключ после ротации, чтобы JWT, выпущенные до ротации, продолжали работать. |

---

### 3.8. Refresh Token: кто блокирует

**Refresh-токены НЕ проходят через Kong.** UI банка обновляет токен напрямую у Keycloak (`POST /realms/abs/protocol/openid-connect/token` с `grant_type=refresh_token`). Kong не видит этот вызов и не проверяет blacklist по нему.

**Источник правды для блокировки refresh — Keycloak.** При вызове refresh Keycloak проверяет:

1. Refresh-токен валидный и не отозван
2. **`user.enabled == true`** — если `false`, refresh отклоняется с 401
3. Сессия пользователя не отозвана через Keycloak Admin API (`/admin/realms/abs/users/{id}/logout`)

**Сценарий: сотрудник уволен, blacklist установлен, есть валидный refresh_token.**

```
1. Admin Service: SET blacklist:user:{user_id} (Redis, TTL 1 час)
2. Admin Service (async): PUT /admin/realms/abs/users/{user_id} {enabled: false}
3. Старый access_token: истечёт через ≤ 1 час (TTL токена)
4. Попытка refresh: UI → Keycloak
   Keycloak: user.enabled == false → 401
5. Сотрудник полностью отрезан через ≤ 1 час
```

**Что если blacklist в Redis протух (TTL 1 час), а сотрудник всё ещё уволен?** Защиту держит `enabled=false` в Keycloak. Refresh не пройдёт. Blacklist в Redis — fast-path для access_token, **не единственный механизм**.

**Сводная таблица — кто блокирует что:**

| Поток | Проверка blacklist в Redis | Проверка `enabled=false` в Keycloak | Итог |
|-------|---------------------------|-------------------------------------|------|
| Обычный API-запрос (access_token) | **Kong** | (если blacklist miss) | Двойная защита |
| Refresh token | Не проверяется (Kong не видит) | **Keycloak** | Защита через Keycloak |
| Логин | Не применимо | Keycloak проверяет enabled | — |

**Что нужно настроить в Keycloak:**

| Параметр | Значение | Зачем |
|----------|----------|-------|
| Refresh token max age | 30 дней (по умолчанию) | Баланс между удобством и безопасностью |
| `enabled` propagation | Instant (single realm, single DB) | `enabled=false` в Keycloak виден сразу всем нодам |
| Session revocation | Через `POST /admin/realms/abs/users/{id}/logout` | Немедленное отключение всех сессий (если нужно жёстче, чем `enabled=false`) |

**Рекомендация:** при увольнении сотрудника делать **обе** операции:
1. `SET blacklist:user:{user_id}` (Redis) — мгновенный рубеж на Kong
2. `PUT /admin/realms/abs/users/{user_id} {enabled: false}` (Keycloak) — рубеж для будущих refresh

Это уже в текущем коде Admin Service (раздел 2.5). Добавлено сюда явно для фиксации как архитектурного решения.

---

### 3.9. Internal Service-to-Service Auth (X-User-Roles)

**Решение (протокол 19.06.2026, #9):** для внутренних межсервисных вызовов в доверенной сети кластера прокидывается заголовок `X-User-Roles` **без обращения к OPA**. Экономит ~50 мс на каждом внутреннем вызове.

**Как это работает:**

```
Kong → Transaction Service:
  Headers: X-User-Id: <sub из JWT>
           X-User-Roles: [operator, manager]  (из realm_access.roles JWT)

Transaction Service → Account Service:
  Прокидывает X-User-Id и X-User-Roles дальше (если нужны)
  ИЛИ использует свой service-account токен (если операция от имени сервиса)
```

**Threat model:**

| Угроза | Защита |
|--------|--------|
| Внешний атакующий → кластер | mTLS (Istio), Kong JWT validation, NetworkPolicy |
| Скомпрометирован под в кластере | mTLS даёт ему валидный сертификат. **X-User-Roles не защищает** — под может подменить заголовок. |
| Скомпрометирован сервис (не под) | Service-account в Keycloak отозван |
| Network eavesdropping | mTLS шифрует трафик |

**Ключевое допущение:** внутри mTLS-периметра Istio мы доверяем X-User-Roles. Компрометация пода = полная эскалация привилегий внутри кластера. X-User-Roles в этом случае вторичен — ущерб уже есть.

**Это нормально для banking?** Да, потому что:

1. mTLS обязателен (Istio по умолчанию) — это baseline защиты
2. NetworkPolicy в k8s как дополнительный слой (Account Service принимает только от Transaction Service, не от любого пода в namespace)
3. Runtime security (Falco / Tetragon / eBPF) детектит аномалии
4. RLS в PostgreSQL — последний рубеж: даже при компрометации банк физически не увидит чужие строки

**Defense in depth на уровне сервиса (для критичных операций):**

Сервисы, выполняющие **критичные операции** (денежные переводы, изменение лимитов, выдача кредитов), не должны слепо доверять X-User-Roles. Дополнительная проверка внутри сервиса:

```java
// Пример на критичной операции (Account Service, перевод)
public TransferResult transfer(TransferRequest req, HttpHeaders headers) {
    String userId = headers.get("X-User-Id");
    List<String> roles = headers.getOrDefault("X-User-Roles", List.of());
    
    // 1. Проверка: операция соответствует роли
    if (!roles.contains("manager") && !roles.contains("operator")) {
        throw new Forbidden("Insufficient role for transfer");
    }
    
    // 2. Проверка: счёт принадлежит этому user'у (бизнес-инвариант)
    Account account = accountRepo.findById(req.accountId());
    if (!account.getOwnerId().equals(userId)) {
        throw new Forbidden("Account does not belong to user");
    }
    
    // 3. RLS на уровне БД (последний рубеж)
    return transferInternal(req);
}
```

**Что должно быть в нашей архитектуре:**

| Сервис | Критичность | X-User-Roles достаточно? |
|--------|-------------|------------------------|
| Transaction Service (переводы) | Высокая | Нет — нужна доп. проверка |
| Account Service (балансы) | Высокая | Нет — нужна доп. проверка |
| Client Service (KYC) | Средняя | Да — допустимо |
| CQRS Read Service (выписки) | Низкая | Да — read-only |
| Audit Service (логирование) | Низкая | Да |

**Рекомендация для MVP:** для критичных сервисов добавить проверку tenant_id + role в коде (как в примере выше). Для некритичных — достаточно X-User-Roles.

**Альтернатива (для будущего):** service-to-service auth через Keycloak service-account токены. Каждый backend-сервис получает свой client_id в Keycloak и ходит к соседям с этим токеном. **Избыточно для MVP**, рассматривать если threat model потребует.

---

## 4. Чек-лист: добавление новой роли в систему

| # | Действие | Куда | Кто |
|---|----------|------|-----|
| 1 | Владелец банка в UI отмечает галочками методы для роли | UI → Admin Service | Владелец банка |
| 2 | Admin Service создаёт client-роль в Keycloak (если ещё нет) | Keycloak Admin API | Admin Service автоматически |
| 3 | Admin Service пишет `role_permissions` | `admin_db` | Admin Service автоматически |
| 4 | Admin Service синхронно триггерит OPA Bundle Server | `POST /internal/v1/bundle/trigger` | Admin Service автоматически |
| 5 | OPA Bundle Worker собирает `data.json` и пушит в OPA | OPA | OPA Bundle Server автоматически |
| 6 | Следующий запрос Kong → OPA: новая роль работает | — | Автоматически |

Время end-to-end: **~1–2 секунды**. Участие разработчика: ноль.

### Когда нужна новая парадигма (не роль, а способ проверки)

Примеры: «доступ по расписанию», «доступ только из определённых IP», «доступ с учётом суммы операции».

| # | Действие | Куда | Кто |
|---|----------|------|-----|
| 1 | Написать новую Rego-политику с новой логикой | Git `policies-repo` | Архитектор / разработчик |
| 2 | Написать unit-тесты | Git | Разработчик |
| 3 | `git push` → CI: opa test → opa build → PUT bundle | OPA | CI автоматически |
| 4 | Обновить `data.json` через OPA Bundle Server (если нужны новые поля) | `admin_db` | Admin Service или миграция |

---

## 5. Чек-лист: онбординг нового банка (100 сотрудников, 10 ролей)

> **Ключевое:** банк регистрируется в **трёх местах**, каждое — через свой механизм. Не путать.

### 5a. Регистрация банка как тенанта (PostgreSQL АБС)

Через **Admin Service**, не руками:

```http
POST /admin/v1/tenants
Authorization: Bearer <admin-token>
{
  "name": "АБС-Банк",
  "contract_number": "Д-2026-007",
  "admin_email": "owner@bank-007.ru",
  "limits": { "daily_withdrawal": 1000000, "single_operation": 500000 },
  "tariff": { "commission_rate": 0.005, "currency_default": "RUB" }
}
```

Admin Service сам пишет в свою БД АБС (тенант + настройки). Без этого шага АБС не знает, что банк существует.

### 5b. Keycloak — клиент, роли, сотрудники

```http
# Создать client банка (admin платформы)
POST /admin/realms/abs/clients
{"clientId": "bank-007", "enabled": true, "redirectUris": ["https://bank-007.ru/*"]}
→ вернёт {clientId, id (uuid)}

# Создать владельца банка с realm-ролью bank_admin
POST /admin/realms/abs/users  {email, enabled, emailVerified}
PUT  /admin/realms/abs/users/{user_id}/role-mappings/realm  [{name: "bank_admin"}]
PUT  /admin/realms/abs/users/{user_id}/execute-actions-email  ["UPDATE_PASSWORD"]
# Keycloak сам шлёт владельцу email со ссылкой на установку пароля

# Владелец входит в UI админки → создаёт свои 7 client-ролей
POST /admin/realms/abs/clients/{bank-uuid}/roles  {name: "senior_operator"}
# (повторить для 7 кастомных ролей)

# Bulk-импорт 100 сотрудников по CSV
POST /api/v1/admin/banks/bank-007/employees/import  (file: employees.csv)
→ 202 Accepted + task_id
# Фоновый воркер создаёт 100 учёток; отчёт по task_id
```

### 5c. OPA — bundle с новым tenant

Через Admin Service автоматически при создании банка (Admin Service пишет в `admin_db`, синхронно триггерит OPA Bundle Server). Никакого ручного вмешательства.

Если новые роли банка требуют новых endpoint'ов (новых методов) — сначала регистрация endpoint'а в `admin_db` (миграция), потом владелец банка ставит галочку в UI.

### 5d. Итоговая последовательность с временем

| # | Действие | Система | Время |
|---|----------|---------|-------|
| 1 | `POST /admin/v1/tenants` | Admin Service → PostgreSQL | ~0.5 с |
| 2 | `POST /clients` (bank-007) | Admin Service → Keycloak | ~0.3 с |
| 3 | Создание 5 базовых realm-ролей | Keycloak (один раз при инициализации платформы) | — |
| 4 | Создание владельца банка + UPDATE_PASSWORD | Admin Service → Keycloak | ~0.5 с |
| 5 | Создание 7 client-ролей банка | Admin Service → Keycloak | ~0.5 с |
| 6 | Bulk-импорт 100 сотрудников (202 + task_id) | Admin Service → Keycloak | **~5 с** в фоне |
| 7 | Trigger OPA Bundle Server | Admin Service → Bundle Server → OPA | **~1 с** |
| **Итого** | **до первого логина сотрудника** | | **~10 с** (bulk — async) |

---

## 6. Типичные ошибки

| Ошибка | Симптом | Что делать |
|--------|---------|------------|
| **Правлю `data/roles.json` в Git** | Ничего не происходит (или старая версия bundle) | **Не делать так.** Данные идут через `admin_db` → OPA Bundle Server. Если в Git-репо лежит `data/` — удалить. |
| OPA bundle не подхватился, новые правила не работают | Запросы возвращают 403 на разрешённые действия | Проверить `curl $OPA_URL/v1/policies/abs` — версия bundle; проверить логи OPA Bundle Server; проверить, что Admin Service дошёл до триггера |
| Сотрудник заблокирован в Keycloak, но токен ещё работает | Запросы проходят 1 час | Blacklist в Redis на Kong (см. раздел 3). Это ожидаемое поведение — TTL = JWT TTL. |
| Bulk-импорт упал на 500-й строке | Часть сотрудников создана, часть нет | Транзакционности в Keycloak нет. Admin Service пропускает ошибки и продолжает. Отчёт по `task_id`. Для retry — повторно загрузить CSV только с проблемными строками. |
| `tenant_id` в JWT не совпадает с `data.tenants.active` | Все запросы банка 403 | Проверить issuer в JWT, проверить что `data.tenants[bank-007].status == "active"` в bundle |
| Redis упал, blacklist не работает | Заблокированные сотрудники могут работать до 1 часа | Это fail-open trade-off. Keycloak `enabled=false` держит защиту. Hardening: Redis Sentinel/Cluster |
| Push в main сломал Rego (новая парадигма) | Все запросы 403 | `git revert` → push, дождаться CI. Данные в `admin_db` не задеты. |
| Admin Service теряет client_secret к Keycloak | IAM операции падают | Проверить секрет-менеджер (Vault / k8s secret). Никогда не коммитить client_secret в репо. |

---

## 7. Связанные документы

- Протокол встречи 19.06.2026 (RBAC): `D:\Астон\evergreen\git\abs\docs\meetings\19062026.md`
- Скорректированный флоу онбординга: `D:\Астон\evergreen\git\abs\docs\meetings\saas-onboarding-flow.md`
- C4 MVP (Gateway API + Service Mesh + OPA + CQRS): `D:\Астон\evergreen\git\abs\docs\mvp-abs\c4-mvp-container-diagram.md`
- C4 инфраструктура (PDP Service OPA): `D:\Астон\evergreen\git\abs\docs\c4-infrastructure-container-diagram.md`
- C4 auth-only (контейнеры auth/authz): `D:\Астон\evergreen\git\abs\docs\meetings\c4-auth-container.puml`
- Sequence-диаграмма auth-флоу: `D:\Астон\evergreen\git\abs\docs\meetings\auth-flow-sequence.puml`
- RLS для бизнес-данных: `D:\Астон\evergreen\git\abs\docs\rls-implementation.md`
- Ответы аналитикам (PDF): `D:\Астон\evergreen\git\abs\docs\meetings\257760380_f60cbee0d8cf4790ae07e5e3db2224de-210626-2135-274.pdf`

---

*Версия: 2.0 (полный rewrite — данные через admin_db + OPA Bundle Server, Git только для Rego, package abs.rbac.authz, blacklist user_id-only, Keycloak через Admin Service + UPDATE_PASSWORD, онбординг через API, убраны прямые SQL-скрипты)*
*Дата: 2026-07-01*
*Автор: протокол встречи 19.06.2026 (Буркин Василий), архитектурное обновление по итогам согласования `saas-onboarding-flow.md` и `c4-mvp-container-diagram.md`*
