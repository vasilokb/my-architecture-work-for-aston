# Аудит архитектуры проекта Liberty Investment

**Дата:** 2026-05-23  
**Аудитор:** Kilo (автоматизированный аудит)  
**Область:** Полный аудит всех 7 разделов + безопасность

---

## Содержание

1. [Критические проблемы](#1-критические-проблемы)
2. [Аудит бэкенда — Общая структура](#2-аудит-бэкенда--общая-структура)
3. [API Gateway](#3-api-gateway)
4. [Межсервисное взаимодействие](#4-межсервисное-взаимодействие)
5. [Структура сервисов и данные](#5-структура-сервисов-и-данные)
6. [Библиотеки и стартеры](#6-библиотеки-и-стартеры)
7. [Аудит фронтенда](#7-аудит-фронтенда)
8. [Связанность client/backend и backend/](#8-связанность-clientbackend-и-backend)
9. [Инфраструктура и DevOps](#9-инфраструктура-и-devops)
10. [Тестирование](#10-тестирование)
11. [Безопасность](#11-безопасность)
12. [Код-стайл и качество](#12-код-стайл-и-качество)
13. [Сильные стороны](#13-сильные-стороны)
14. [Рекомендации с приоритетами](#14-рекомендации-с-приоритетами)
15. [Архитектурная диаграмма](#15-архитектурная-диаграмма)

---

## 1. Критические проблемы

### 1.1. Hardcoded Credentials (CRITICAL)

В исходном коде найдены захардкоженные секреты (значения в публичную копию не включены):

| Секрет | Файл |
|--------|------|
| Keycloak admin password (fallback) | `api-gateway/application.yaml` |
| Keycloak client secret (fallback) | `api-gateway/application.yaml` |
| Nexus password (fallback) | 6+ `build.gradle` файлов |
| JWT secret (admin) | `auth-service/application-dev.yaml` |
| JWT secret (client) | `document-service-pb/application.yaml`, `account-service-test/application.yaml` |
| JWT secret (customercare) | `customercare-service/application.yaml` (**без env fallback**) |
| Frontend JWT token | `react-service/.env` |

**Рекомендация:** Немедленно удалить все fallback-значения секретов. Использовать только env variables без defaults.

### 1.2. Outbox Batch Send Disabled (CRITICAL)

В `trading-service` метод `sendStatusChangeNotificationBatch()` содержит закомментированный вызов `sendBatchMessages()`. Это означает, что **события изменения статуса ордеров (executed, rejected, expired, cancelled) никогда не публикуются в Kafka**.

### 1.3. API Gateway: Blocking Calls in Reactive Context (HIGH)

`JwtFilter` и `AuthJwtFilter` используют `.block()` внутри WebFlux-фильтров. Это блокирует Netty event loop thread и может вызвать каскадные задержки под нагрузкой.

### 1.4. API Gateway: No Rate Limiting (HIGH)

Отсутствует конфигурация rate limiting на уровне API Gateway. Любой клиент может отправлять неограниченное количество запросов.

### 1.5. Kubernetes: No Resource Limits, No Health Probes (HIGH)

Ни один сервис не определяет resource requests/limits или health probes в Helm values. Это означает:
- Pods могут потреблять неограниченные ресурсы
- Kubernetes не может определить готовность сервиса
- Нет защиты от OOM kills

---

## 2. Аудит бэкенда — Общая структура

### 2.1. Инвентаризация сервисов

Проект содержит **28 активных сервисов** (17 в `backend/`, 7 в `client/backend/`, 4 shared-библиотеки):

#### backend/ (21 директория)

| # | Сервис | Group ID | Build DSL | Spring Boot | Статус |
|---|--------|----------|-----------|-------------|--------|
| 1 | api-gateway | `ru.aston` | Kotlin DSL | 3.5.0 | Активен |
| 2 | auth-service | `ru.aston.investment.admin` | Kotlin DSL | **3.5.5** | Активен |
| 3 | trading-service | `ru.aston.trading_service` | Groovy | 3.5.0 | Активен |
| 4 | education-service | `ru.aston.investment.educationservice` | Groovy | 3.5.0 | Активен |
| 5 | employee-service | `ru.aston` | Groovy | 3.5.0 | Активен |
| 6 | userinfo-service | `ru.aston.investment.admin` | Groovy | 3.5.0 | Активен |
| 7 | management-service-pb | `ru.aston.admin_domain.management_service` | Groovy | 3.5.0 | Активен |
| 8 | document-service-pb | `ru.aston` | Groovy | 3.5.0 | Активен |
| 9 | account-service-test | `com.astondevs` | Groovy | 3.5.0 | Активен |
| 10 | tax-service | `com.astondevs` | Groovy | 3.5.0 | Активен |
| 11 | support-service | `ru.aston` | Groovy | **3.5.6** | Частичный |
| 12 | financialtransactions-service | `ru.aston` | Groovy | 3.5.0 | Активен |
| 13 | customercare-service | `com.astondevs` | Groovy | 3.5.0 | Активен |
| 14 | newsfeed-service | `ru.aston.investment` | Groovy | 3.5.0 | Частичный |
| 15 | criticalfeedbackchannel | `org.example` | Groovy | 3.5.0 | Активен |
| 16 | test-service | `ru.aston.investment.test_service` | Groovy | 3.5.0 | Активен |
| 17 | logging-spring-boot-starter | `ru.aston` | **Maven** | **3.2.0** | Библиотека |
| 18 | account-service-pb | — | — | — | **Git submodule не инициализирован** |
| 19 | jwt-starter | — | — | — | **Git submodule не инициализирован** |
| 20 | keycloak-providers | — | — | — | **Git submodule не инициализирован** |
| 21 | backend/ | — | — | — | **Пустая директория** |

#### client/backend/ (7 сервисов)

| # | Сервис | Group ID | Build DSL | Spring Boot | Язык |
|---|--------|----------|-----------|-------------|------|
| 1 | account-service | `com.astondevs` | Groovy | 3.5.0 | Java |
| 2 | customer-service | `ru.aston` | Groovy | 3.5.0 | Java |
| 3 | catalog-service | `ru.aston` | Groovy | 3.5.0 | Java |
| 4 | document-service | `ru.aston` | Groovy | 3.5.0 | Java |
| 5 | emulator-service | `com.astondevs` | Groovy | 3.5.0 | Kotlin + Java |
| 6 | notification-service | `ru.aston.investment` | Groovy | 3.5.0 | Java |
| 7 | otp-service | `ru.aston` | Groovy | 3.5.0 | Java |

### 2.2. Дублирование и пересечение ответственности

| Пара сервисов | Проблема | Вердикт |
|---------------|----------|---------|
| `account-service-test` vs `account-service-pb` | Два варианта account-сервиса | `account-service-pb` — мёртвый submodule. `account-service-test` — активен |
| `document-service-pb` vs `client/backend/document-service` | Оба — документооборот | Разные домены: pb — partner bank (админ), client — клиентский |
| `customercare-service` vs `support-service` | Оба — клиентская поддержка | **Дублирование**: два конкурирующих impl одной доменной области |
| `management-service-pb` vs `employee-service` | Управление персоналом | Разные зоны: management — шире (MinIO, Feign), employee — узко (данные) |
| `backend/backend/` | Вложенный каталог | **Пустая директория** — удалить |

### 2.3. Фрагментация Group ID

Три различных конвенции именования group ID:
- `ru.aston.*` — большинство сервисов
- `com.astondevs` — account-service-test, tax-service, customercare-service, account-service, emulator-service
- `org.example` — criticalfeedbackchannel (placeholder)

### 2.4. Версионные нестыковки

| Зависимость | Версии | Сервисов затронуто |
|-------------|--------|--------------------|
| Spring Boot | 3.2.0, 3.5.0, 3.5.5, 3.5.6 | 3 сервиса |
| MapStruct | 1.5.5.Final, 1.6.3 | ~4 сервиса |
| Liquibase | 4.27.0, 4.29.2, 5.0.1 | ~6 сервисов |
| PostgreSQL driver | 42.7.7, 42.7.8, 42.7.9, 42.7.10 | ~8 сервисов |
| jjwt | 0.11.5, 0.13.0 | 4 сервиса |
| springdoc-openapi | 2.5.0, 2.6.0, 2.8.9, 2.8.14 | ~6 сервисов |

**Нет центрального BOM или parent Gradle проекта** для управления версиями.

---

## 3. API Gateway

### 3.1. Маршрутизация

- **38 маршрутов** (19 API + 19 Swagger-UI + 1 Keycloak direct)
- Все API-маршруты: `Path=/api/{version}/{service-name}/**`
- Service URL resolution через profile-specific placeholders
- Профили: `local` (localhost:8088), `dev` (172.17.1.26 NodePorts), Helm values (K8s intranet)

### 3.2. Аутентификация

Два фильтра:
- **JwtFilter** (клиентский) — introspection через Keycloak, inject `customer_id` header
- **AuthJwtFilter** (админский) — delegation к auth-service, inject `employeeId`, `role`, `permissions` headers

### 3.3. Проблемы

| # | Severity | Проблема |
|---|----------|----------|
| 1 | HIGH | `.block()` в reactive filters |
| 2 | HIGH | No rate limiting |
| 3 | HIGH | Hardcoded Keycloak credentials |
| 4 | MEDIUM | Circuit breaker `exampleCircuitBreaker` — мёртвая конфигурация, все маршруты используют default-ы |
| 5 | MEDIUM | Keycloak fallback `/fallback/keycloak-unavailable` — не обработан в FallbackController |
| 6 | MEDIUM | JDK 17 (build) vs JRE 21 (runtime) — нестыковка |
| 7 | MEDIUM | `spring-cloud-starter-zipkin:2.2.8.RELEASE` — устаревшая версия от Spring Cloud Hoxton |
| 8 | LOW | Swagger routes без аутентификации |
| 9 | LOW | 100% trace sampling в production |
| 10 | LOW | 4 варианта имени заголовка idempotency-key |

---

## 4. Межсервисное взаимодействие

### 4.1. Kafka Topic Map

#### Order Processing Pipeline
```
trading-service --(order_request)--> emulator-service
emulator-service --(order_result)--> trading-service [via Outbox]
emulator-service --(order_errors)--> trading-service
trading-service --(new_order, order_result_notification)--> notification-service
trading-service --(accounts_request, trade_history)--> account-service [client]
```

#### Asset Data Pipeline (MOEX)
```
emulator-service --(actual_stocks/bonds/currencies/options/forts)--> catalog-service
catalog-service --(actual_missing_request)--> emulator-service
emulator-service --(actual_missing_response)--> catalog-service
```

#### Notification Pipeline
```
otp-service --(otp_notification)--> notification-service
customer-service --(user_auth_notification, user_registration)--> notification-service
catalog-service --(favourite_price)--> notification-service
account-service --(account_changes_notification, margin_call_notification)--> notification-service
```

#### Auth Pipeline
```
auth-service --(register-account)--> employee-service --(register-result)--> userinfo-service
```

### 4.2. Feign Dependency Graph

```
customer-service (5 inbound Feign calls) ← account, document, notification, otp, customercare
account-service (6 inbound Feign calls) ← catalog, document, trading, tax, financial-tx, customercare
```

**Нет циклических Feign-зависимостей** — граф является DAG.

### 4.3. Проблемы

| # | Severity | Проблема |
|---|----------|----------|
| 1 | **CRITICAL** | Outbox batch send disabled в trading-service |
| 2 | **HIGH** | Только 2 из 26+ Kafka listeners имеют `@RetryableTopic` с DLT |
| 3 | **HIGH** | Нет idempotency guards в Kafka consumers |
| 4 | **MEDIUM** | `interservice-interaction-dto-lib` — 3 разные версии: `0.0.3`, `0.0.3a`, `0.0.3f` |
| 5 | **MEDIUM** | Нет circuit breakers на Kafka consumers |
| 6 | **MEDIUM** | Только catalog-service имеет Resilience4j retry для Feign |
| 7 | **MEDIUM** | `customer_blacklist` listener закомментирован в customer-service |
| 8 | **LOW** | `temporary-mock-topic` в auth-service — неполная интеграция |
| 9 | **LOW** | Нет консистентного correlation ID propagation |

---

## 5. Структура сервисов и данные

### 5.1. Внутренние архитектуры (сравнение)

| Аспект | trading-service | auth-service | document-service |
|--------|----------------|--------------|------------------|
| **Слои** | Controller→Service→Repository | Controller→Service→Logic→Storage (4 слоя) | Controller→Service→Repository |
| **Data Access** | Spring Data JPA + Redis | **JdbcTemplate** (core) + JPA (partial) | Spring Data JPA + JdbcTemplate (seq) |
| **Mapper** | MapStruct | Manual | MapStruct |
| **Exceptions** | Shared lib `@RestControllerAdvice` | Local `@ControllerAdvice` (25+ handlers) | Shared lib |
| **Validation** | `@Valid` + 4 custom validators | Custom imperative + JSR-380 (v2) | `@Valid` only |
| **Security** | Custom JwtFilter (null authorities) | SecurityFilterChain + Keycloak | None (gateway-trusting) |
| **Caching** | Redis + `@Cacheable` | None | Hibernate 2nd-level cache |
| **Liquibase** | YAML DSL, `YYYY-MM-DD-action-target` | Raw SQL, numeric IDs | YAML DSL, `YYYY-MM-DD-action-target` |

### 5.2. Ключевые проблемы

1. **auth-service:** Полностью на JdbcTemplate вместо JPA — высокая трудоёмкость поддержки, нетипичный паттерн для Spring Boot 3.x
2. **trading-service:** `JwtFilter` создаёт authentication с `null` authorities — нет role-based access внутри сервиса
3. **Duplicate shared libraries:** `exceptionhandlerstarter` **скопирован** в исходный код trading-service, test-service, tax-service вместо использования как зависимость
4. **auth-service:** 25+ exception classes без общего базового класса доменных ошибок
5. **document-service:** `@Query` содержит `SELECT d *` — невалидный JPQL (но метод переопределён default-ом)

---

## 6. Библиотеки и стартеры

### 6.1. Nexus Shared Libraries

| Библиотека | Версии в использовании | Назначение |
|------------|----------------------|------------|
| `interservice-interaction-dto-lib` | 0.0.3, 0.0.3a, 0.0.3f | Общие DTO для межсервисного взаимодействия |
| `liberty-investment-globalexceptionhandler-starter` | 0.0.5, 0.0.5b, 0.0.5c, 0.0.5db | Глобальная обработка исключений |
| `liberty-investment-otphandler-starter` | 0.0.10 | OTP интеграция |
| `liberty-bank-logger-starter` | 0.0.1 | Централизованное логирование |

### 6.2. Проблемы

1. **3 разные версии `interservice-interaction-dto-lib`** — риск несовместимости сериализации
2. **4 разные версии `globalexceptionhandler-starter`** — фрагментация
3. **exceptionhandlerstarter скопирован в исходники** сервисов вместо использования как зависимость
4. **jwt-starter и keycloak-providers** — git submodules не инициализированы

---

## 7. Аудит фронтенда

### 7.1. Технологический стек

| Категория | Технология | Версия |
|-----------|-----------|--------|
| Framework | React | 18.2.0 |
| Build | Vite | 4.4.9 |
| State | Redux Toolkit + RTK Query | 1.9.5 |
| Routing | React Router DOM | 6.16.0 |
| Forms | React Hook Form + Yup | 7.46.1 / 1.2.0 |
| Styling | SCSS Modules | 1.65.1 |
| Testing | Jest + Testing Library | 29.7.0 |

### 7.2. FSD Compliance

```
src/
  app/           ✓ Корректный корневой слой
  pages/         ✓ 22 страницы
  widgets/       ✓ 16 композитных блоков
  features/      ⚠ Только 4 фичи (недоиспользован)
  shared/        ⚠ Нарушения импортов (см. ниже)
```

### 7.3. Нарушения FSD (Layer Violations)

**SEVERE:** `shared/` импортирует из `pages/`:

| Файл | Импорт |
|------|--------|
| `shared/api/authApi/authApi.ts` | `@/pages/otpVerification/types` |
| `shared/api/accountApi/accountApi.ts` | `@/pages/otpVerification/types` |
| `shared/api/customerApi/customerApi.ts` | `@/pages/otpVerification/types` |
| `shared/api/closeBrokerAccountApi/...` | `@/pages/otpVerification/types` |
| `shared/hooks/usePhoneOrEmailField.ts` | `@/pages/Registration/constant` |

### 7.4. State Management

- 9 RTK Query API slices + 2 Redux slices (auth, pushNotifications)
- `serializableCheck: false` — отключены проверки сериализации
- `authSlice.afterAction` хранит **функцию** в state (non-serializable)
- Только `customerApi` использует cache tags — **8 API slices без инвалидации кэша**

### 7.5. API Layer

- `baseQuery.ts`: Невалидный Content-Type: `"application/json; application/pdf; text/event-stream"`
- OTP-паттерн дублируется в 4 API slices
- Token refresh с mutex (async-mutex) — корректная реализация
- SSE notifications с exponential backoff — хорошая реализация

### 7.6. Routing

- `createBrowserRouter` с lazy loading всех страниц — отлично для code splitting
- `PrivateRoutes` — простая проверка токена без обработки expiration
- Централизованные пути в `paths.ts`

### 7.7. Проблемы фронтенда

| # | Severity | Проблема |
|---|----------|----------|
| 1 | HIGH | FSD layer violation: shared → pages (5 файлов) |
| 2 | HIGH | Broken test utility: `test/testUtils.tsx` импортирует `appStore` вместо `store` |
| 3 | HIGH | JWT token в `.env` файле |
| 4 | MEDIUM | Нет cache invalidation в 8 из 9 API slices |
| 5 | MEDIUM | Невалидный Content-Type в baseQuery |
| 6 | MEDIUM | `serializableCheck: false` скрывает потенциальные баги |
| 7 | MEDIUM | Inconsistent naming: PascalCase + camelCase в директориях |
| 8 | LOW | Features layer недоиспользован (4 из ~20+ потенциальных) |
| 9 | LOW | Incomplete barrel exports (widgets, features, pages) |
| 10 | LOW | `classnames` в devDependencies вместо dependencies |

---

## 8. Связанность client/backend и backend/

### 8.1. Разделение ответственности

| Директория | Домен | Пользователи |
|-----------|-------|-------------|
| `client/backend/` | Клиентские сервисы (брокерские счета, каталог, клиенты, документы, уведомления, OTP, эмулятор биржи) | Клиенты (инвесторы) |
| `backend/` | Административные сервисы (аутентификация сотрудников, трейдинг, управление, HR, налоги, обучение) | Сотрудники, администрация |

### 8.2. Cross-directory взаимодействия

```
document-service [client] --Feign--> tax-service [backend]
trading-service [backend] --Kafka--> emulator-service [client]
trading-service [backend] --Kafka--> account-service [client]
```

### 8.3. Проблема разделения

**Почему сервисы разделены на две директории — неочевидно.** Обоснования не найдено в документации. Кросс-вызовы между директориями существуют. Рекомендация: объединить в единую структуру или создать документацию, объясняющую разделение.

---

## 9. Инфраструктура и DevOps

### 9.1. Scorecard

| Категория | Оценка |
|-----------|--------|
| Docker best practices | 5.2/10 (C) |
| Docker Compose | 3.0/10 (D) |
| CI/CD качество | 5.5/10 (C) |
| Kubernetes maturity | 2.2/10 (D-) |
| Environment management | 3.5/10 (D) |
| Infrastructure-as-Code | 0/10 (F) |
| **Общая** | **3.2/10 (D)** |

### 9.2. Docker

- Все 24 backend Dockerfiles: 3-stage build (Gradle 9.0.0-jdk17 → layered JAR → ubuntu/jre:21)
- Frontend: 2-stage (node:20-alpine → nginx:**1.21.0-alpine** — устаревший)
- **Нет `.dockerignore` файлов** (0 из 26 проектов)
- **Нет `USER` директива** — все контейнеры работают от root
- JDK 17 (build) vs JRE 21 (runtime) — нестыковка
- Layered JAR extraction — хорошо реализовано

### 9.3. Docker Compose

- 23 compose файла для локальной разработки
- **Портовые конфликты:** все сервисы используют одинаковые порты (5432, 9092, 6379)
- **Нет healthchecks** в compose
- Inconsistent versions: PostgreSQL 14/15/17, Kafka 7.0.0/7.9.0

### 9.4. CI/CD

- **Dual system:** GitLab CI + Jenkins одновременно
- Backend: Centralized shared libraries (DRY — хорошо)
- Frontend: Self-contained pipeline с Docker build + GitOps deployment
- **Security scanning:** Только jwt-starter имеет SAST
- 2 сервиса ссылаются на **personal branches** вместо main (`SKarabanov`, `RSafin`)
- 13 backup-файлов (`.bak`, `-test`) в репозиториях

### 9.5. Kubernetes/Helm

- Helm charts централизованы в отдельном репозитории (`helm-charts`)
- 50 values-файлов (25 dev + 25 release)
- **Нет resource limits/requests**
- **Нет health probes**
- **Нет HPA/autoscaling**
- Все сервисы привязаны к одному node (no HA)
- Typo: `values-realese.yaml` вместо `values-release.yaml`
- Большинство release-конфигов используют `SPRING_PROFILES_ACTIVE: dev` вместо `prod`

---

## 10. Тестирование

### 10.1. Backend Testing

**Test-to-Source Ratio:** ~1:6 (с учётом сервисов без тестов)

| Категория | Статус |
|-----------|--------|
| Unit тесты | Есть в ~8 из 29 сервисов |
| Integration тесты | Testcontainers в 7 сервисах |
| JaCoCo | Настроен в 7+ сервисах, **только userinfo-service** enforce 85% |
| SonarQube | 2 разных сервера: `sonarqube9.astondevs.ru:9000` и `172.17.1.26:9000` |

**13+ backend сервисов имеют 0 unit тестов:** education, trading, management, employee, financialtransactions, document-pb, tax, newsfeed, criticalfeedbackchannel, test-service, api-gateway и др.

### 10.2. Frontend Testing

- 38 test файлов (31 UI компонент + 6 widget + 2 hook + 3 utility + 1 feature)
- Jest + Testing Library + ts-jest
- **Нет coverage thresholds**
- **Сломанный test utility:** `test/testUtils.tsx` импортирует несуществующий путь
- Storybook 7.4.5 для визуальной документации

### 10.3. AQA

- 3 проекта в `client/aqa/`
- REST Assured 5.3.0 (API тесты) + Selenium WebDriver 4.43.0 (UI тесты)
- Allure reporting, WireMock mocking
- **КРИТИЧЕСКАЯ ПРОБЛЕМА:** Test data CSV содержат потенциально реальные credentials

---

## 11. Безопасность

### 11.1. Scorecard

| Категория | Оценка |
|-----------|--------|
| Аутентификация | 7/10 |
| Авторизация | 5/10 |
| Защита данных | 3/10 |
| Секреты в коде | **2/10** |
| Input validation | 8/10 |
| **Общая** | **4/10** |

### 11.2. Authentication

- **Клиентский домен:** Keycloak integration с token introspection через API Gateway
- **Админский домен:** Custom JWT (jjwt) с 15min access / 9hr refresh
- OTP: 6-digit, 3min TTL, max 3 attempts, rate limiting 10/min
- 8 OTP container variants на фронтенде

### 11.3. Authorization

- `@PreAuthorize` только в management-service-pb (25+ annotations)
- Остальные сервисы: или gateway-level auth, или `null` authorities
- trading-service JwtFilter: **null authorities** — нет RBAC внутри сервиса

### 11.4. OWASP Top 10

| Уязвимость | Риск | Статус |
|------------|------|--------|
| A01 Broken Access Control | MEDIUM | CSRF disabled (оправдано для stateless), swagger/actuator доступны без auth |
| A03 Injection | LOW | JPA/Hibernate параметризованные запросы |
| A04 Insecure Design | MODERATE | Нет DOMPurify в React, нет CSP headers |
| A07 Auth Failures | LOW | Хорошие механизмы: JWT + OTP + rate limiting |
| Hardcoded Secrets | **CRITICAL** | 7+ секретов в исходном коде |

### 11.5. Все hardcoded credentials

```
1. api-gateway: Keycloak admin + password + client_secret
2. api-gateway: Nexus credentials in build.gradle.kts
3. auth-service: JWT secret key fallback
4. document-service-pb: JWT secret
5. account-service-test: JWT secret
6. customercare-service: JWT secret (БЕЗ env fallback)
7. support-service: Nexus credentials in build.gradle
8. customer-service: Nexus credentials (in build.gradle)
9. otp-service: Nexus credentials (in build.gradle)
10. react-service/.env: VITE_API_TOKEN
11. AQA test data: потенциально реальные credentials в CSV файлах
```

---

## 12. Код-стайл и качество

### 12.1. Backend

| Аспект | Статус |
|--------|--------|
| Build DSL | Kotlin DSL (2) vs Groovy (15) vs Maven (1) — непоследовательно |
| Group IDs | `ru.aston`, `com.astondevs`, `org.example` — 3 конвенции |
| Boot JAR names | `application-service.jar` (generic) vs service-specific — непоследовольно |
| Checkstyle | Только userinfo-service (strict) и employee-service (lenient) |
| SonarQube | 7 сервисов, но 2 разных сервера |
| Dead code | newsfeed-service: закомментированы JPA, Security, Kafka, Liquibase |
| Copy-paste | `criticalfeedbackchannel` bootJar дважды, сначала `userinfo-service.jar` |

### 12.2. Frontend

| Аспект | Статус |
|--------|--------|
| ESLint | Настроен с `no-console: "error"`, max line 250 |
| TypeScript | `strict: true`, `noImplicitAny: true` — хорошо |
| Prettier | Настроен |
| Husky + Commitlint | Настроен |
| Naming | PascalCase + camelCase в директориях — непоследовольно |
| Barrel exports | Неполные (widgets 6/16, features 1/4, pages 10/22) |

---

## 13. Сильные стороны

1. **Хорошая декомпозиция микросервисов** — чёткое разделение по доменам (account, customer, catalog, trading, notification)
2. **Outbox Pattern** реализован в trading-service и emulator-service для надёжной доставки Kafka-сообщений
3. **Centralized API Gateway** с token introspection и circuit breakers
4. **Frontend lazy loading** — все страницы загружаются по требованию
5. **RTK Query с SSE** — notifications используют EventSource с exponential backoff
6. **Shared Nexus libraries** — переиспользуемые стартеры для logging, exception handling, OTP
7. **Input validation** — comprehensive на обоих уровнях (Yup frontend + Bean Validation backend)
8. **OTP security** — rate limiting, attempt lockout, TTL
9. **GitOps deployment** — frontend CI обновляет Helm values в git для ArgoCD/Flux
10. **Layered Docker images** — Spring Boot layered JAR extraction для оптимизации
11. **Token refresh с mutex** — предотвращает concurrent refresh requests
12. **Feign dependency graph** — направленный ациклический граф, нет циклических зависимостей

---

## 14. Рекомендации с приоритетами

### CRITICAL (Немедленно)

| # | Рекомендация | Трудоёмкость | Затронуто |
|---|-------------|-------------|-----------|
| R1 | Удалить все hardcoded secrets, использовать только env variables без fallback defaults | Средняя | 10+ файлов |
| R2 | Исправить outbox batch send в trading-service (`sendBatchMessages()` закомментирован) | Низкая | 1 файл |
| R3 | Добавить `.dockerignore` во все сервисы | Низкая | 26 проектов |
| R4 | Добавить `USER` директиву во все Dockerfiles | Низкая | 26 файлов |

### HIGH (В течение 2 недель)

| # | Рекомендация | Трудоёмкость | Затронуто |
|---|-------------|-------------|-----------|
| R5 | Добавить Kubernetes resource limits/requests и health probes | Средняя | 50 values файлов |
| R6 | Добавить rate limiting на API Gateway | Средняя | 1 сервис |
| R7 | Заменить `.block()` на reactive chain в JwtFilter/AuthJwtFilter | Высокая | 2 файла |
| R8 | Добавить DLT/retry для всех Kafka listeners (сейчас только 2 из 26+) | Высокая | 24+ listeners |
| R9 | Добавить idempotency guards в Kafka consumers | Высокая | 20+ listeners |
| R10 | Стандартизировать версии `interservice-interaction-dto-lib` на одну | Средняя | 7+ сервисов |
| R11 | Удалить мёртвые submodules (`account-service-pb`, `jwt-starter`, `keycloak-providers`) | Низкая | 3 директории |
| R12 | Удалить пустую `backend/backend/` директорию | Низкая | 1 директория |

### MEDIUM (В течение 1 месяца)

| # | Рекомендация | Трудоёмкость |
|---|-------------|-------------|
| R13 | Создать центральный Gradle BOM для управления версиями зависимостей | Средняя |
| R14 | Стандартизировать Group IDs на единую конвенцию | Средняя |
| R15 | Добавить security scanning (SAST + container scanning) в shared CI pipeline | Средняя |
| R16 | Исправить FSD violations: переместить `otpType` в `shared/types/` | Низкая |
| R17 | Исправить невалидный Content-Type в frontend `baseQuery.ts` | Низкая |
| R18 | Добавить cache invalidation tags во все RTK Query API slices | Средняя |
| R19 | Стандартизировать Liquibase naming convention (все на `YYYY-MM-DD-action-target`) | Низкая |
| R20 | Добавить tests для сервисов с 0% покрытием (trading, management, education и др.) | Высокая |
| R21 | Консолидировать dual CI/CD (GitLab CI или Jenkins, не оба) | Средняя |
| R22 | Исправить personal branch references в CI (`SKarabanov`, `RSafin` → `main`) | Низкая |
| R23 | Добавить circuit breakers на все Feign clients | Средняя |
| R24 | Исправить auth-service exception hierarchy — создать общий `DomainException` base class | Средняя |

### LOW (В течение 3 месяцев)

| # | Рекомендация | Трудоёмкость |
|---|-------------|-------------|
| R25 | Унифицировать build DSL (все на Groovy или все на Kotlin DSL) | Высокая |
| R26 | Вынести `exceptionhandlerstarter` из исходников сервисов в Nexus dependency | Средняя |
| R27 | Добавить missing `entities/` layer во frontend FSD | Высокая |
| R28 | Добавить Ingress/LB для Kubernetes вместо NodePort | Средняя |
| R29 | Добавить Infrastructure-as-Code (Terraform/Ansible) | Высокая |
| R30 | Обновить nginx с 1.21.0 до актуальной версии в frontend Dockerfile | Низкая |
| R31 | Исправить frontend test utility (broken import path) | Низкая |
| R32 | Добавить coverage thresholds для Jest | Низкая |
| R33 | Документировать разделение `backend/` vs `client/backend/` | Низкая |

---

## 15. Архитектурная диаграмма

```
                              ┌─────────────────────────┐
                              │     React Frontend       │
                              │  (Vite + Redux Toolkit)  │
                              └────────────┬────────────┘
                                           │ HTTPS
                              ┌────────────▼────────────┐
                              │      API Gateway         │
                              │  (Spring Cloud Gateway)  │
                              │  JwtFilter / AuthFilter  │
                              │  Circuit Breaker         │
                              │  Prometheus + Zipkin     │
                              └────────────┬────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
         ┌──────────▼─────────┐ ┌──────────▼─────────┐ ┌──────────▼─────────┐
         │   CLIENT BACKEND   │ │   ADMIN BACKEND    │ │    KEYCLOAK        │
         │   (client/backend/) │ │   (backend/)       │ │                    │
         └──────────┬─────────┘ └──────────┬─────────┘ └────────────────────┘
                    │                      │
     ┌──────────────┼──────────────┐       │
     │              │              │       │
┌────▼────┐  ┌─────▼─────┐  ┌────▼───┐   │   ┌──────────────────────────────┐
│account  │  │customer   │  │catalog │   │   │ auth-service (JWT)           │
│service  │  │service    │  │service │   │   │ trading-service (Kafka+Redis)│
│(Redis)  │  │(Keycloak) │  │(Redis) │   │   │ education-service            │
└────┬────┘  └─────┬─────┘  └────┬───┘   │   │ employee-service (Eureka)    │
     │             │             │        │   │ userinfo-service (WS+Kafka)  │
     │        ┌────▼────┐        │        │   │ management-service-pb (Feign)│
     │        │otp-svc  │        │        │   │ document-service-pb (MinIO)  │
     │        │(Redis)  │        │        │   │ tax-service (Kafka)          │
     │        └─────────┘        │        │   │ support-service              │
     │                           │        │   │ customercare-service (Feign) │
     │  ┌────────────────────────▼──┐     │   │ newsfeed-service             │
     │  │    emulator-service       │     │   │ financialtransactions-svc    │
     │  │    (Kotlin, Quartz,       │─────│───│ criticalfeedbackchannel      │
     │  │     MOEX Feign, Kafka)    │     │   │ account-service-test         │
     │  └───────────────────────────┘     │   │ test-service                 │
     │                                    │   └──────────────────────────────┘
     │  ┌────────────────────────────┐    │
     ├──│  notification-service      │◄───┤ (Kafka from all)
     │  │  (Kafka hub, SSE, Email)   │    │
     │  └────────────────────────────┘    │
     │                                    │
     │  ┌────────────────────────────┐    │
     └──│  document-service          │──► tax-service
        │  (MinIO, PDF, Thymeleaf)   │
        └────────────────────────────┘

KAFKA TOPICS:
═══════════
order_request:        trading → emulator
order_result/errors:  emulator → trading
actual_*:             emulator → catalog
otp_notification:     otp → notification
user_auth/registration: customer → notification
favourite_price:      catalog → notification
account_changes:      account → notification
register-account:     auth → employee
register-result:      employee → userinfo
```

---

*Аудит завершён. Всего проанализировано: 28 сервисов, 26 Dockerfiles, 23 docker-compose, 29 GitLab CI, 39 Jenkinsfiles, 50 Helm values, 38 frontend тестов, ~100+ backend тестов.*
