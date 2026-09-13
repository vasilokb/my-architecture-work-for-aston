# Liberty Investment — Обзор архитектуры

**Дата:** 2026-05-24  
**Версия документа:** 1.0

---

## Содержание

1. [Назначение системы](#1-назначение)
2. [Пользователи](#2-пользователи)
3. [Архитектура верхнего уровня](#3-архитектура)
4. [Технологический стек](#4-стек)
5. [Инвентаризация сервисов](#5-сервисы)
6. [Межсервисное взаимодействие](#6-взаимодействие)
7. [API Gateway](#7-gateway)
8. [Аутентификация и авторизация](#8-аутентификация)
9. [Данные и хранилища](#9-данные)
10. [Shared-библиотеки](#10-библиотеки)
11. [Ключевые бизнес-процессы](#11-процессы)
12. [Инфраструктура](#12-инфраструктура)

---

## 1. Назначение системы <a name="1-назначение"></a>

**Liberty Investment** — инвестиционная платформа, предоставляющая розничным инвесторам доступ к торговле ценными бумагами на Московской бирже (MOEX). Платформа также обеспечивает полный back-office для сотрудников брокера: управление клиентами, документооборот, бухгалтерию, налоги, CRM и поддержку.

### Основные возможности

| Возможность | Описание |
|---|---|
| Торговля ценными бумагами | Лимитные, рыночные и стоп-ордера через эмулятор биржи |
| Управление брокерскими счетами | Открытие/закрытие счетов, пополнение, вывод средств |
| Каталог инструментов | Акции, облигации, фонды с актуальными котировками |
| Документооборот | Генерация PDF-документов, 2-НДФЛ, договоров |
| Бухгалтерия и налоги | Расчёт НДФЛ, история транзакций |
| Обучение инвесторов | Курсы, уроки, квалификационные тесты |
| Поддержка клиентов | Тикеты, чат, обратная связь |
| Уведомления | Push, SSE, email о событиях на счёте |
| CRM для сотрудников | Управление клиентами, задачи, рабочие места |

---

## 2. Пользователи <a name="2-пользователи"></a>

| Роль | Описание | Аутентификация | Основной интерфейс |
|---|---|---|---|
| **Инвестор** | Физическое лицо, клиент брокера | Keycloak (OAuth 2.0) | React SPA (`react-service`) |
| **Сотрудник** | Сотрудник брокера (оператор, аналитик, администратор) | Custom JWT (`auth-service`) | Внутренний портал (через `management-service-pb`) |
| **MOEX** | Внешняя Московская биржа | API-ключ | Внешняя система |

---

## 3. Архитектура верхнего уровня <a name="3-архитектура"></a>

### 3.1. Структура репозиториев

Проект разделён на **два независимых Git-репозитория**:

```
investment/
├── client/
│   ├── backend/          ← Клиентские сервисы (7 сервисов)
│   │   ├── account-service/
│   │   ├── catalog-service/
│   │   ├── customer-service/
│   │   ├── document-service/
│   │   ├── emulator-service/
│   │   ├── notification-service/
│   │   └── otp-service/
│   └── react/
│       └── react-service/  ← Frontend SPA
│
└── backend/              ← Back-office сервисы (16 сервисов)
    ├── api-gateway/
    ├── auth-service/
    ├── trading-service/
    ├── management-service-pb/
    ├── userinfo-service/
    ├── employee-service/
    ├── account-service-test/
    ├── document-service-pb/
    ├── education-service/
    ├── test-service/
    ├── tax-service/
    ├── financialtransactions-service/
    ├── customercare-service/
    ├── support-service/
    ├── newsfeed-service/
    └── criticalfeedbackchannel/
```

Разделение проведено **по роли пользователя** (клиент / сотрудник), а не по бизнес-доменам. Это означает, что все 12 DDD-доменов пересекают границу `client/backend/` ↔ `backend/`. Рекомендация — сохранить раздельные репозитории, но ввести правила изоляции (общие контракты через OpenAPI, а не через shared DTO lib). Объединение в монорепозиторий не решит архитектурные проблемы и не рекомендуется.

### 3.2. Визуальная схема

```
┌──────────────┐       ┌──────────────┐
│  React SPA   │       │  Back-office │
│  (инвестор)  │       │   портал     │
└──────┬───────┘       └──────┬───────┘
       │                      │
       │  VITE_API_URL        │  /api/v1/...
       │  :31531              │
       ▼                      ▼
┌──────────────────────────────────────┐
│          API Gateway (:31531)        │
│  JwtFilter (Keycloak) — 17 routes   │ ← Клиенты
│  AuthJwtFilter (JWT) — 2 routes     │ ← Сотрудники
└──┬───┬───┬───┬───┬───┬───┬───┬──────┘
   │   │   │   │   │   │   │   │
   ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
┌──────────────────────────────────────────────┐
│              Микросервисы (20 шт.)           │
│                                              │
│  client/backend/ (7):     backend/ (13):     │
│  ┌─────────────────┐    ┌─────────────────┐  │
│  │ account-service │    │ trading-service │  │
│  │ catalog-service │    │ auth-service    │  │
│  │ customer-service│    │ management-s-pb │  │
│  │ document-service│    │ userinfo-service│  │
│  │ emulator-service│    │ employee-service│  │
│  │ notification-svc│    │ account-svc-test│  │
│  │ otp-service     │    │ document-svc-pb │  │
│  └─────────────────┘    │ education-svc   │  │
│                         │ test-service    │  │
│                         │ tax-service     │  │
│                         │ fintrans-service│  │
│                         │ customcare-svc  │  │
│                         │ support-service │  │
│                         │ newsfeed-service│  │
│                         │ criticalfeed-ch │  │
│                         └─────────────────┘  │
└──────────────────────────────────────────────┘
         │                │           │
         ▼                ▼           ▼
   ┌──────────┐    ┌──────────┐  ┌────────┐
   │PostgreSQL│    │  Kafka   │  │  MOEX  │
   │  (2 host)│    │ (Zookepr)│  │  API   │
   └──────────┘    └──────────┘  └────────┘
```

**API Gateway — единая точка входа для ВСЕХ запросов**, хотя физически расположен в `backend/`. 85% маршрутов обслуживают клиентские запросы (Keycloak), 10% — административные (JWT).

---

## 4. Технологический стек <a name="4-стек"></a>

### 4.1. Backend

| Компонент | Технология | Версия |
|---|---|---|
| Язык | Java | 17 |
| Язык (1 сервис) | Kotlin | 2.2.21 |
| Фреймворк | Spring Boot | 3.5.0 (3.5.5, 3.5.6 — 2 сервиса) |
| Spring Cloud | | 2025.0.0 |
| Build | Gradle (Groovy + Kotlin DSL) | 8.10 — 9.0.0 |
| API Gateway | Spring Cloud Gateway (WebFlux) | 3.5.0 |
| Inter-service REST | Spring Cloud OpenFeign | 5.0.1 |
| Messaging | Spring Kafka | 3.2.4 — 3.3.0 |
| ORM | Spring Data JPA (Hibernate) | |
| Миграции БД | Liquibase | 4.27 — 5.0.1 (имена скриптов не согласованы: дата vs числовой ID) |
| Кэш | Redis + Caffeine / EhCache | |
| Resilience | Resilience4j | 2.1.0 — 2.3.0 |
| DTO маппинг | MapStruct | 1.5.5 — 1.6.3 |
| PDF генерация | Thymeleaf + html2pdf (iText) | |
| Object Storage | MinIO | 8.6.0 |
| Auth (клиенты) | Keycloak | 26.0.7 |
| Auth (сотрудники) | Custom JWT (jjwt) | 0.11.5 — 0.13.0 |
| API docs | springdoc-openapi (Swagger) | 2.5.0 — 2.8.14 |
| Tracing | Zipkin + Micrometer | |

### 4.2. Frontend

| Компонент | Технология | Версия |
|---|---|---|
| Фреймворк | React | 18.2.0 |
| Язык | TypeScript | 5.0.2 |
| Build | Vite | 4.4.9 |
| State | Redux Toolkit | 1.9.5 |
| Routing | react-router-dom | 6.16.0 |
| Forms | react-hook-form + yup | 7.46.1 |
| Charts | Recharts | 3.1.0 |
| Testing | Jest + Testing Library | 29.7.0 |

### 4.3. Инфраструктура

| Компонент | Технология | Версия |
|---|---|---|
| Контейнеры | Docker | |
| Оркестрация | Kubernetes (Helm) | |
| БД | PostgreSQL | 14 |
| Брокер сообщений | Apache Kafka (Confluent) | 7.9.0 |
| Кэш | Redis | 7.2 |
| Object Storage | MinIO | RELEASE.2025-04-08 |
| Identity Provider | Keycloak | |
| Tracing | Zipkin | 3.5.1 |
| CI/CD | GitLab CI + Jenkins | |

---

## 5. Инвентаризация сервисов <a name="5-сервисы"></a>

### 5.1. Клиентские сервисы (`client/backend/`)

| # | Сервис | Назначение | БД | Kafka | Feign |
|---|---|---|---|---|---|
| 1 | **account-service** | Брокерские счета, депо, операции | PostgreSQL + Redis | ✅ | ✅ (2) |
| 2 | **catalog-service** | Каталог инструментов, портфели, котировки | PostgreSQL + Redis | ✅ | ✅ (1) |
| 3 | **customer-service** | Профиль клиента, регистрация, 2FA | PostgreSQL + Redis | ✅ | — |
| 4 | **document-service** | Генерация PDF-документов для клиентов | PostgreSQL + MinIO | — | ✅ (3) |
| 5 | **emulator-service** | Эмуляция биржи MOEX (ордера, сделки) | PostgreSQL | ✅ | ✅ (1→MOEX) |
| 6 | **notification-service** | Push, SSE, email-уведомления | PostgreSQL + Redis | ✅ | ✅ (1) |
| 7 | **otp-service** | Генерация и валидация OTP-кодов | Redis | ✅ | ✅ (1) |

### 5.2. Back-office сервисы (`backend/`)

| # | Сервис | Назначение | БД | Kafka | Feign | Статус |
|---|---|---|---|---|---|---|
| 8 | **api-gateway** | Единая точка входа, аутентификация | — | — | — | Активен |
| 9 | **auth-service** | Аутентификация сотрудников (JWT) | PostgreSQL | ✅ | — | Активен |
| 10 | **trading-service** | Создание ордеров, торговый конвейер | PostgreSQL + Redis | ✅ | ✅ (2) | ⚠️ Outbox отключён |
| 11 | **management-service-pb** | Back-office портал, агрегация данных | PostgreSQL | ✅ | ✅ (2) | Активен |
| 12 | **userinfo-service** | BFF для сотрудников + CRM-логика (см. 5.3) | PostgreSQL | ✅ | ✅ (4) | ⚠️ God-сервис |
| 13 | **employee-service** | Управление сотрудниками, задачами | PostgreSQL | ✅ | — | Активен |
| 14 | **account-service-test** | Клон account-service для прод-окружения | PostgreSQL | ✅ | ✅ (2) | ⚠️ Shared DB с account-service |
| 15 | **document-service-pb** | Генерация PDF для back-office | PostgreSQL + MinIO | — | ✅ | Активен |
| 16 | **education-service** | Курсы, темы, уроки | PostgreSQL | — | ✅ | Активен |
| 17 | **test-service** | Квалификационные тесты | PostgreSQL | — | — | Активен |
| 18 | **tax-service** | Расчёт НДФЛ, 2-НДФЛ | PostgreSQL | ✅ | ✅ (1) | Активен |
| 19 | **financialtransactions-service** | История транзакций | PostgreSQL | ✅ | ✅ (1) | Активен |
| 20 | **customercare-service** | Подключение платных услуг | PostgreSQL | ✅ | ✅ (3) | Активен |
| 21 | **support-service** | Тикеты поддержки, шаблоны ответов | PostgreSQL | — | — | ⚠️ Полумёртвый — создание заявок закомментировано |
| 22 | **newsfeed-service** | Новостная лента | — | — | ✅ | 🔴 Мёртвый — пустая заглушка (Hello World) |
| 23 | **criticalfeedbackchannel** | Обратная связь | PostgreSQL + Redis | ✅ | — | ⚠️ Публичный эндпоинт без авторизации |

### 5.3. Архитектурные проблемы сервисов

#### userinfo-service — BFF, «выросший» доменную логику

`userinfo-service` задумывался как Backend for Frontend (BFF) — агрегирующий слой для back-office портала. Однако в процессе развития он накопил **собственную доменную логику**, которой не место в BFF:

| Что содержит | Почему это проблема |
|---|---|
| Локальная БД с сущностями `Relationship`, `Verification`, `Event`, `Audit` | BFF не должен иметь собственной доменной модели |
| KYC-процедуры (верификация клиентов) | Доменная логика,不属于 BFF |
| Блокировка/разблокировка клиентов | Доменная логика |
| Аудит действий сотрудников | Доменная логика |
| 4 Feign-клиента + 2 Kafka listener | Сильная связанность |
| Dual-profile транспорт (REST + Kafka для одних и тех же данных) | Анти-паттерн: один и тот же запрос можно отправить через REST ИЛИ через Kafka → 12 классов вместо 6 (по 2 producer/consumer/handler/dto на каждый профиль), busy-wait polling в Kafka-варианте |

**Итог:** userinfo-service — частично легитимный BFF (агрегация данных для UI), частично god-сервис с чужой доменной логикой (KYC, аудит, верификация).

#### account-service-test — не «тестовый»

Название `account-service-test` обманчиво: сервис **используется в прод-окружении** как параллельный экземпляр account-service, подключённый к **той же базе данных** (`account_service_db`). Это нарушает database-per-service и создаёт риск конкурентных записей.

#### criticalfeedbackchannel — уязвимость

Маршрут `/api/v1/criticalfeedbackchannel-service/**` проходит через `JwtFilter` (Keycloak), но сам сервис имеет публичные эндпоинты, доступные без аутентификации. Это создаёт вектор DoS-атаки.

### 5.3. Неактивные / placeholder-модули

| Модуль | Статус |
|---|---|
| `account-service-pb` | Пустой репозиторий |
| `jwt-starter` | Пустой репозиторий |
| `keycloak-providers` | Пустой репозиторий |
| `logging-spring-boot-starter` | Shared-библиотека (Maven) |

---

## 6. Межсервисное взаимодействие <a name="6-взаимодействие"></a>

### 6.1. REST (Feign)

Система содержит **20 Feign-клиентов** для синхронных REST-вызовов между сервисами.

#### Полная матрица вызовов

```
                   →  acct  cust  docu  tax  fina  cata  emul  MOEX
account-service    ·   —     ✅    ✅    —    —     —     —     —
catalog-service    ·   ✅    —     —     —    —     —     —     —
document-service   ·   ✅    ✅    —     ✅   —     —     —     —
emulator-service   ·   —     —     —     —    —     —     ✅    ✅
notification-svc   ·   —     ✅    —     —    —     —     —     —
otp-service        ·   —     ✅    —     —    —     —     —     —
account-svc-test   ·   —     ✅    ✅    —    —     —     —     —
customercare-svc   ·   ✅    ✅    ✅    —    —     —     —     —
fintrans-svc       ·   ✅    —     —     —    —     —     —     —
management-svc-pb  ·   —     —     —     —    ✅    ✅    —     —
tax-service        ·   ✅    —     —     —    —     —     —     —
trading-service    ·   ✅    —     —     —    —     ✅    —     —
```

#### Хаб-сервисы (наиболее востребованные)

| Сервис | Кол-во вызывающих | Критичность |
|---|---|---|
| **account-service** | 6 | SPOF — падение отключает половину системы |
| **customer-service** | 6 | SPOF — блокирует все операции с клиентами |
| **document-service** | 3 | Блокирует генерацию документов |

#### Кольцевые зависимости

```
ЦИКЛ 1:  account-service ←→ document-service  (прямая, двунаправленная)
ЦИКЛ 2:  account-service → document-service → tax-service → account-service  (3-узловой)
```

**Риск каскадных отказов:**
- **Цикл 1** — `account-service` вызывает `document-service` для генерации документов при открытии/закрытии счёта, а `document-service` вызывает `account-service` для проверки доступа. При насыщении thread pools — distributed deadlock.
- **Цикл 2** — любая ошибка в `tax-service` откатывается на `account-service`, который одновременно вызывает `document-service` → зацикливание при восстановлении.
- **Оба цикла** не имеют circuit breaker на участвующих Feign-клиентах → каскадный сбой не изолируется.

#### Самые длинные синхронные цепочки (4 хопа)

```
trading-service → catalog-service → account-service → document-service → tax-service
management-service-pb → financialtransactions-service → account-service → document-service → customer-service
```

### 6.2. Kafka

#### Топики и потребители

| Топик | Продюсер | Консьюмеры |
|---|---|---|
| `order_request` | trading-service | emulator-service |
| `order_cancel` | trading-service | emulator-service |
| `order_status` | emulator-service | trading-service |
| `order.status.change` | trading-service *(отключён)* | account-service |
| `order_executed` | *(ожидается trading)* | account-service |
| `order_rejected` | *(ожидается trading)* | account-service |
| `order_cancelled` | *(ожидается trading)* | account-service |
| `order_expired` | *(ожидается trading)* | account-service |
| `account-event` | account-service | customer-service |
| `notification-events` | various | notification-service, userinfo-service |
| `support-ticket-notification` | support-service | notification-service |
| `ticket.status.changed` | support-service | notification-service, support-service |
| `feedback.status.changed` | various | notification-service, userinfo-service |
| `order.status.changed` | various | notification-service |

**Итого:** 25 `@KafkaListener`-методов в 8 сервисах.

#### Надёжность Kafka-коммуникации

| Защита | Кол-во listeners | Сервисы |
|---|---|---|
| @RetryableTopic + DLT + exponential backoff | **1** | notification-service (эталон) |
| DLT без retry (`attempts=1`) | **3** | emulator-service |
| **Без retry/DLT** | **21** | trading, account, account-test, customer, support, userinfo |

**23 из 25 listeners** не имеют retry или DLT. При исключении в обработчике сообщение теряется (auto-commit) или consumer зависает (manual commit). В сочетании с отключённым Outbox в trading-service это означает, что критические бизнес-события могут быть потеряны безвозвратно.

---

## 7. API Gateway <a name="7-gateway"></a>

### 7.1. Маршрутизация

API Gateway (`backend/api-gateway`) — **единая точка входа для всех запросов** от клиентов и сотрудников. Несмотря на расположение в `backend/`, обслуживает преимущественно клиентские запросы.

**Подключение фронтенда:**
- React SPA: `VITE_API_URL = http://172.17.1.26:31531` (NodePort API Gateway)
- nginx (production): проксирует `/api/v1/customer-service/` → API Gateway
- Vite dev proxy: проксирует `/api/v1/customer-service/refresh-token` → API Gateway

Все маршруты используют префикс `/api/v1/{service-name}/**` и имеют Circuit Breaker (Resilience4j).

| Маршрут | Целевой сервис | Auth-фильтр |
|---|---|---|
| `/api/v1/account-service/**` | account-service | JwtFilter (Keycloak) |
| `/api/v1/auth-service/**` | auth-service | AuthJwtFilter (JWT) |
| `/api/v1/catalog-service/**` | catalog-service | JwtFilter |
| `/api/v1/customer-service/**` | customer-service | JwtFilter |
| `/api/v1/customercare-service/**` | customercare-service | JwtFilter |
| `/api/v1/criticalfeedbackchannel-service/**` | criticalfeedbackchannel | JwtFilter |
| `/api/v1/document-service/**` | document-service | JwtFilter |
| `/api/v1/education/**` | education-service | JwtFilter |
| `/emulator/**` | emulator-service | JwtFilter |
| `/api/v1/employee-service/**` | employee-service | AuthJwtFilter (JWT) |
| `/api/v1/financialtransaction-service/**` | financialtransactions-service | JwtFilter |
| `/api/v1/newsfeed-service/**` | newsfeed-service | JwtFilter |
| `/api/v1/notification-service/**` | notification-service | JwtFilter |
| `/api/v1/otp-service/**` | otp-service | JwtFilter |
| `/api/v1/support-service/**` | support-service | JwtFilter |
| `/api/v1/tax-service/**` | tax-service | JwtFilter |
| `/api/v1/test-service/**` | test-service | JwtFilter |
| `/api/v1/trading-service/**` | trading-service | JwtFilter |
| `/api/v1/userinfo-service/**` | userinfo-service | JwtFilter |
| `/auth/**` | Keycloak | Нет |

Дополнительно 19 маршрутов для Swagger-документации (без аутентификации).

### 7.2. Фильтры

Gateway выполняет **минимальную трансформацию** — это чистый reverse proxy с аутентификацией:

- **Header injection:** `customer_id`, `x-role`, `x-permissions`
- **Circuit Breaker:** Resilience4J на каждом маршруте, fallback → HTTP 503
- **CORS:** Настроен для конкретных origins
- **Tracing:** Zipkin (100% sampling)

---

## 8. Аутентификация и авторизация <a name="8-аутентификация"></a>

### 8.1. Два потока аутентификации

| Аспект | Клиенты (JwtFilter) | Сотрудники (AuthJwtFilter) |
|---|---|---|
| Token | Keycloak OAuth 2.0 | Custom JWT (auth-service) |
| Валидация | Keycloak Token Introspection | auth-service `/token/context` |
| Identity | `sub` (customer UUID) | `employeeId`, `role`, `permissions` |
| Заголовки downstream | `customer_id` | `customer_id` + `x-role` + `x-permissions` |
| Сервисов на потоке | 17 | 2 (auth-service, employee-service) |

### 8.2. Публичные эндпоинты (без аутентификации)

| Сервис | Пути |
|---|---|
| customer-service | `/registration`, `/auth`, `/otp`, `/otp/verify`, `/checklogin`, `/refresh-token`, `/forgot-password`, `/referral` |
| auth-service | `/authentication/initiate`, `/authentication/confirm`, `/password-reset/*`, `/otp/refresh/*` |
| catalog-service | `/assets`, `/assets/*`, `/issuer/*` |

---

## 9. Данные и хранилища <a name="9-данные"></a>

### 9.1. PostgreSQL

Каждый сервис имеет собственную базу данных (database-per-service). Все базы расположены на **двух PostgreSQL-инстансах**:

**Dev (172.17.1.26:31421):**

| БД | Сервис |
|---|---|
| `account_service_db` | account-service, account-service-test |
| `customer_service_db` | customer-service |
| `catalog_service_db` | catalog-service |
| `emulator_service_db` | emulator-service |
| `notification_service_db` | notification-service |

**Prod (postgres.dev:5432):**

| БД | Сервис |
|---|---|
| `release_management_service_pb_db` | management-service-pb |
| `release_userinfo_service_db` | userinfo-service |
| `release_financialtransactions_service_db` | financialtransactions-service |

**Изолированные (localhost):**

| БД | Сервис |
|---|---|
| `trading_service_db` | trading-service |
| `education_service_db` | education-service |
| `test_service_db` | test-service |
| `document_db` | document-service-pb |
| `employee_db` | employee-service |
| `auth_db` | auth-service |
| `support_service_db` | support-service |
| `tax_service_db` | tax-service |
| `customer_care_db` | customercare-service |
| `document_service_db` | document-service |
| `critical_feedback_channel` | criticalfeedbackchannel |

### 9.2. Redis

| Сервис | Redis DB | Назначение |
|---|---|---|
| account-service | DB 7 | Кэш |
| customer-service | DB 6 | Кэш |
| catalog-service | DB 0 | Кэш (Caffeine + Redis) |
| notification-service | DB 5 | Кэш |
| trading-service | DB 9 | Кэш (Jedis) |
| otp-service | DB 6 | Хранилище OTP-кодов |
| criticalfeedbackchannel | — | — |

### 9.3. MinIO (Object Storage)

| Сервис | Назначение |
|---|---|
| document-service | Хранение PDF-документов |
| document-service-pb | Хранение PDF-документов |
| customer-service | Хранение файлов |
| catalog-service | Хранение файлов |
| trading-service | Хранение файлов |
| notification-service | Хранение вложений |

---

## 10. Shared-библиотеки <a name="10-библиотеки"></a>

Библиотеки публикуются в **приватный Nexus** (`nexus.astondevs.ru`).

### 10.1. `interservice-interaction-dto-lib`

**Назначение:** Общие DTO для межсервисного взаимодействия (Feign + Kafka).  
**Потребители:** 8 сервисов.  
**Версии:** 0.0.3, 0.0.3a, 0.0.3f — **фрагментация**, совместимость не гарантирована.  
**Содержимое:** DTO для account-service, customer-service, document-service, notification-service, catalog-service + общие enums.

**Проблема:** Все DTO всех сервисов собраны в один артефакт. Изменение контракта одного сервиса требует обновления Nexus-зависимости у всех 8 потребителей → скрытая связанность на уровне компиляции. Kafka-сообщения между сервисами с разными версиями библиотеки могут быть несовместимы.

### 10.2. `liberty-investment-globalexceptionhandler-starter`

**Назначение:** Глобальный `@ControllerAdvice` для форматирования ошибок REST API.  
**Потребители:** 9 сервисов.  
**Версии:** 0.0.5, 0.0.5b, 0.0.5c, 0.0.5db (фрагментация).

### 10.3. `liberty-bank-logger-starter`

**Назначение:** AOP-логирование REST-контроллеров, профилирование через `@Profiling`.  
**Потребители:** 7 сервисов.  
**Исходники:** `backend/logging-spring-boot-starter/` (Maven).

### 10.4. `liberty-investment-otphandler-starter`

**Назначение:** Генерация и валидация OTP-кодов.  
**Потребители:** account-service, customer-service.

### 10.5. Неиспользуемые

| Библиотека | Статус |
|---|---|
| `jwt-starter` | Пустой репозиторий, не используется |
| `keycloak-providers` | Пустой репозиторий, не используется |

---

## 11. Ключевые бизнес-процессы <a name="11-процессы"></a>

### 11.1. Торговый конвейер

Наиболее критичный процесс — полный цикл торговли задействует **6+ сервисов** из обоих репозиториев:

```
1. Инвестор создаёт ордер
   react-service → api-gateway → trading-service (REST)

2. Ордер отправляется в эмулятор
   trading-service → [Kafka: order_request] → emulator-service

3. Эмулятор запрашивает котировку у MOEX
   emulator-service → (Feign + Resilience4j) → MOEX API

4. Эмулятор возвращает статус
   emulator-service → [Kafka: order_status] → trading-service

5. Trading публикует изменение статуса (ОТКЛЮЧЕНО — Outbox закомментирован)
   trading-service → [Kafka: order.status.change] → account-service
   trading-service → [Kafka: order_executed] → account-service

6. Account обновляет баланс и депо
   account-service → [Kafka: account-event] → customer-service

7. Уведомление инвестора
   notification-service → [Kafka] → Push/SSE/Email
```

### 11.2. Открытие брокерского счёта

```
1. Инвестор инициирует открытие
   react-service → api-gateway → account-service (REST)

2. Проверка клиента и OTP
   account-service → (Feign) → customer-service
   account-service → OTP validation

3. Генерация документов
   account-service → (Feign) → document-service → (Thymeleaf + html2pdf)

4. Сохранение в MinIO
   document-service → MinIO (PUT)

5. Уведомление
   notification-service → Push/SSE/Email
```

### 11.3. Онбординг клиента

```
1. Регистрация
   react-service → api-gateway → customer-service (REST, без аутентификации)

2. OTP-верификация
   react-service → customer-service → otp-service (Redis)

3. Создание профиля в Keycloak
   customer-service → Keycloak Admin API

4. Генерация 2-НДФЛ (по запросу)
   react-service → document-service → (Feign) → tax-service → account-service
```

### 11.4. Back-office: управление клиентами

```
1. Сотрудник открывает профиль клиента
   management-service-pb → (Feign) → financialtransactions-service → account-service
   management-service-pb → (Feign) → catalog-service → account-service

2. Просмотр транзакций
   management-service-pb → financialtransactions-service → account-service

3. Генерация документов
   management-service-pb → catalog-service → account-service → document-service

4. Управление тарифами
   customercare-service → (Feign) → account-service, customer-service, document-service
```

---

## 12. Инфраструктура <a name="12-инфраструктура"></a>

### 12.1. Kubernetes

Все 22 сервиса развёрнуты в Kubernetes через Helm charts:
- Service type: **NodePort** (все сервисы)
- Replicas: **1** (все сервисы, нет HPA)
- Ingress: **1** (только api-gateway)
- Health probes: **нет**
- Resource limits: **нет**

### 12.2. Docker

26 Dockerfile-ов, базовый образ — `eclipse-temurin:17-jdk` или `openjdk:17-slim`.
- Multi-stage builds: **нет**
- Non-root user: **нет**
- HEALTHCHECK: **нет**

### 12.3. CI/CD

Дублирование: 29 `.gitlab-ci.yml` + 24 `Jenkinsfile` = **53 pipeline-файла** для 23 сервисов.
- Shared library: `jenkins-shared-library`
- Security scanning: **нет**

### 12.4. Тестирование

| Метрика | Значение |
|---|---|
| Сервисов с 0 unit-тестов | **13+** |
| Порог покрытия тестами в CI | **Нет** |
| Интеграционные тесты | Единичные, не в CI |
| Test containers | Не используются |

**13 из 23 сервисов** не имеют unit-тестов. Детальный разбор — см. `AUDIT-REPORT.md` раздел 10.

### 12.4. Известные критические дефекты

| # | Проблема | Где | Влияние |
|---|---|---|---|
| 1 | **Outbox отключён** | `trading-service`: `sendBatchMessages()` закомментирован | События изменения статуса ордеров (executed, rejected, expired, cancelled) **никогда не публикуются** в Kafka → account-service не узнаёт об исполнении ордеров |
| 2 | **Hardcoded credentials** | Захардкоженные секреты в `api-gateway/application.yaml`, `auth-service`, `customercare-service`, 6+ `build.gradle` (Nexus), `react-service/.env` — полный список в `AUDIT-REPORT.md` раздел 1.1 | Детальный разбор — см. `AUDIT-REPORT.md` раздел 1.1 |
| 3 | **Shared database** | `account-service` + `account-service-test` → одна БД `account_service_db` | Нарушение database-per-service, конкурентные записи |
| 4 | **Misconfiguration** | `criticalfeedbackchannel`: `application.yaml` — copy-paste от financialtransactions-service | Сервис подключается к чужой БД `release_financialtransactions_service_db` вместо своей |
| 5 | **`.block()` в WebFlux** | API Gateway: `JwtFilter`, `AuthJwtFilter` | Блокировка Netty event loop thread → каскадные задержки под нагрузкой |
| 6 | **Нет rate limiting** | API Gateway | Любой клиент может отправлять неограниченное количество запросов |
