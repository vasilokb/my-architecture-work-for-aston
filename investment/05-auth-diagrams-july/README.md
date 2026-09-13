# Авторизация и аутентификация — схемы (PlantUML)

**Дата:** 2026-07-23
**Источник:** анализ `backend/auth-service`, `client/backend/customer-service` и **`client/aqa/` (AQA-тесты — источник истины о реальном клиентском потоке)**. Исходники SPA (`react-service`) и API Gateway локально не выкачаны (только `.git` + README), поэтому клиентский поток восстановлен по AQA.
**Положение:** AS-IS (как реализовано/работает в коде).

---

## Состав схем

### Диаграммы контейнеров (сервисы-участники)

| Файл | Содержание |
|---|---|
| [`auth-containers-client.puml`](./auth-containers-client.puml) | **C2** — авторизация инвестора с разделением **ФРОНТЕНД ↔ БЭКЕНД**: какие сервисы участвуют (Keycloak=IdP, SPA=OAuth-клиент, Gateway=PEP, customer/otp=сервисы авторизации, downstream доверяют PEP, Redis, PG) + нумерация шагов и таблица «кто за что отвечает» |
| [`auth-overview.puml`](./auth-overview.puml) | **C2** — обзор обоих потоков (клиент / сотрудник), точки входа, хранилища, IdP |

### Диаграммы компонентов (декомпозиция сервисов)

| Файл | Содержание |
|---|---|
| [`auth-components-employee.puml`](./auth-components-employee.puml) | Декомпозиция **auth-service** на компоненты по слоям: Web → Application → Domain logic → Infrastructure (utils/kafka/config) → auth_db. Контроллеры, сервисы-оркестраторы, RBAC, JWT, OTP, Kafka |
| [`auth-components-client.puml`](./auth-components-client.puml) | Декомпозиция **customer-service** (авторизация инвестора) на компоненты: контроллеры, AuthService/OTPService, стратегии OTP, JwtProvider/Filter, Redis, PostgreSQL + Keycloak |

### Диаграммы последовательности (поведенческие)

| Файл | Содержание |
|---|---|
| [`auth-employee-login.puml`](./auth-employee-login.puml) | Вход сотрудника: двухфакторная аутентификация (`/authentication/initiate` → OTP → `/authentication/confirm` → выпуск JWT) |
| [`auth-token-lifecycle.puml`](./auth-token-lifecycle.puml) | Жизненный цикл токена сотрудника и RBAC: refresh, verify, deserialize role/permissions, `/access/verify`, logout |
| [`auth-data-model.puml`](./auth-data-model.puml) | ER-модель `auth_db`: Employee, Credentials, Session, Role, Permission, EventCode, AuditLog |
| [`auth-client-login.puml`](./auth-client-login.puml) | Вход инвестора: **Keycloak Password Grant** + регистрация/2FA через customer-service + refresh |

Откройте `.puml` в любом инструменте с поддержкой PlantUML (IDE-плагин, plantuml.com, CLI `plantuml *.puml`).
Компонентные и обзорная схемы используют стандартную библиотеку **C4-PlantUML** (`C4_Component.puml` / `C4_Container.puml`, подключается через `!include` из сети).

---

## Два потока аутентификации — краткая сводка

