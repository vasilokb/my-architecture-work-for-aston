# Auth Sandbox — локальный стенд auth/authz Облачной АБС

> 📋 **Сценарии проверки и план реализации** зафиксированы в [`docs/plan.md`](docs/plan.md) — раздел «Что из себя представляет» содержит описание сценариев, а «Фазы и шаги» разбивает работу на исполнимые шаги. Архитектурный контекст (откуда этот стенд) — в [`D:\Астон\evergreen\git\abs\docs\meetings\saas-onboarding-flow.md`](D:\Астон\evergreen\git\abs\docs\meetings\saas-onboarding-flow.md) и [`D:\Астон\evergreen\git\abs\docs\mvp-abs\c4-mvp-container-diagram.md`](D:\Астон\evergreen\git\abs\docs\mvp-abs\c4-mvp-container-diagram.md).

## О проекте

**Auth Sandbox** — локальный docker-compose стенд, который воспроизводит архитектуру auth/authz Облачной АБС в упрощённом виде. Задача стенда — дать возможность руками пройти ключевые сценарии (логин, авторизация, blacklist, refresh, fail-closed) и убедиться, что архитектурные решения работают как описано.

**Это НЕ полная ABS.** Только auth/authz подсистема: Keycloak, Kong, OPA, Redis, Admin Service, Backend Service. Бизнес-логика счетов, кредитов, платежей — замокана на двух эндпоинтах Backend Service.

**Сценарий использования:** архитектор или разработчик поднимает стенд, проходит 6 проверочных сценариев из `scripts/test-flow.sh`, видит как работает каждый уровень защиты. Используется для:
- Демонстрации архитектуры коллегам
- Проверки, что изменения в Rego-политике не сломали flow
- Отладки интеграций (что если blacklist протух, что если OPA не отвечает)
- Онбординга новых разработчиков в auth/authz

## Стек

- **Docker + Docker Compose** — развёртывание всех сервисов одной командой.
- **Keycloak** (Quarkus-дистрибутив, `quay.io/keycloak/keycloak`) — IdP, выпуск JWT. Realm `abs` импортируется из `keycloak/realm-export.json`.
- **Kong** OSS (`kong:3`) — API Gateway. Custom Lua plugin (`blacklist-guard`) для blacklist + audit.
- **Open Policy Agent** (`openpolicyagent/opa`) — PDP. Rego-политика `abs.rbac.authz` в `opa/policies/`.
- **Redis 7** — blacklist JWT + (опционально) JWKS cache.
- **Java 21** (LTS) + **Spring Boot 3.3** + **Spring Data JPA** + **SQLite** (через Xerial JDBC) — Admin Service и Backend Service. 1:1 с production docs (тоже Java/Spring Boot) по стеку. SQLite вместо PostgreSQL упрощает локальный стенд; RLS эмулируется через `WHERE tenant_id=?` на каждом запросе.
- **Maven** — сборка (multi-stage Dockerfile с `maven:3.9-eclipse-temurin-21` для сборки и `eclipse-temurin:21-jre` для runtime).
- **Bash** + **curl** + **jq** — скрипты `scripts/test-flow.sh` (6 сценариев), `scripts/reset.sh`.

**Без** Python, без Kafka, без OPA Bundle Server (в сатике Admin Service сам пушит `data.json` в OPA через `PUT /v1/policies/bundle`), без Istio Service Mesh (mTLS не реализован, помечено как отступление), без HA / replicas.

## Структура проекта

