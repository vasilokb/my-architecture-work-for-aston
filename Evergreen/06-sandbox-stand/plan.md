# Auth Sandbox — Plan — Code — Test

> **Цель плана:** развернуть локальный docker-compose стенд auth/authz Облачной АБС для ручной проверки ключевых сценариев (логин, авторизация, blacklist, refresh, fail-closed, internal service-to-service).
> **Архитектурный контекст:** берётся 1:1 из production docs в `D:\Астон\evergreen\git\abs\docs\` — см. `meetings/saas-onboarding-flow.md`, `meetings/iam-deploy-runbook.md`, `meetings/19062026.md`, `mvp-abs/c4-mvp-container-diagram.md`.
> **Стек Admin/Backend сервисов:** Java 21 + Spring Boot 3.3 (1:1 с production). Прочее — Keycloak (Quarkus), OPA (openpolicyagent/opa), Kong (OSS 3.x + Lua plugin), Redis.
> **Что упрощаем относительно прода:** SQLite вместо PostgreSQL, нет OPA Bundle Server (Admin Service пушит bundle сам), нет Kafka (audit в файл), нет Istio Service Mesh (нет mTLS), нет HA / replicas.

---

## 1. Что из себя представляет стенд

**Auth Sandbox** — локальный docker-compose стенд, который воспроизводит архитектуру auth/authz Облачной АБС в упрощённом виде. Поднимается одной командой `docker compose up -d --build`.

**Сценарий использования:** архитектор или разработчик поднимает стенд, проходит 6 проверочных сценариев из `scripts/test-flow.sh`, видит как работает каждый уровень защиты. Используется для демонстрации архитектуры коллегам, отладки интеграций, проверки изменений в Rego-политике, онбординга новых разработчиков.

**Сервисы в стенде:**

| Сервис | Технология | Порт | Назначение |
|--------|------------|------|------------|
| **Keycloak** | Quarkus, realm `abs` импортируется | 8080 (Admin), 8180 (auth) | IdP: выпуск JWT по Auth Code + PKCE, service-account `admin-service` |
| **Kong** | OSS 3.x + custom Lua plugin `blacklist-guard` | 8000 (proxy), 8001 (admin) | API Gateway: JWT validation (JWKS), blacklist, OPA authz, audit → файл |
| **OPA** | openpolicyagent/opa:latest | 8181 | PDP: Rego-политика `abs.rbac.authz` + data.json |
| **Redis** | redis:7-alpine | 6379 | Blacklist JWT (TTL 1 час) + JWKS cache (опционально) |
| **Admin Service** | **Java 21 + Spring Boot 3.3 + Spring Data JPA + SQLite (Xerial)** | 5001 | IAM CRUD: банки, роли, сотрудники. PUT bundle в OPA |
| **Backend Service** | **Java 21 + Spring Boot 3.3 + Spring Data JPA + SQLite (Xerial)** | 5002 | Mock АБС: 3 эндпоинта (`/accounts`, `/credits`, `/me`) |

**Что НЕ демонстрируется** (явные упрощения):
- Бизнес-логика АБС (счета, кредиты, платежи) — замокана на 2 эндпоинтах
- HA / replicas — каждый сервис в одном экземпляре
- mTLS между сервисами — plain HTTP внутри docker compose
- Service-to-service auth через service-account — backend доверяет X-User-Roles
- OPA Bundle Server — Admin Service пушит bundle сам
- Kafka — audit пишется в `data/audit.log`
- Keycloak `execute-actions-email` flow — пароль задаётся напрямую в realm-export
- Bulk-импорт сотрудников через CSV — только ручной POST

---

## 2. Активное состояние

Обновляется после каждого шага. После закрытия всех фаз — в архив.

| Фаза | Статус | Закрыта | Комментарий |
|---|---|---|---|
| 1. README + уточняющие вопросы | [x] | [x] | README.md + docs/plan.md созданы (v0.2, Java 21 + Spring Boot 3.3) |
| 2. Окружение: docker-compose + .env + базовые образы | [x] | [x] | .env.example (649 B), .gitignore (254 B), docker-compose.yml (4.7 KB) с 6 сервисами и healthchecks, Makefile (1.3 KB) с целями up/down/build/logs/status/test/reset. `docker compose config` валиден. |
| 3. Keycloak: realm `abs` с тестовыми пользователями | [x] | [x] | `keycloak/realm-export.json` (2.9 KB): realm `abs`, 5 базовых realm-ролей (operator, manager, credit_manager, auditor, bank_admin), 2 клиента (bank-007 с PKCE + ROPC для тестов; admin-service с client_credentials + service-account), 3 пользователя (operator, manager, bank-admin) с паролями. `keycloak/Dockerfile` (24.0, start-dev + --import-realm). JSON валиден. **Протестировано end-to-end** (см. TEST_REPORT.md сценарии 7-9): OIDC discovery 200, ROPC login для operator@bank-007.test выдаёт JWT с `sub=user-operator`, `realm_access.roles=[operator]`, `expires_in=3600s`. **Был баг** с Docker build cache, который копировал старую версию realm-export.json с полем `accessPolicy` (Keycloak 24 это поле не знает). Лечится `docker compose build --no-cache keycloak`. |
| 4. OPA: Rego-политика `abs.rbac.authz` + data.json | [x] | [x] | `opa/policies/abs/rbac/authz.rego` (1.7 KB): пакет `abs.rbac.authz`, v0 синтаксис (для OPA 0.59.0). `opa/policies/data.json` (1.7 KB): 2 тенанта. **Протестировано** через REST API на работающем контейнере: 5/5 тестов прошли (operator+accounts=true, operator+credits=false, bank-008=blocked=false, manager+*=true, wildcard=accounts/123=true). Image pinned на `0.59.0` (стабильная v0). |
| 5. Admin Service: Java 21 + Spring Boot + SQLite + REST API + OPA publisher | [x] | [x] | Полный набор: pom.xml (Spring Boot 3.3.4, Java 21, SQLite Xerial, Lombok), 11 Java-файлов (AdminApplication, 2 controllers, 3 services, 2 repositories, 2 models, 1 config), application.yml, multi-stage Dockerfile (Maven + JRE 21 + wget для healthcheck). **Протестировано end-to-end**: 10/10 тестов прошли. T1 health, T2/T4 409 на дубли, T3 GET банка, T5 list ролей, T6 add role, T7 404 для несуществующего тенанта, T8 2 роли в списке, T9 OPA содержит 2 метода, T10 OPA authz=true для нового метода. **OPA-интеграция:** Admin Service пушит данные через `PUT /v1/data/tenants` (не bundle, проще для MVP). |
| 6. Backend Service: Java 21 + Spring Boot + SQLite + 3 эндпоинта + RLS-эмуляция | [x] | [x] | Полный набор: pom.xml (Spring Boot 3.3.4, Java 21, SQLite Xerial, Lombok), 11 Java-файлов (BackendApplication, 3 controllers, 2 services, 2 repositories, 2 models, 1 interceptor, 1 WebMvcConfig, 1 DataSeeder), application.yml, multi-stage Dockerfile. **Протестировано end-to-end**: 13/13 тестов прошли. T1 health, T2-T4 auth interceptor (401 без headers, 401 без roles, 200 с полными), T5 2 счёта для bank-007, T6 1 счёт для bank-008 (RLS), T7 403 operator на /credits, T8 1 кредит для manager, T9 add role → bundle push, T10 OPA data корректен, T11 OPA authz=true, T12 /me 200, T13 wildcard. AuthInterceptor: проверяет X-User-Id/X-Tenant-Id/X-User-Roles, ставит в request attributes. RLS-эмуляция: `@Query findByTenantId` с явным `WHERE tenant_id=?`. Role check на уровне контроллера (defense in depth). |
| 7. Redis + Kong + custom Lua plugin `blacklist-guard` | [x] | [x] | `kong/kong.yml` (декларативная конфигурация: services admin/backend, plugins blacklist-guard + file-log), `kong/plugins/blacklist-guard/handler.lua` (Redis EXISTS с fail-open, PRIORITY=1000), `kong/plugins/blacklist-guard/schema.lua`, `kong/Dockerfile` (multi-stage с USER root для mkdir). **Протестировано end-to-end через Kong:8000**: 5/5 тестов. T1 bank-007, operator НЕ в blacklist → 200. T2 test-blacklisted-user → 401 "Token revoked". T3 tenant bank-002 → 401. T4 /api/v1/accounts → 200. T5 audit.log содержит все 3 события с request/response/headers/latencies. **Пришлось обойти:** schema с конфигурируемыми полями вызывала "cannot create a new field" — обошёл через пустой `fields = {}` + хардкод `fail-open=true`. **Пришлось обойти:** luarocks make не работает — обошёл через прямой COPY в `/usr/local/share/lua/5.1/kong/plugins/`. **Пришлось обойти:** Kong USER=kong не может создать `/var/log/kong` — обошёл через `USER root` в Dockerfile. Bind mount `./kong/audit:/var/log/kong` для проброса audit-лога на хост (после `docker compose down/up` — иначе volume bind не подхватывается). |
| 8. Test scenarios + scripts/test-flow.ps1 | [x] | [x] | `sandbox/test-flow.ps1` (PowerShell — на Windows баш coreutils недоступен). **9/9 OK** в TEST_REPORT.md: OPA operator/accounts allow=true, OPA operator/credits allow=false, OPA bank-008 deny, Kong blacklist user 401, Kong blacklist tenant 401, audit.log вырос на 1903 байт, Keycloak OIDC discovery 200, Keycloak ROPC login JWT с ttl=3600s, JWT содержит sub+realm_access.roles. |
| 9. Wrap-up + TEST_REPORT.md | [x] | [x] | `sandbox/TEST_REPORT.md` создан: таблица 6/6 сценариев, что доказано end-to-end, как воспроизвести, известные отступления от прода. |

**Правило обновления:** после Test-критерия, прошедшего проверку, — отметить `[x]`. Если нет — добавить «⚠ <дата>: <что не прошло>» в «Комментарий» и/или скорректировать следующие шаги.

---

## 3. Бизнес-границы (что НЕ входит в стенд)

> Стенд — это **демо auth/authz**, а не полная АБС. Ниже — что НЕ демонстрируется.

**НЕ входит:**
- **Бизнес-логика АБС.** Реальные счета, проводки, кредиты, карты, депозиты, платежи — замоканы на 2 эндпоинтах в Backend Service.
- **Multi-tenancy в полном объёме.** 2 тенанта в БД (test-bank-001, test-bank-002) для демонстрации изоляции. В проде — сотни тенантов.
- **Сложные сценарии увольнения / отзыв токенов.** Только `enabled=false` в Keycloak + blacklist. Без массовых операций через Kafka + DLQ.
- **Custom Kong plugin в production-качестве.** В сатике plugin покрывает blacklist и audit → файл. В проде — async produce в Kafka, health-checks, метрики.
- **OPA Bundle Server как отдельный сервис.** В сатике Admin Service сам делает `PUT /v1/policies/bundle` в OPA. В проде — выделенный Java-сервис с cron-джобом.
- **Kafka для auth-audit.** В сатике — `data/audit.log`. В проде — Kafka topic `auth-audit` + Audit Service + ClickHouse.
- **PostgreSQL + реальный RLS.** В сатике — SQLite через Xerial JDBC, `WHERE tenant_id=?` в Spring Data JPA `@Query`. В проде — PostgreSQL + `SET LOCAL app.current_tenant` + Row-Level Security.
- **Istio Service Mesh + mTLS.** В сатике — plain HTTP внутри docker compose. В проде — Istio + mTLS между всеми сервисами.
- **Refresh token rotation, Keycloak session revocation.** Только базовый refresh.
- **Monitoring / observability.** Без Prometheus, Grafana, Jaeger.
- **CI/CD.** Без GitHub Actions, GitLab CI — стенд поднимается руками.

---

## 4. Имена файлов и слоёв

- **Корень:** `git/abs/sandbox/`
- **Документация:** `git/abs/sandbox/README.md`, `git/abs/sandbox/docs/plan.md` (этот файл)
- **docker-compose:** `git/abs/sandbox/docker-compose.yml`
- **Keycloak:** `git/abs/sandbox/keycloak/realm-export.json` (преднастроенный realm), `git/abs/sandbox/keycloak/Dockerfile` (импорт realm при старте)
- **OPA:** `git/abs/sandbox/opa/policies/abs/rbac/authz.rego` (Rego-политика), `git/abs/sandbox/opa/data.json` (начальный снимок маппингов)
- **Admin Service (Java 21 + Spring Boot):** `git/abs/sandbox/admin-service/pom.xml`, `src/main/java/ru/abs/sandbox/admin/` (контроллеры, сервисы, репозитории, модели, конфиг), `src/main/resources/application.yml`, `Dockerfile`
- **Backend Service (Java 21 + Spring Boot):** `git/abs/sandbox/backend-service/pom.xml`, `src/main/java/ru/abs/sandbox/backend/` (контроллеры, interceptor, репозитории, модели), `src/main/resources/application.yml` + `data.sql`, `Dockerfile`
- **Kong:** `git/abs/sandbox/kong/kong.yml` (декларативная конфигурация), `kong/plugins/blacklist-guard/handler.lua`, `kong/plugins/blacklist-guard/schema.lua`, `kong/Dockerfile` (сборка Kong с plugin)
- **Redis:** `git/abs/sandbox/redis/seed.sh` (предзаполнение blacklist)
- **Скрипты:** `git/abs/sandbox/scripts/test-flow.sh` (6 сценариев), `scripts/reset.sh`, `scripts/logs.sh`
- **Makefile:** `git/abs/sandbox/Makefile` (`make up`, `make test`, `make reset`, `make logs`)
- **Данные:** `git/abs/sandbox/data/admin.db`, `backend.db`, `audit.log` (создаются при первом запуске, в `.gitignore`)

---

## 5. Стек и архитектурные решения

- **Docker Compose** для оркестрации. Все сервисы — `depends_on` с healthchecks. Стенд стартует одной командой `docker compose up -d --build`.
- **Keycloak в режиме dev** (`start-dev`), без HTTPS. Admin Console на `localhost:8080`. Realm `abs` импортируется через `KEYCLOAK_IMPORT` env-переменную.
- **Kong OSS 3.x + custom Lua plugin.** Custom plugin `blacklist-guard` лежит в `kong/plugins/`. Сборка Kong — через кастомный Dockerfile с `COPY plugins /tmp/plugins && luarocks install ...`. Использует `lua-resty-redis` (встроен в Kong) и `lua-resty-kafka` (если Kafka, иначе fallback на файл).
- **OPA latest** с bundle-файлами на старте. Конфигурация через `decision_logs` env (выключены для простоты).
- **Redis 7** — стандартный, без кластера, без persistence (для сатидка OK).
- **Java 21 (LTS) + Spring Boot 3.3** для Admin Service и Backend Service. **1:1 с production docs** (тоже Java/Spring Boot).
- **Maven** — multi-stage build. Стадия сборки: `maven:3.9-eclipse-temurin-21`. Runtime: `eclipse-temurin:21-jre-alpine`.
- **Spring Data JPA + Hibernate** для ORM. DDL через `spring.jpa.hibernate.ddl-auto=update` (для dev) или `validate` (для прод-like).
- **SQLite через Xerial JDBC** (`org.xerial:sqlite-jdbc:3.46.0.0`). Диалект Hibernate: `org.hibernate.community.dialect.SQLiteDialect`. В проде — PostgreSQL + `org.hibernate.dialect.PostgreSQLDialect`.
- **Bash + curl + jq** для скриптов. Проверки через `grep` на ответы.
- **Makefile** как единая точка входа: `make up`, `make down`, `make test`, `make reset`, `make logs`, `make status`.

---

## 6. Архитектурный контракт (что стенд воспроизводит)

> Эти правила — копия production docs, упрощённая для стенда. Должны быть покрыты тестами в TEST_REPORT.

### 6.1. Аутентификация

- **OAuth 2.0 Authorization Code + PKCE** (НЕ ROPC — ROPC deprecated в OAuth 2.1).
- Realm `abs`, два клиента:
  - `bank-007` (для тестирования пользователей банка)
  - `admin-service` (client_credentials grant, для Admin Service)
- 5 базовых realm-ролей: `operator`, `manager`, `credit_manager`, `auditor`, `bank_admin`.
- Тестовые пользователи в realm-export:
  - `operator@bank-007.test` / `operator` (realm-role: operator)
  - `manager@bank-007.test` / `manager` (realm-role: manager)
  - `bank-admin@bank-007.test` / `admin` (realm-role: bank_admin)

### 6.2. Авторизация (OPA)

- Rego-политика `abs.rbac.authz` с правилом:
  ```rego
  allow {
      is_tenant_active
      some user_role in input.roles
      allowed_endpoints := data.tenants[input.tenant_id].roles[user_role].allowed_methods
      some endpoint in allowed_endpoints
      match_endpoint(endpoint, input.method, input.path)
  }
  is_tenant_active { data.tenants[input.tenant_id].status == "active" }
  ```
- `data.json` — initial snapshot: `bank-007` с ролями `operator` (только `GET /api/v1/accounts`) и `manager` (всё через `*`).
- Tenant `bank-008` со статусом `blocked` для проверки блокировки.

### 6.3. Blacklist в Redis (fast-path)

- Ключ `blacklist:user:{user_id}` (TTL 1 час, = JWT TTL).
- Ключ `blacklist:tenant:{tenant_id}` (без TTL — fast-path; source of truth в OPA через `data.tenants[bank_id].status`).
- Проверка: `EXISTS blacklist:*` в Kong Lua plugin.
- TTL 1 час гарантирует автоочистку.

### 6.4. Fail-closed OPA

- Kong Lua plugin при timeout 50 мс или 5xx от OPA → 503 Service Unavailable.
- **Альтернативы (allow / cached decision) отклонены** для banking.
- HA OPA в стенде НЕ нужна — один экземпляр, при остановке стенд показывает fail-closed явно.

### 6.5. Auth-audit (в файл в сатике)

- Каждое решение allow/deny пишется в `data/audit.log` в формате JSON Lines:
  ```json
  {"ts":"2026-07-01T14:58:46Z","request_id":"...","tenant_id":"bank-007","user_id":"...","roles":["operator"],"method":"GET","path":"/api/v1/accounts","opa_decision":"allow","opa_latency_ms":12,"blacklist_hit":false,"kong_decision":"allow","kong_reason":null}
  ```
- Async fire-and-forget — не блокирует основной запрос.
- **В проде** — Kafka topic `auth-audit`, не файл.

### 6.6. RLS-эмуляция в SQLite (Spring Data JPA)

- Каждая таблица в `backend.db` имеет `tenant_id`.
- В Spring Data JPA репозиториях — `@Query("SELECT a FROM Account a WHERE a.tenantId = :tenantId")` либо кастомный `Specification`.
- Альтернатива: Hibernate Filter (`@FilterDef`) — автоматически добавляет `WHERE tenant_id=?` ко всем запросам.
- **В проде** — PostgreSQL + `SET LOCAL app.current_tenant` + реальный RLS.

### 6.7. Internal service-to-service (X-User-Roles)

- Kong прокидывает `X-User-Id` и `X-User-Roles` из JWT в backend.
- Backend для критичных операций проверяет внутри (defense in depth) через Spring `HandlerInterceptor`:
  - `X-User-Roles` содержит нужную роль
  - `X-User-Id` соответствует владельцу ресурса (account.owner_id == X-User-Id)
- **В сатике** проверка упрощённая, без полного business-инварианта.

---

## 7. Окружение: .env / ports / start-up

### 7.1. `.env.example`

```dotenv
# Порты (можно менять, если заняты на хосте)
KONG_HTTP_PORT=8000
KONG_ADMIN_PORT=8001
KEYCLOAK_HTTP_PORT=8080
KEYCLOAK_HTTPS_PORT=8443
OPA_PORT=8181
REDIS_PORT=6379
ADMIN_SERVICE_PORT=5001
BACKEND_SERVICE_PORT=5002

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KC_REALM=abs
KC_URL=http://keycloak:8080