| Аспект | Инвестор | Сотрудник |
|---|---|---|
| **IdP / сервис** | **Keycloak** (`:30803`, realm test-BE) + `customer-service` | `auth-service` |
| **Механизм** | **OAuth 2.0 Password Grant** (Keycloak выпускает JWT) | Собственный JWT (jjwt, HS256) |
| **Фильтр в Gateway** | `JwtFilter` (17 маршрутов) — валидирует Keycloak-токен | `AuthJwtFilter` (2 маршрута: auth, employee) |
| **Identity в токене** | `sub = customerId`, `scope` (profile), issuer = realm Keycloak | `employee_id`, `roles`, `rights[]` |
| **Заголовки downstream** | `customer_id` | `customer_id` + `x-role` + `x-permissions` |
| **Хранение токенов** | SPA: access → `localStorage`, refresh → HttpOnly-cookie | PostgreSQL (таблица `Session`) |
| **Участие customer-service** | registration, OTP/2FA, `/refresh-token` (обмен с Keycloak) | — |
| **TTL access / refresh** | ≈ 5 мин / 30 мин (Keycloak) | 15 мин / 540 мин |
| **2FA** | Опциональная (email/phone), таблица `Verification` | Обязательная (EventCode + OTP), 6 цифр, TTL 1 мин |
| **Пароли** | BCrypt (registration) / учётки в Keycloak user-store | **plaintext** (сравнение строкой) |
| **RBAC** | нет (идентификация по customerId) | Role → Permission (4 роли) |
| **Legacy** | в customer-service остался собственный HS256-JWT (`/auth`, JwtProvider, Redis) | нет |

---

## Keycloak — РЕАЛЬНЫЙ IdP клиентов (исправлено)

> **Важно:** более ранние версии этих схем ошибочно утверждали, что Keycloak не используется.
> Это было следствием того, что анализ ограничился бэкендом `customer-service`, а **исходники
> SPA и API Gateway не выкачаны локально** (в `react-service` и `api-gateway` только `.git` + README).
> Реальный поток восстановлен по **AQA-тестам** (`client/aqa/`) — источнику истины для «как реально работает».

`ARCHITECTURE-OVERVIEW.md` §8.1 заявляет аутентификацию клиентов через **Keycloak (OAuth 2.0)** —
и код это **подтверждает**:

### Доказательства из AQA (`client/aqa/practice-investment_aqa`)

- `BaseUrls.java:9,14` — `KEY_CLOAK = http://172.17.1.26:30803`
- `KeyCloakServiceRequests.java:13-21` — **Password Grant**: `POST /auth/realms/test-BE/protocol/openid-connect/token`,
  `client_id=token_client`, `grant_type=password`, `client_secret=...`
- `AuthService.java:17,26` — берёт `access_token` из ответа Keycloak → используется как `Bearer` против API Gateway
- `RefreshValidator.java:23,49` — JWT `iss = http://172.17.1.26:30803/auth/realms/test-BE`, `scope` содержит `profile`
  → **токен выпускает Keycloak**
- FE-тесты — `localStorage.getItem('access_token')` → SPA хранит Keycloak-JWT в localStorage

### Как это уложено

1. **Логин:** SPA → Keycloak (Password Grant) → `access_token` (issuer = realm) в `localStorage`.
2. **Запросы:** SPA → API Gateway (`Bearer {keycloak access}`) → `JwtFilter` валидирует Keycloak-токен →
   заголовок `customer_id` → downstream-сервисы.
3. **Refresh:** SPA → `customer-service /refresh-token` (cookie `refresh_token`) → обмен с Keycloak →
   новый `access_token` + обновлённая HttpOnly-cookie.
4. **Регистрация / OTP / 2FA:** через `customer-service` (`/registration`, `/otp`, `/otp/verify`).

### Сосуществование (legacy)

В `customer-service` **сохранилась собственная HS256-JWT-логика** (`JwtProvider`, `JwtFilter`, BCrypt, эндпоинт `/auth`,
Redis-хранилище `tokens:{customerId}`). Это legacy-путь, частично вытеснённый миграцией на Keycloak:
`/refresh-token` уже возвращает Keycloak-токены (issuer = Keycloak), а `/auth` + `JwtProvider` остались как параллельный механизм.

### Отдельно: `keycloak-service` (скелет)

`client/backend/keycloak-service` — отдельный Kotlin-модуль (Spring Boot **4.0.6**, Java 21, новее проекта),
в `build.gradle.kts:36-37` объявлены `keycloak-admin-client:24.0.5` + `keycloak-core`, но **реализации нет**
(пустой `@SpringBootApplication`, пустой `application.yaml`, дефолтный README). Не инвентаризирован в
`ARCHITECTURE-OVERVIEW.md §5.1`, не подключён к `customer-service`. Вероятно — будущая обёртка/прокси к IdP.