```
sandbox/
├── README.md                          # этот файл
├── docs/
│   └── plan.md                        # сценарии + план реализации по фазам
├── docker-compose.yml                 # все сервисы стенда
├── .env.example                       # пример .env для docker-compose
├── keycloak/
│   ├── realm-export.json              # realm abs с тестовыми пользователями и ролями
│   └── Dockerfile                     # импорт realm при старте
├── opa/
│   ├── policies/abs/rbac/authz.rego   # Rego-политика (тот же что в runbook)
│   └── data.json                      # начальный снимок маппингов
├── admin-service/                     # Java 21 + Spring Boot, IAM CRUD
│   ├── pom.xml
│   ├── src/main/java/ru/abs/sandbox/admin/
│   │   ├── AdminApplication.java
│   │   ├── controller/BankController.java
│   │   ├── controller/RoleController.java
│   │   ├── service/BankService.java
│   │   ├── service/RoleService.java
│   │   ├── service/OpaPublisherService.java
│   │   ├── repository/BankRepository.java
│   │   ├── repository/RolePermissionRepository.java
│   │   ├── model/Bank.java
│   │   ├── model/RolePermission.java
│   │   └── config/RestTemplateConfig.java
│   ├── src/main/resources/
│   │   ├── application.yml
│   │   └── data.sql                   # seed (опционально)
│   └── Dockerfile                     # multi-stage Maven → JRE
├── backend-service/                  # Java 21 + Spring Boot, mock АБС
│   ├── pom.xml
│   ├── src/main/java/ru/abs/sandbox/backend/
│   │   ├── BackendApplication.java
│   │   ├── controller/AccountController.java
│   │   ├── controller/CreditController.java
│   │   ├── controller/MeController.java
│   │   ├── interceptor/AuthVerificationInterceptor.java
│   │   ├── service/AccountService.java
│   │   ├── service/CreditService.java
│   │   ├── repository/AccountRepository.java
│   │   ├── repository/CreditRepository.java
│   │   ├── model/Account.java
│   │   └── model/Credit.java
│   ├── src/main/resources/
│   │   ├── application.yml
│   │   └── data.sql                   # seed
│   └── Dockerfile                     # multi-stage Maven → JRE
├── kong/
│   ├── kong.yml                       # декларативная конфигурация: services, routes, plugins
│   ├── plugins/
│   │   └── blacklist-guard/          # custom Lua plugin
│   │       ├── handler.lua            # blacklist в Redis + audit в файл
│   │       └── schema.lua
│   └── Dockerfile                     # сборка Kong с custom plugin
├── redis/
│   └── seed.sh                        # предзаполнение blacklist для теста
├── scripts/
│   ├── test-flow.sh                   # 6 проверочных сценариев
│   ├── reset.sh                       # сброс стенда
│   └── logs.sh                        # tail всех логов в одном окне
├── Makefile                           # make up / make test / make reset / make logs
└── data/                              # SQLite-файлы (создаются при первом запуске)
    ├── admin.db
    └── backend.db
```

## Как запустить проект на macOS / Linux

```bash
# Требования: Docker Desktop ≥ 4.0, docker compose plugin
docker --version
docker compose version

# Переход в папку
cd git/abs/sandbox/

# Копирование .env.example
cp .env.example .env

# Запуск всех сервисов (первый запуск ~3-5 минут на скачивание образов и сборку Java-сервисов)
docker compose up -d --build

# Дождаться, пока Keycloak станет healthy (~30 сек)
docker compose logs -f keycloak | grep "started in"

# Запуск проверочных сценариев
make test

# Просмотр логов всех сервисов
make logs
```

Откройте в браузере:
- **Keycloak Admin Console:** http://localhost:8080 (admin / admin)
- **Kong Admin API:** http://localhost:8001
- **OPA REST API:** http://localhost:8181

## Как запустить проект на Windows (PowerShell)

```powershell
# Требования: Docker Desktop ≥ 4.0
docker --version
docker compose version

# Запуск
cd D:\Астон\evergreen\git\abs\sandbox
Copy-Item .env.example .env
docker compose up -d --build

# Дождаться Keycloak
docker compose logs keycloak | Select-String "started in"

# Проверочные сценарии
make test

# Логи
make logs
```

## Что проверяет `make test` (6 сценариев)

1. **Логин через Auth Code + PKCE** — UI → Keycloak, получение JWT + refresh_token.
2. **Обычный запрос operator** — `GET /api/v1/accounts` с JWT → 200 OK.
3. **Запрет по роли** — `GET /api/v1/credits` с JWT operator → 403 Forbidden.
4. **Blacklist в Redis** — `SET blacklist:user:{user_id}` → следующий запрос → 401 Unauthorized.
5. **OPA fail-closed** — остановить OPA → следующий запрос → 503 Service Unavailable.
6. **Auth-audit** — после каждого сценария в `data/audit.log` появляется запись `allow/deny + tenant + user + method`.

## Границы MVP

В текущий стенд **НЕ входит**:

- **HA и репликация.** Каждый сервис — один экземпляр. В проде — OPA 2-3 реплики, Kong 2+ реплики, Redis Sentinel/Cluster.
- **OPA Bundle Server как отдельный микросервис.** В сатике Admin Service сам делает `PUT /v1/policies/bundle` в OPA. В проде — выделенный сервис с cron-джобом 5 минут.
- **Kafka для auth-audit.** В сатике audit пишется в `data/audit.log` (файл, асинхронно через stdout). В проде — Kafka topic `auth-audit` → Audit Service → ClickHouse.
- **PostgreSQL с реальным RLS.** В сатике — SQLite через Xerial JDBC, RLS эмулируется через `WHERE tenant_id=?` на каждом запросе. В проде — PostgreSQL + `SET LOCAL app.current_tenant` + реальный Row-Level Security.
- **Istio Service Mesh + mTLS.** В сатике Kong → backend по HTTP (без mTLS). В проде — Istio обеспечивает mTLS между всеми сервисами внутри кластера.
- **Service-to-service auth через service-account токены.** В сатике backend-сервисы доверяют `X-User-Roles` (решение #9 протокола). В проде для критичных операций — доп. проверка tenant_id внутри сервиса.
- **Refresh token ротация, logout-all-sessions, Keycloak revoke.** В сатике refresh идёт напрямую, но без сложных сценариев отзыва.
- **Healthchecks, мониторинг, метрики Prometheus, трейсинг.** Стенд для ручной проверки, не для прода.

## Известные отступления от прода

### 1. Admin Service сам пушит bundle в OPA (без OPA Bundle Server)

В сатике Admin Service делает синхронный `PUT /v1/policies/bundle` в OPA при каждом изменении `role_permissions`. В проде это делает выделенный **OPA Bundle Server** с cron-джобом 5 минут (fallback). В сатике cron-джоба нет — если OPA упадёт между изменениями, нужно вручную дёрнуть `trigger`.

### 2. Auth-audit пишется в файл, не в Kafka

В сатике Lua-плагин Kong пишет audit-события в `data/audit.log` через `tail -f` в stdout контейнера. В проде — Kafka topic `auth-audit` с retention 90 дней. Сборка через `Filebeat → Logstash → ClickHouse` или аналог.

### 3. SQLite вместо PostgreSQL + реального RLS

В сатике каждая таблица в `backend.db` имеет `tenant_id` (для всех тенантов, потому что у нас два тенанта: test-bank-001 и test-bank-002). Запросы фильтруют `WHERE tenant_id=?` на уровне кода (`@Query` в Spring Data JPA). В проде — PostgreSQL + Row-Level Security через `SET LOCAL app.current_tenant`, что делает изоляцию **прозрачной** для приложения.

### 4. mTLS между сервисами не реализован

В сатике Kong → backend по plain HTTP. В проде — Istio Service Mesh обеспечивает mTLS между всеми сервисами внутри кластера. В сатике это не нужно: трафик не уходит за пределы `docker compose`.

### 5. Custom Lua plugin для Kong, а не встроенный плагин opa

В сатике Kong использует встроенный `opa` plugin (есть в Kong 3.x) для вызова OPA, плюс custom Lua plugin `blacklist-guard` для blacklist. В проде архитектура та же: один custom плагин + стандартные плагины Kong. В сатике custom плагин упрощён — не покрывает все edge cases (асинхронный produce в Kafka, health-checks).

## Где лежат данные

| Что | Где | Создаётся |
|-----|-----|-----------|
| `admin.db` (SQLite, `role_permissions`, `banks`) | `sandbox/data/admin.db` | При первом запуске Admin Service (Spring Data JPA `ddl-auto: update`) |
| `backend.db` (SQLite, `accounts`, `credits`) | `sandbox/data/backend.db` | При первом запуске Backend Service |
| Redis данные | Внутри контейнера `redis` | Потеряются при `docker compose down` без volume |
| `audit.log` (auth-аудит) | `sandbox/data/audit.log` | Пишется при каждом запросе через Kong |
| Keycloak realm `abs` | Внутри контейнера `keycloak` | Импортируется из `realm-export.json` при первом старте |

## Сброс стенда

```bash
# Полный сброс: остановить, удалить volumes, пересоздать
make reset
```

Это удалит все SQLite-файлы, Redis-данные, Keycloak realm (импортируется заново). После `reset` — снова `make up` и `make test`.

## Где смотреть для отладки

| Симптом | Куда смотреть |
|---------|---------------|
| 401 на валидный JWT | `docker compose logs kong` — проверка JWKS cache + подпись |
| 403 на запрос operator | `docker compose logs opa` — Rego-политика + bundle |
| 503 на любой запрос | `docker compose logs opa` — OPA недоступна (fail-closed) |
| Blacklist не работает | `docker compose logs kong` — Lua plugin + Redis |
| Audit не пишется | `tail -f data/audit.log` + `docker compose logs kong` |
| Keycloak не отвечает | `docker compose logs keycloak` — статус запуска |
| OPA bundle не применился | `curl localhost:8181/v1/policies/abs` — текущий bundle |
| Admin Service упал при сборке | `docker compose logs admin-service` — Java stacktrace |
| Backend Service 500 | `docker compose logs backend-service` — Spring stacktrace |

---

*Версия: 0.2 (стек изменён на Java 21 + Spring Boot 3.3)*
*Согласовано с: `saas-onboarding-flow.md`, `19062026.md`, `iam-deploy-runbook.md`, `c4-mvp-container-diagram.md`*