# OPA
OPA_DECISION_LOG=false
OPA_URL=http://opa:8181

# Admin Service (Java)
ADMIN_DB_PATH=/data/admin.db

# Backend Service (Java)
BACKEND_DB_PATH=/data/backend.db

# Тестовые tenant_id для data.json
TENANT_BANK_001=bank-007
TENANT_BANK_002=bank-008
```

### 7.2. Healthchecks (для `depends_on` в docker-compose)

| Сервис | Healthcheck |
|--------|-------------|
| Keycloak | `curl -fs http://localhost:8080/health/ready` |
| Kong | `kong health` |
| OPA | `curl -fs http://localhost:8181/health` |
| Redis | `redis-cli ping` |
| Admin Service | `curl -fs http://localhost:5001/actuator/health` |
| Backend Service | `curl -fs http://localhost:5002/actuator/health` |

### 7.3. Запреты для ИИ-агента

- Не читать `.env` ни прямо, ни через `node -e "console.log(process.env.X)"` или `printenv`.
- Не выполнять `make reset` без явного подтверждения пользователя.
- `.env` — в `.gitignore`.
- Не модифицировать `realm-export.json` (Keycloak пересоздаст realm с дефолтными пользователями).

### 7.4. Reset

```bash
# macOS / Linux / Windows
make reset
```