---

## Риски безопасности (AS-IS)

Заимствовано из `ARCHITECTURE-OVERVIEW.md §12.4` и подтверждено кодом:

1. **Пароли сотрудников хранятся в открытом виде** — `CredentialsEntity.password`, сравнение `equals()` в `AuthEmployeeServiceImpl.editPassword` и `AuthVerificationServiceImpl.checkAttempts`. Клиентские пароли при этом — BCrypt.
2. **Захардкоженные секреты** — JWT-секрет auth-service по умолчанию `[redacted]` (`application-dev.yaml`), Keycloak-админ `[redacted]` в api-gateway.
3. **`.block()` в реактивном API Gateway** — `JwtFilter`/`AuthJwtFilter` блокируют Netty event-loop thread → каскадные задержки под нагрузкой.
4. **Симметричная подпись HS256** — любой downstream-сервис, знающий секрет, может выпускать валидные токены (RS256/асимметрия не используется).
5. **Отзыв токена = флаг-строка** `"logout"` в БД, без blacklist по `jti`; одна `Session` на сотрудника (вход с нового устройства перезаписывает сессию).
6. **`criticalfeedbackchannel`** — публичные эндпоинты без авторизации (вектор DoS).
7. **Нет rate limiting** на API Gateway.

---

## Источники в коде

- **auth-service:**
  - Контроллеры: `web/impl/AuthFreeControllerImpl.java`, `web/impl/AuthEmployeesControllerImpl.java`
  - Логин: `service/impl/AuthTokenServiceImpl.java:46` (`login`), `:116` (`authorization`)
  - Доступ/RBAC: `service/impl/AuthAccessServiceImpl.java:42` (`verifyAccess`), `:73` (`checkRole`)
  - OTP/события: `service/impl/AuthEventServiceImpl.java`, `service/impl/AuthVerificationServiceImpl.java`
  - JWT: `utils/impl/ProcessingTokenUtilImpl.java:98` (`generateToken`), `:118` (`deserializeToken`)
  - Конфиг URL: `src/main/resources/application-dev.yaml:29-67`
  - Security: `config/SettingSecurityManagement.java` (всё под `/api/v1/auth-service/**` → `permitAll`, токен проверяется внутри сервисов)
- **AQA-тесты (источник истины о клиентском потоке):** `client/aqa/practice-investment_aqa/`
  - `src/main/java/org/liberty/constants/apiEndpoints/BaseUrls.java:9,14` — `KEY_CLOAK = :30803`
  - `src/main/java/org/liberty/requests/services/KeyCloakServiceRequests.java:13-21` — Password Grant
  - `src/main/java/client/AuthService.java:17,26` — `getAccessToken()` → Keycloak → Bearer
  - `src/main/java/org/liberty/validations/customerService/RefreshValidator.java:23,49` — issuer=Keycloak, scope=profile
- **customer-service (legacy JWT + регистрация/OTP/refresh):** `client/backend/customer-service/`
  - Security: `configuration/SecurityConfiguration.java:42-49`
  - Логин/refresh: `service/impl/AuthServiceImpl.java`
  - JWT (legacy): `util/JwtProviders.java:27` (`generate`), `util/JwtFilter.java`
  - 2FA/OTP: `service/impl/OTPServiceImpl.java`, `strategy/impl/AuthOtpCheckStrategy.java`
  - Хранилище: `repository/impl/RedisRepositoryImpl.java:39`
- **keycloak-service** (скелет, не реализован): `client/backend/keycloak-service/`
  - `build.gradle.kts:36-37` — объявлены `keycloak-admin-client:24.0.5`, `keycloak-core`
  - `src/main/kotlin/.../KeycloakServiceApplication.kt` — единственный класс (пустой)
  - `src/main/resources/application.yaml` — только `spring.application.name`
  - не инвентаризирован в `ARCHITECTURE-OVERVIEW.md §5.1`
