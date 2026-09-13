# ABS Sandbox - Container Diagram

Источник: `sandbox/docker-compose.yml` + `docker ps` (на 2026-07-01).
PlantUML: `sandbox-container-diagram.puml`.

## Что развернуто

6 контейнеров в одном docker-compose. Все Up, Keycloak healthy (ready=200), остальные healthchecks тоже зелёные.

| # | Контейнер | Технология | Порт | Назначение |
|---|-----------|------------|------|------------|
| 1 | keycloak | Quarkus 24.0, Keycloak 24.0.5 | 8080 | IdP. Realm `abs` импортируется при старте. |
| 2 | kong | Kong OSS 3.9.3 (OpenResty + Lua) | 8000 proxy, 8001 admin | API Gateway + кастомный Lua plugin. |
| 3 | opa | openpolicyagent/opa:0.59.0 | 8181 | PDP. Rego `abs/rbac/authz.rego` + `data.json`. |
| 4 | redis | redis:7-alpine | 6379 | Blacklist (`blacklist:user:*`, `blacklist:tenant:*`). |
| 5 | admin-service | Java 21 + Spring Boot 3.3.4 + Spring Data JPA + SQLite | 5001 | IAM CRUD: банки + роли + методы. PUT в OPA при изменениях. |
| 6 | backend-service | Java 21 + Spring Boot 3.3.4 + Spring Data JPA + SQLite | 5002 | Mock АБС: `/api/v1/accounts`, `/api/v1/credits`, `/api/v1/me`. |

## Потоки

### Логин (мимо Kong)
Developer → Keycloak:8080 напрямую через `/realms/abs/protocol/openid-connect/{auth,token}`. В нашем стенде используется ROPC (Resource Owner Password Credentials) для headless-тестов. PKCE включён в клиенте `bank-007` (`pkce.code.challenge.method=S256`), но в тестах не прогоняется.

### Каждый запрос сотрудника
Developer → Kong:8000 → Kong внутри делает:
1. routing (`/v1/admin/*` → admin-service:5001, `/api/v1/*` → backend-service:5002)
2. blacklist-guard плагин: `EXISTS blacklist:user:{X-User-Id}` и `EXISTS blacklist:tenant:{X-Tenant-Id}` в Redis. Hit → 401 `{"message":"Token revoked"}`.
3. file-log плагин: JSON-строка в `/var/log/kong/audit.log` (bind mount на хост → `sandbox/kong/audit/audit.log`).
4. proxy в upstream (admin-service или backend-service) с прокинутыми `X-User-Id`, `X-Tenant-Id`, `X-User-Roles`.

Backend-service дополнительно: Spring `HandlerInterceptor` (`AuthVerificationInterceptor`) проверяет что заголовки непустые, парсит `X-User-Roles` в `List<String>`, кладёт в request attributes. Контроллеры (`AccountController`, `CreditController`) делают role check (operator/manager/auditor для accounts; manager/credit_manager для credits).

### При изменениях в IAM
admin-service → OPA:8181 через `RestTemplate.put(OPA_URL + "/v1/data/tenants", body)` в `OpaPublisherService.publishBundle()`. Триггер: создание банка, добавление роли, удаление роли. После PUT OPA in-memory видит новые маппинги → следующий authz-запрос учитывает их.

## Что НЕ реализовано в стенде (явно зафиксировано)

| Чего нет | Где видно | Что вместо |
|----------|-----------|------------|
| Kong JWT plugin | kong.yml (комментарий внизу) | Тестовые запросы идут с готовыми `X-User-*` заголовками, как если бы Kong уже провалидировал JWT |
| Kong OPA pre-function | lua-плагин НЕ вызывает OPA | OPA проверяется напрямую через `test-input-*.json` файлы |
| Kafka + Audit Service + ClickHouse | Kong пишет в `audit.log` файл | file-log plugin пишет JSON строки |
| PKCE browser flow | realm-export.json: `pkce.code.challenge.method=S256` | Используется ROPC grant (`directAccessGrantsEnabled: true`) |
| Custom `tenant_id` JWT claim | JWT содержит только `sub`, `realm_access.roles` | Для тестов `tenant_id` передаётся в отдельном `X-Tenant-Id` заголовке |
| Service-to-service auth | backend-service доверяет `X-User-Roles` | Внутри docker-network mTLS нет |

## Как смотреть

```bash
cd D:\Астон\evergreen\git\abs
docker compose -f sandbox/docker-compose.yml ps
# -> 6 контейнеров, 5 healthy, Keycloak healthy по факту (ready=200)
#    но docker healthcheck может показывать starting в первые 30s

powershell -ExecutionPolicy Bypass -File sandbox/test-flow.ps1
# -> PASS: 9    FAIL: 0
```

Файлы, которые стоит смотреть для понимания стенда:
- `docker-compose.yml` — оркестрация, healthchecks, volumes
- `kong/kong.yml` — маршруты и плагины
- `kong/plugins/blacklist-guard/handler.lua` — кастомный blacklist-плагин (71 строка Lua)
- `opa/policies/abs/rbac/authz.rego` — Rego-политика (47 строк)
- `opa/policies/data.json` — данные тенантов и ролей
- `keycloak/realm-export.json` — realm, клиенты, пользователи, роли
- `admin-service/src/main/java/ru/abs/sandbox/admin/` — 11 Java-файлов
- `backend-service/src/main/java/ru/abs/sandbox/backend/` — 13 Java-файлов
- `test-flow.ps1` — 9 проверочных сценариев
- `TEST_REPORT.md` — результаты прогона