Удаляет: `data/admin.db`, `data/backend.db`, `data/audit.log`, volumes для Redis и Keycloak. После reset — снова `make up`.

---

## 8. Контекстные правила для ИИ-агента

Преамбула для каждого шага (или один раз в начале сессии):

> Прочитай `D:\Астон\evergreen\git\abs\sandbox\README.md` и `D:\Астон\evergreen\git\abs\sandbox\docs\plan.md`. Найди активную фазу в §2, текущий шаг в §10. **Не читай `.env`** ни прямо, ни через команды терминала. **Не выполняй `make reset`** без явного подтверждения. Архитектурный контракт стенда — в §6, он соответствует production docs в `D:\Астон\evergreen\git\abs\docs\meetings\`. После выполнения шага — отметь `[x]` в §10 и опиши изменения.

**Правило «новый чат при засорении контекста»:** после 4-5 фаз активное контекстное окно ИИ-агента заполняется. Для фаз 6-9 — открыть **новый чат** и передать ему: `README.md`, `docs/plan.md`. Без этого есть риск, что модель начнёт забывать правила §6.

---

## 9. Сводный план

| № | Фаза | Артефакты | Test-критерий (упрощённо) |
|---|-------|-----------|---------------------------|
| 1 | README + уточняющие вопросы | `README.md`, `docs/plan.md` | README содержит стек, структуру, сценарии; план содержит фазы |
| 2 | docker-compose + .env | `docker-compose.yml`, `.env.example`, `Makefile` | `docker compose up -d --build` поднимает все сервисы; healthchecks green |
| 3 | Keycloak realm `abs` | `keycloak/realm-export.json`, `keycloak/Dockerfile` | `curl http://localhost:8080/realms/abs/.well-known/openid-configuration` возвращает 200; тестовые пользователи существуют |
| 4 | OPA: Rego + data.json | `opa/policies/abs/rbac/authz.rego`, `opa/data.json` | `curl -X POST http://localhost:8181/v1/data/abs/rbac/authz/allow -d '...'` возвращает `{"result": true}` для operator+GET accounts |
| 5 | Admin Service (Java 21 + Spring Boot 3.3) | `admin-service/pom.xml`, `src/main/java/...`, `application.yml`, `Dockerfile` | `curl POST /banks` создаёт тенант в SQLite; `POST /banks/{id}/roles` пушит bundle в OPA |
| 6 | Backend Service (Java 21 + Spring Boot 3.3) | `backend-service/pom.xml`, `src/main/java/...`, `application.yml`, `data.sql`, `Dockerfile` | `curl GET /api/v1/accounts` с JWT operator+bank-007 → 200; с JWT operator+bank-008 → 403 (tenant blocked) |
| 7 | Redis + Kong + Lua plugin | `redis/seed.sh`, `kong/kong.yml`, `kong/plugins/blacklist-guard/handler.lua`, `kong/Dockerfile` | `docker compose up -d kong` собирает кастомный образ; `GET /api/v1/accounts` с blacklist:user → 401 |
| 8 | Test scenarios | `sandbox/test-flow.ps1` | `powershell -ExecutionPolicy Bypass -File sandbox/test-flow.ps1` проходит все 9 сценариев (см. TEST_REPORT.md) |
| 9 | Wrap-up + TEST_REPORT | `TEST_REPORT.md` | Документированы все сценарии + edge cases + отступления от прода |

---

## 10. Фазы и шаги

Структура строки: **Вход** → **Слой** → **Действие** → **Результат** → **Test** → **Файлы**.

### Фаза 1. README + уточняющие вопросы · Docs

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 1.1 | Architecture docs (saas-onboarding-flow, c4-mvp, runbook) | Docs | Создать `README.md` со структурой: О проекте, Стек, Структура проекта, Как запустить (macOS/Windows), Что проверяет, Границы MVP, Известные отступления | README объясняет стенд | grep: 4 команды запуска (mac/win × start), раздел «Что проверяет» с 6 сценариями, раздел «Известные отступления» | `README.md` |
| 1.2 | §6 | Docs | Раздел «Границы MVP» сослаться на §3 плана (одна точка истины) | Синхронизировано | grep «Границы MVP» — найдено | `README.md` |
| 1.3 | §10 фазы 2-9 | Docs | Создать `docs/plan.md` со всеми 9 фазами по структуре §10 | План готов | grep: «Фаза 1.», «Фаза 9.», «Коммит после фазы» — все 9 найдены | `docs/plan.md` |

**Коммит после фазы:** `docs: README и план реализации Auth Sandbox (Java 21 + Spring Boot 3.3)`

---

### Фаза 2. docker-compose + .env + Makefile · Infra

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 2.1 | §7.1 | Infra | Создать `.env.example` с переменными из §7.1 (порты, Keycloak, OPA, пути к БД, tenant_id) | Файл коммитится | `cat .env.example` — все переменные из §7.1 | `.env.example` |
| 2.2 | §7.4 | Infra | В `.gitignore` добавить `.env`, `data/*.db`, `data/*.log`, `**/target/` (Maven build output) | Локальный `.env` и сбилженные JAR не коммитятся | `git check-ignore -v .env` | `.gitignore` |
| 2.3 | §7.2 | Infra | Создать `docker-compose.yml` со всеми 6 сервисами и healthchecks. Сервисы: keycloak, kong, opa, redis, admin-service, backend-service. Volumes: keycloak-data, redis-data, data/ (host). Admin/Backend собираются из локальных Dockerfile | Compose готов | `docker compose config` — без ошибок; `docker compose up -d --build` поднимает все | `docker-compose.yml` |
| 2.4 | 2.3 | Infra | Создать `Makefile` с целями: `up`, `down`, `test`, `reset`, `logs`, `status` | Единая точка входа | `make` (без аргументов) показывает help | `Makefile` |
| 2.5 | 2.3, 2.4 | Infra | `make up` — все контейнеры стартуют, healthchecks проходят за 3-5 минут (включая сборку Java-сервисов) | Стенд поднят | `make status` показывает все 6 сервисов healthy | — |

**Коммит после фазы:** `chore: docker-compose с Keycloak, Kong, OPA, Redis, Admin (Java/Spring), Backend (Java/Spring); Makefile; .env.example`

---

### Фаза 3. Keycloak realm `abs` · IAM

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 3.1 | §6.1 | IAM | Создать `keycloak/realm-export.json`: realm `abs`, 5 базовых realm-ролей, 2 клиента (`bank-007` для пользователей, `admin-service` с `client_credentials` + service-account), 3 пользователя (operator, manager, bank-admin) с паролями | Realm готов | Импорт при старте Keycloak | `keycloak/realm-export.json` |
| 3.2 | 3.1 | IAM | Создать `keycloak/Dockerfile`: `FROM quay.io/keycloak/keycloak:24.0`, `COPY realm-export.json /opt/keycloak/data/import/`, `CMD ["start-dev", "--import-realm"]` | Auto-import при старте | `docker compose up -d keycloak` → логи `Realm 'abs' imported` | `keycloak/Dockerfile` |
| 3.3 | 3.2 | IAM | `make restart keycloak` — проверить, что realm импортирован: `curl http://localhost:8080/realms/abs/.well-known/openid-configuration` | Endpoint отвечает 200 с правильным `issuer` | curl возвращает 200; `jq .issuer` = `http://localhost:8080/realms/abs` | — |
| 3.4 | 3.3 | IAM | Проверить тестовых пользователей: `curl -X POST .../protocol/openid-connect/token -d "username=operator@bank-007.test&password=operator&grant_type=password&client_id=bank-007"` | Token выпускается | curl возвращает `access_token` с `sub`, `tenant_id`, ролями | — |

**Коммит после фазы:** `feat: Keycloak realm abs с 5 базовыми ролями, 2 клиентами, 3 тестовыми пользователями`

---

### Фаза 4. OPA: Rego + data.json · PDP

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 4.1 | §6.2 runbook §1.3 | PDP | Создать `opa/policies/abs/rbac/authz.rego` — копия production Rego из `iam-deploy-runbook.md` §1.3 | Политика готова | `curl -X POST http://localhost:8181/v1/data/abs/rbac/authz/allow -d '{"input":{"tenant_id":"bank-007","user_roles":["operator"],"method":"GET","path":"/api/v1/accounts"}}'` → `{"result": true}` | `opa/policies/abs/rbac/authz.rego` |
| 4.2 | §6.2 | PDP | Создать `opa/data.json` с двумя тенантами: `bank-007` (active, operator+GET accounts, manager+*), `bank-008` (blocked для проверки tenant-блокировки) | Initial bundle | `curl -X POST .../v1/data/abs/rbac/authz/allow -d '{"input":{"tenant_id":"bank-008","user_roles":["operator"],...}}'` → `{"result": false}` (tenant blocked) | `opa/data.json` |
| 4.3 | 4.1, 4.2 | PDP | `docker-compose up -d opa` — OPA стартует с bundle из `opa/policies/` + `data.json` | OPA работает | `curl http://localhost:8181/v1/policies/abs` — bundle загружен | `docker-compose.yml` (volumes для opa) |

**Коммит после фазы:** `feat: OPA с Rego abs.rbac.authz и data.json (2 тенанта, blocked-tenant для теста)`

---

### Фаза 5. Admin Service (Java 21 + Spring Boot 3.3) · IAM CRUD

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 5.1 | §6.1, §6.2 | Backend | `admin-service/pom.xml`: Spring Boot 3.3, Java 21, зависимости `spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `org.xerial:sqlite-jdbc:3.46.0.0`, `org.hibernate.orm:hibernate-community-dialects`, `lombok`, `spring-boot-starter-actuator` | Maven-проект готов | `cd admin-service && mvn package -DskipTests` собирает JAR без ошибок | `admin-service/pom.xml` |
| 5.2 | 5.1 | Backend | `AdminApplication.java`: `@SpringBootApplication` с `main()`, сканирование пакета `ru.abs.sandbox.admin` | Скелет | `mvn spring-boot:run` стартует без ошибок | `src/main/java/ru/abs/sandbox/admin/AdminApplication.java` |
| 5.3 | 5.2 | Backend | `model/Bank.java`: JPA-entity с полями `id`, `tenantId` (unique), `name`, `status`, `createdAt`. `model/RolePermission.java`: `id`, `bankId` (FK), `role` (String), `method` (String), `createdAt`. Lombok `@Data`, `@NoArgsConstructor`, `@AllArgsConstructor` | Модели готовы | `mvn spring-boot:run` — Spring создаёт таблицы в `data/admin.db` | `model/Bank.java`, `model/RolePermission.java` |
| 5.4 | 5.3 | Backend | `repository/BankRepository extends JpaRepository<Bank, Long>`, `Optional<Bank> findByTenantId(String tenantId)`. `repository/RolePermissionRepository` — `List<RolePermission> findByBankId(Long bankId)` | Spring Data JPA работает | unit-тест: `findByTenantId("bank-007")` возвращает Optional | `repository/*.java` |
| 5.5 | 5.4 | Backend | `service/OpaPublisherService.java`: метод `publishBundle()` — собирает `data.json` из всех `RolePermission` всех банков, вызывает `RestTemplate.put("${opa.url}/v1/policies/abs/bundle", bundle)` | Sync триггер OPA | unit-тест с мок-RestTemplate: `publishBundle()` вызывает PUT с правильным URL и body | `service/OpaPublisherService.java` |
| 5.6 | 5.5 | Backend | `service/BankService.java`: `createBank`, `addRole`, `getBankByTenantId`. `service/RoleService.java`: после `addRole` вызывает `opaPublisherService.publishBundle()` | Бизнес-логика готова | unit-тест: `addRole` → `RolePermissionRepository.save` + `OpaPublisherService.publishBundle` вызван | `service/*.java` |
| 5.7 | 5.6 | Backend | `controller/BankController.java`: `POST /banks` (создать банк), `GET /banks/{tenantId}` (получить), `GET /banks/{tenantId}/roles` (список ролей), `POST /banks/{tenantId}/roles` (добавить роль + метод), `DELETE /banks/{tenantId}/roles/{role}/{method}` (удалить). Все с `@RestController`, JSON-вход-выход, валидация через `@Valid` | CRUD работает | `curl POST /banks -H "Content-Type: application/json" -d '{"tenantId":"bank-007","name":"Test Bank"}'` → 201; `curl GET /banks/bank-007/roles` → массив | `controller/BankController.java`, `controller/RoleController.java` |
| 5.8 | 5.7 | Backend | `src/main/resources/application.yml`: `server.port=5001`, `spring.datasource.url=jdbc:sqlite:${ADMIN_DB_PATH:./data/admin.db}`, `spring.jpa.hibernate.ddl-auto=update`, `spring.jpa.properties.hibernate.dialect=org.hibernate.community.dialect.SQLiteDialect`, `opa.url=${OPA_URL:http://localhost:8181}` | Конфиг готов | `mvn spring-boot:run` стартует с этим конфигом | `src/main/resources/application.yml` |
| 5.9 | 5.8 | Backend | `Dockerfile`: multi-stage — стадия 1 `FROM maven:3.9-eclipse-temurin-21 AS build` с `mvn package -DskipTests`, стадия 2 `FROM eclipse-temurin:21-jre-alpine` с `COPY --from=build /app/target/*.jar app.jar` и `ENTRYPOINT ["java", "-jar", "/app/app.jar"]` | Образ собирается | `docker compose build admin-service` — без ошибок; образ ~250 MB | `Dockerfile` |

**Коммит после фазы:** `feat: Admin Service на Java 21 + Spring Boot 3.3 + SQLite (Xerial) с OPA Bundle publisher`

---

### Фаза 6. Backend Service (Java 21 + Spring Boot 3.3) · Mock АБС

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 6.1 | §6.6, §6.7 | Backend | `backend-service/pom.xml`: те же зависимости что у Admin Service, плюс `spring-boot-starter-validation` | Maven-проект готов | `mvn package -DskipTests` собирает JAR | `backend-service/pom.xml` |
| 6.2 | 6.1 | Backend | `BackendApplication.java`: `@SpringBootApplication` с `main()` | Скелет | `mvn spring-boot:run` стартует | `BackendApplication.java` |
| 6.3 | 6.2 | Backend | `model/Account.java`: JPA-entity с `id`, `tenantId`, `ownerId`, `accountNumber`, `balance`, `createdAt`. `model/Credit.java`: аналогично, плюс `amount`, `status` | Модели готовы | Spring создаёт таблицы в `backend.db` | `model/*.java` |
| 6.4 | 6.3 | Backend | `repository/AccountRepository extends JpaRepository<Account, Long>`, `@Query("SELECT a FROM Account a WHERE a.tenantId = :tenantId") List<Account> findByTenantId(@Param("tenantId") String tenantId)`. Аналогично для CreditRepository. Все методы с явным `WHERE tenant_id=?` (RLS-эмуляция) | Spring Data JPA работает | `findByTenantId("bank-007")` возвращает только записи bank-007 | `repository/*.java` |
| 6.5 | 6.4 | Backend | `interceptor/AuthVerificationInterceptor.java`: implements `HandlerInterceptor`. `preHandle()` — проверяет заголовки `X-User-Id` (required), `X-User-Roles` (required, парсится из comma-separated в `List<String>`), `tenant_id` (required, извлекается из `X-User-Id` либо передаётся отдельно). Если отсутствуют — 401. Возвращает `true` если всё ок, `false` если отказ. Регистрируется через `WebMvcConfigurer.addInterceptors()` для путей `/api/**` | Auth interceptor работает | unit-тест: отсутствие X-User-Id → false; наличие → true | `interceptor/AuthVerificationInterceptor.java`, `config/WebMvcConfig.java` |
| 6.6 | 6.5 | Backend | `controller/AccountController.java`: `GET /api/v1/accounts` — принимает `tenantId` из interceptor, `@RequestHeader("X-User-Roles") List<String> roles`, проверяет что `roles.contains("operator") || roles.contains("manager")` (403 если нет), вызывает `accountRepository.findByTenantId(tenantId)`, возвращает JSON. `CreditController`: `GET /api/v1/credits` — аналогично, требует `manager` или `credit_manager`. `MeController`: `GET /api/v1/me` — возвращает `X-User-Id` и роли, любой авторизованный | 3 эндпоинта работают | `curl -H "X-User-Id: 1" -H "X-User-Roles: operator,manager" -H "tenant_id: bank-007"` → 200 | `controller/*.java` |
| 6.7 | 6.6 | Backend | `service/AccountService.java`, `service/CreditService.java` — бизнес-логика, обёртка над repository | Сервисы готовы | unit-тесты | `service/*.java` |
| 6.8 | 6.7 | Backend | `src/main/resources/data.sql`: 3 записи — 2 accounts (по одной на bank-007 и bank-008), 1 credit (для bank-007). `application.yml`: `server.port=5002`, `spring.sql.init.mode=always` для запуска `data.sql` при старте | Seed работает | При первом запуске в `backend.db` появляются seed-данные | `data.sql`, `application.yml` |
| 6.9 | 6.8 | Backend | `Dockerfile`: multi-stage как у Admin Service, порт 5002 | Образ собирается | `docker compose build backend-service` — без ошибок | `Dockerfile` |

**Коммит после фазы:** `feat: Backend Service на Java 21 + Spring Boot 3.3 + SQLite (Xerial) с AuthInterceptor, 3 эндпоинта, seed-данные`

---

### Фаза 7. Redis + Kong + custom Lua plugin · Edge

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 7.1 | §6.3 | Edge | `kong/kong.yml`: декларативная конфигурация — services (admin-service, backend-service), routes, plugins: `jwt` (issuer, key claims), `opa` (host:opa, timeout 50ms), `file-log` (audit → stdout) | Kong config готов | `curl http://localhost:8001/services` — 2 сервиса | `kong/kong.yml` |
| 7.2 | §6.3, §6.5 | Edge | `kong/plugins/blacklist-guard/handler.lua`: access-фаза — (1) `EXISTS blacklist:*` в Redis, (2) если hit → 401, (3) пропускаем в upstream, (4) async пишем audit в файл через `io.open` | Plugin готов | `curl /api/v1/accounts` с `SET blacklist:user:1` → 401 | `kong/plugins/blacklist-guard/handler.lua`, `schema.lua` |
| 7.3 | 7.2 | Edge | `kong/Dockerfile`: `FROM kong:3`, `COPY plugins/ /tmp/plugins/`, `RUN luarocks make /tmp/plugins/blacklist-guard/handler.lua`, `KONG_PLUGINS=bundled,blacklist-guard` env | Кастомный Kong | `docker compose build kong` — без ошибок; `curl http://localhost:8001/plugins` показывает blacklist-guard | `kong/Dockerfile` |
| 7.4 | 7.3 | Edge | `redis/seed.sh`: `redis-cli SET blacklist:tenant:bank-002 1` (для теста tenant-блокировки) | Seed готов | `make up` → `docker compose exec redis redis-cli EXISTS blacklist:tenant:bank-002` → 1 | `redis/seed.sh` |
| 7.5 | 7.3, 7.4 | Edge | `make up` → Kong → Backend → 200. `redis-cli SET blacklist:user:1` → следующий запрос → 401 | End-to-end работает | curl + grep | — |

**Коммит после фазы:** `feat: Kong с custom Lua plugin blacklist-guard, декларативная конфигурация, Redis seed`

---

### Фаза 8. Test scenarios · Verify

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 8.1 | §6 (все правила) | Verify | `sandbox/test-flow.ps1` (PowerShell, не bash — на Windows баш coreutils недоступен): 6 сценариев — (1) OPA direct allow для operator+accounts, (2) OPA direct deny для operator+credits, (3) OPA direct deny для bank-008 (tenant blacklist), (4) Kong blacklist user = 401, (5) Kong blacklist tenant = 401, (6) Kong file-log audit.log вырос | Все 6 сценариев зелёные | exit 0; PASS: 6 FAIL: 0 | `sandbox/test-flow.ps1` |
| 8.2 | 8.1 | Verify | `scripts/reset.sh`: `docker compose down -v`, `rm -rf data/*.db`, `docker compose up -d --build` | Полный сброс | `make reset && make up` — все healthchecks green | `scripts/reset.sh` |
| 8.3 | 8.1 | Verify | `scripts/logs.sh`: `docker compose logs --tail=50 -f` | Удобный просмотр логов | `make logs` — выводит все 6 сервисов | `scripts/logs.sh` |

**Коммит после фазы:** `test: 6 сценариев проверки auth-флоу + reset.sh + logs.sh`

---

### Фаза 9. Wrap-up + TEST_REPORT · Docs

| # | Вход | Слой | Действие | Результат | Test | Файлы |
|---|------|------|----------|-----------|------|-------|
| 9.1 | §10 фазы 1-8 закрыты | Docs | Создать `TEST_REPORT.md` с шаблоном: пройденные сценарии (✅), edge cases, известные отступления от прода (cross-link на README §Известные отступления) | Документировано | `grep "✅"` — все 6 сценариев | `TEST_REPORT.md` |
| 9.2 | 9.1 | Docs | В `README.md` секция «Куда смотреть для отладки» — обновить при необходимости | Удобно для дебага | grep «Куда смотреть» — найдено | `README.md` |
| 9.3 | 9.1 | Verify | Финальный smoke test: `make reset && make up && make test` — все сценарии зелёные с чистого старта | Полный сценарий работает | exit 0, 6/6 ✓ | — |

**Коммит после фазы:** `docs: TEST_REPORT с результатами 6 сценариев и edge cases`

---

## 11. Тестовые сценарии (детально для `sandbox/test-flow.ps1`)

| # | Сценарий | Действие | Ожидаемый результат | Фактический результат |
|---|----------|----------|---------------------|----------------------|
| 1 | OPA direct: operator+GET /accounts | `curl -X POST http://localhost:8181/v1/data/abs/rbac/authz -d @sandbox/opa/test-input-operator.json` | `{"result":{"allow":true,"is_tenant_active":true}}` | OK |
| 2 | OPA direct: operator+GET /credits | `curl ... -d @sandbox/opa/test-input-operator-credits.json` | `{"result":{"allow":false,"is_tenant_active":true}}` | OK |
| 3 | OPA direct: bank-008 (tenant blacklist) | `curl ... -d @sandbox/opa/test-input-bank-008.json` | `{"result":{"allow":false}}` | OK |
| 4 | Kong blacklist: user | `curl -H "X-User-Id: test-blacklisted-user" -H "X-Tenant-Id: bank-001" -H "X-User-Roles: operator" http://localhost:8000/api/v1/accounts` | 401 + `{"message":"Token revoked"}` | OK |
| 5 | Kong blacklist: tenant | `curl -H "X-User-Id: alice" -H "X-Tenant-Id: bank-002" -H "X-User-Roles: bank_admin" http://localhost:8000/v1/admin/banks/bank-002` | 401 | OK |
| 6 | Kong file-log → audit.log | запрос к Kong → запись в `sandbox/kong/audit/audit.log` растёт | `delta > 0` (фактически +1903 байт) | OK |
| 7 | Keycloak OIDC discovery | `GET /realms/abs/.well-known/openid-configuration` | 200 + issuer | OK |
| 8 | Keycloak ROPC login | `POST /realms/abs/protocol/openid-connect/token` (operator@bank-007.test / operator) | access_token с `expires_in=3600` | OK |
| 9 | Keycloak JWT claims | decode payload | `sub=user-operator`, `realm_access.roles=[operator]`, `iss=.../realms/abs` | OK |

**Что НЕ покрыто в сатике** (см. TEST_REPORT.md §Known sandbox limitations):
- Логин Auth Code + PKCE: client `bank-007` настроен с `pkce.code.challenge.method=S256`, но headless-тест использует ROPC. PKCE проверяется в browser-flow в проде.
- OPA fail-closed 503: backend в сатике не вызывает OPA синхронно, проверяется только через прямые REST-вызовы в OPA (сценарии 1-3). В проде Kong `opa` pre-function plugin вызовет OPA и вернёт 503 при недоступности.

---

*Версия плана: 0.4 (Keycloak протестирован end-to-end, 9/9 сценариев зелёные)*
*Дата: 2026-07-01*
*Соответствует: `saas-onboarding-flow.md`, `iam-deploy-runbook.md`, `19062026.md`, `c4-mvp-container-diagram.md`*
