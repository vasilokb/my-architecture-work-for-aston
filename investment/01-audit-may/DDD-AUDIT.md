# DDD-аудит архитектуры Liberty Investment

**Дата:** 2026-05-24

---

## Содержание

1. [Введение: структура проектов](#1-введение)
2. [Идентифицированные DDD-домены](#2-домены)
3. [Кросс-репозиторные процессы](#3-кросс-репозиторные-процессы)
4. [Кросс-доменные сервисы (нарушение SRP)](#4-кросс-доменные-сервисы)
5. [Дублирование сервисов](#5-дублирование)
6. [Мёртвые и полумёртвые сервисы](#6-мёртвые-сервисы)
7. [Анализ по DDD-принципам](#7-анализ-по-principles)
8. [Рекомендации](#8-рекомендации)

---

## 1. Введение

### 1.1. Структура проектов

Проект Liberty Investment разделён на **два независимых Git-репозитория**, расположенных в параллельных директориях:

| Репозиторий | Назначение | Сервисов | Group ID | Пользователи |
|---|---|---|---|---|
| `client/backend/` | Клиентские сервисы (инвесторы) | 7 | `com.astondevs`, `ru.aston` | Клиенты через Keycloak |
| `backend/` | Back-office сервисы (сотрудники) | 16 | `ru.aston`, `com.astondevs`, `org.example` | Сотрудники через custom JWT |

Разделение на два репозитория предполагает, что **клиентские** и **админские** сервисы развиваются независимо. Однако на практике это не так — бизнес-процессы «размазаны» по обоим репозиториям, и граница между ними не совпадает с границами DDD-ограниченных контекстов (bounded contexts).

### 1.2. Проблема разделения

Разделение `client/backend/` vs `backend/` проведено **по роли пользователя** (клиент/сотрудник), а не по бизнес-доменам. Это приводит к:

- **Один и тот же домен реализован в двух репозиториях** (например, брокерские счета — `account-service` и `account-service-test`)
- **Кросс-репозиторные вызовы** при выполнении одного бизнес-процесса (торговый конвейер затрагивает 4 сервиса из обоих репозиториев)
- **Дублирование кода** — одинаковая бизнес-логика реализована независимо в двух репозиториях
- **Отсутствие единого Ubiquitous Language** — одинаковые сущности называются по-разному в разных репозиториях

---

## 2. Идентифицированные DDD-домены

Анализ контроллеров всех 23 сервисов выявил **12 ограниченных контекстов (bounded contexts)**:

| # | Домен | Описание | Сервисы (чистые) | Сервисы (кросс-доменные) |
|---|---|---|---|---|
| 1 | **Ядро инвестиционной торговли** | Ордера, эмулятор биржи, каталог инструментов, брокерские счета | trading-service, emulator-service, catalog-service | account-service, account-service-test, management-service-pb (частично), userinfo-service (частично) |
| 2 | **Клиенты** | Профиль клиента, регистрационные данные | — | customer-service (частично) |
| 3 | **CRM** | Управление взаимоотношениями с клиентами (admin-side) | — | userinfo-service (частично) |
| 4 | **Безопасность** | Аутентификация, авторизация, OTP | auth-service, otp-service | customer-service (частично) |
| 5 | **Управление персоналом** | Сотрудники, рабочие места, задачи | — | employee-service (частично) |
| 6 | **Бухгалтерия и налоги** | НДФЛ, история транзакций | tax-service, financialtransactions-service | customer-service (частично), userinfo-service (частично) |
| 7 | **Документооборот** | Генерация PDF, 2-НДФЛ, скачивание | document-service, document-service-pb | — |
| 8 | **Тарифный модуль** | Подключение платных услуг | customercare-service | — |
| 9 | **Образование** | Курсы, темы, уроки, квалификационные тесты | education-service, test-service | management-service-pb (частично) |
| 10 | **Поддержка** | Тикеты, шаблоны ответов, обратная связь | support-service, criticalfeedbackchannel | employee-service (частично) |
| 11 | **Уведомления** | Push, SSE, email, история | notification-service, newsfeed-service | — |
| 12 | **Инфраструктура** | API Gateway, маршрутизация | api-gateway | — |

**Ключевой вывод:** ни один из 12 доменов не содержится полностью в одном репозитории. Все значимые бизнес-процессы пересекают границу `client/backend/` ↔ `backend/`.

---

## 3. Кросс-репозиторные процессы

### 3.1. Торговый конвейер

Наиболее критичный пример — полный цикл торговли задействует **6 сервисов из обоих репозиториев**:

```
[backend/]  trading-service
    │  ├── Создание ордера (REST)
    │  └── Kafka: order_request
    │
    ▼
[client/]   emulator-service
    │  ├── Обработка заявки (limit/market/stop)
    │  ├── Kafka: order_result / order_errors
    │  └── Feign → MOEX (котировки каждые 3 мин)
    │
    ├── Kafka: actual_* (котировки)
    │       ▼
    │   [client/] catalog-service (каталог инструментов)
    │
    ├── Kafka: order_result
    │       ▼
    │   [backend/] trading-service (результат обработки)
    │       │
    │       └── Kafka: new_order, order_result_notification
    │               ▼
    │           [client/] notification-service (push клиенту)
    │
    ├── Kafka: accounts_request, trade_history
    │       ▼
    │   [client/] account-service (брокерские счета)
    │
    └── Feign: getBrokerAccounts
            ▼
        [client/] account-service
```

**Проблема:** торговый конвейер — это единый бизнес-процесс, но его реализация размазана на 2 репозитория. Изменение в торговом процессе требует координации между двумя командами, работающими в разных репозиториях.

### 3.2. Конвейер регистрации клиента

```
[client/]   customer-service (registration, JWT auth)
    │
    ├── Keycloak: создание пользователя
    ├── Kafka: user_registration
    │       ▼
    │   [client/] notification-service (welcome-уведомление)
    │
    └── Feign ← [client/] otp-service (OTP при регистрации)
```

### 3.3. Конвейер регистрации сотрудника

```
[backend/]  auth-service (вход, OTP 2FA)
    │
    ├── Kafka: register-account
    │       ▼
    │   [backend/] employee-service (создание записи сотрудника)
    │       │
    │       └── Kafka: register-result
    │               ▼
    │           [backend/] userinfo-service (создание связи менеджер→клиент)
    │
    └── Feign → employee-service (получение данных для токена)
```

### 3.4. Документы и налоги

```
[client/]   document-service (генерация PDF, 2-НДФЛ)
    │
    ├── Feign → [client/] customer-service (getCustomerInfo, getTaxInfo)
    ├── Feign → [client/] account-service (checkAccess)
    ├── Feign → [backend/] tax-service (get2ndfl)
    │                    │
    │                    └── Feign → [client/] account-service (taxWithdraw)
    │
    └── Feign ← [backend/] customercare-service (generateDocument)
```

**Проблема:** формирование справки 2-НДФЛ затрагивает 4 сервиса в обоих репозиториях. Данные о клиенте, его торговых результатах и налогах хранятся в разных сервисах, причём налоговый сервис из `backend/` синхронно вызывает клиентский сервис из `client/backend/`.

### 3.5. Карта кросс-репозиторных связей

| Источник | Цель | Тип | Назначение |
|---|---|---|---|
| trading-service [backend/] | emulator-service [client/] | Kafka | Ордера |
| trading-service [backend/] | account-service [client/] | Feign + Kafka | Брокерские счета |
| trading-service [backend/] | notification-service [client/] | Kafka | Уведомления |
| emulator-service [client/] | catalog-service [client/] | Kafka | Котировки |
| catalog-service [client/] | notification-service [client/] | Kafka | Ценовые уведомления |
| document-service [client/] | tax-service [backend/] | Feign | Данные 2-НДФЛ |
| customercare-service [backend/] | document-service [client/] | Feign | Генерация договора |
| customercare-service [backend/] | account-service [client/] | Feign | Брокерские счета |
| customercare-service [backend/] | customer-service [client/] | Feign | Данные клиента |
| tax-service [backend/] | account-service [client/] | Feign | Налоговые списания |
| employee-service [backend/] | userinfo-service [backend/] | Kafka | Результат регистрации |

**Итого:** 11 кросс-репозиторных связей. 6 из них — синхронные Feign-вызовы, 5 — асинхронные Kafka-сообщения.

---

## 4. Кросс-доменные сервисы

Четыре сервиса нарушают принцип единой ответственности (SRP), реализуя функциональность из нескольких DDD-доменов в одном микросервисе.

### 4.1. userinfo-service (BFF + доменная логика — 5 доменов)

**Репозиторий:** `backend/`  
**9 контроллеров, 22 эндпоинта**

userinfo-service реализует паттерн **BFF (Backend for Frontend)** для админ-панели — агрегирует данные из нескольких доменных сервисов и отдаёт единый API для фронтенда. Часть функциональности является **легитимным BFF** (тонкая агрегация без своей бизнес-логики), но сервис «оброс» доменной логикой, которая не должна находиться в BFF-слое.

#### Легитимный BFF (тонкая агрегация)

Эти компоненты не содержат собственной бизнес-логики — они читают данные из доменных сервисов (через RestClient или Kafka) и передают на фронтенд:

| Компонент | Контроллер | Источник данных | Описание |
|---|---|---|---|
| История торгов | HistoryTradeController | account-service (RestClient/Kafka) | Прокси: читает торговые операции клиента |
| Счета клиентов | AccountDataController | account-service (RestClient/Kafka) | Прокси: читает брокерские счета клиента |
| Данные клиентов (чтение) | CustomersDataController (GET) | customer-service (RestClient/Kafka) | Прокси: список и детальные данные клиента |
| Менеджеры клиентов (чтение) | EmployeeDataController | employee-service + локальная таблица связей | Прокси: данные менеджера для клиента |

#### Доменная логика, не относящаяся к BFF

Эти компоненты содержат **собственную бизнес-логику**, пишут в **локальную БД** и генерируют **доменные события**. По DDD это не функция BFF, а самостоятельные ограниченные контексты, ошибочно помещённые в агрегирующий сервис:

| Компонент | Контроллер | Домен по DDD | Почему не BFF |
|---|---|---|---|
| KYC-верификация | TicketClientController | **Комплаенс** | Локальная БД: `VerificationDto`, `EventDto`. Доменный workflow: получить тикет → подтвердить → записать верификацию → опубликовать Kafka-событие |
| Блокировка клиентов | BlacklistClientController | **Комплаенс** | Мутирующая операция: блокировка/разблокировка + запись в аудит. Делегирует в customer-service, но инициирует side-эффекты |
| Аудит действий | AuditClientController | **Комплаенс** | Локальная БД с полным аудитом действий сотрудников. Фильтры: кто, что, когда, IP, статус. Экспорт отчётов |
| Рефералы | ReferralClientController | **Маркетинг** | Регистрация рефералов, управление бонусами. Локальная бизнес-логика |
| Чат с клиентами | WebsocketController | **CRM** | Инфраструктура WebSocket-соединений, не агрегация |
| Мутации клиентов | CustomersDataController (PATCH/POST) | **CRM** | Редактирование, сброс пароля, экспорт — не просто чтение, а операции с audit trail |
| Связи клиент→менеджер | EmployeeDataController (RelationshipDto) | **CRM** | Локальная таблица `RelationshipDto` — чужие доменные данные хранятся в БД BFF |

**Архитектурные проблемы:**

1. **BFF с собственной БД:** userinfo-service хранит доменные данные, которые принадлежат другим bounded contexts: таблицы связей клиент→менеджер (`RelationshipDto`), верификации (`VerificationDto`), события (`EventDto`), аудит. BFF не должен владеть доменными данными — его задача агрегировать и трансформировать.

2. **Доменные workflow в BFF:** KYC-верификация — это полноценный доменный процесс (получить тикет → проверить данные → подтвердить → уведомить другие сервисы через Kafka). Такой процесс не должен жить в BFF — это отдельный ограниченный контекст «Комплаенс/KYC».

3. **Мутирующие операции:** блокировка клиентов, регистрация рефералов, управление бонусами — это write-операции с доменной семантикой. BFF должен быть преимущественно read-oriented (или тонким оркестратором для write-операций, делегирующим их в доменные сервисы).

4. **Dual-profile транспорт (web/kafka):** userinfo-service — **единственный** сервис в проекте, который имеет две реализации для каждого вызова downstream-сервиса. Для каждого `ServiceLogic`-интерфейса написано два класса: один в пакете `logics/web/` (через Spring `RestClient`), другой в `logics/kafka/` (через `ApplicationKafkaService`). Выбор реализации определяется свойством `service.exchange.type` в `application.yaml`:

```yaml
service.exchange.type: "${EXCHANGE_TYPE:web}"  # по умолчанию — web
```

Spring подставляет нужный бин через `@ConditionalOnProperty`:

```java
// web-реализация (активна по умолчанию)
@ConditionalOnProperty(value = "service.exchange.type", havingValue = "web")
public class CustomerServiceLogicImpl implements CustomerServiceLogic {
    private final RestClient client;
    public ResultResponse blockClient(...) {
        return client.post().uri("...").body(request).retrieve().body(...);
    }
}

// kafka-реализация (не используется в продакшене)
@ConditionalOnProperty(value = "service.exchange.type", havingValue = "kafka")
public class CustomerServiceLogicImpl implements CustomerServiceLogic {
    private final ApplicationKafkaService service;
    public ResultResponse blockClient(...) {
        String json = mapper.toJson(request);
        String response = service.exchangeData(json, ExchangeType.BLACKLIST);
        return mapper.toResultResponse(response);
    }
}
```

Обе реализации делают **одно и то же** — отправляют запрос downstream-сервису. Разница только в транспорте: HTTP или Kafka. При этом:

- По умолчанию установлен режим `web` — kafka-реализация **нигде не используется в продакшене**
- Kafka-реализация использует **RPC поверх Kafka с busy-wait**: отправляет сообщение в топик, кладёт запрос в in-memory `HashMap` (KafkaBox) и крутит цикл с проверкой ответа — это антипаттерн
- Итого **12 классов** вместо 6 — удвоенная поверхность багов
- Kafka-реализация использует **RPC поверх Kafka с busy-wait**: отправляет сообщение в топик, кладёт запрос в in-memory `HashMap` (KafkaBox) и крутит цикл с проверкой ответа — это антипаттерн, который блокирует поток и не даёт преимуществ асинхронности
- Остальные 14 сервисов проекта используют **Feign** для синхронных вызовов и **Kafka** для асинхронных событий — без dual-profile
- Идея переключаемого транспорта может иметь смысл (например, для работы в условиях плохой сети), но реализация через busy-wait и удвоение бизнес-кода сводит преимущества на нет

**Рекомендация:** если dual-profile действительно нужен — вынести транспорт в отдельную абстракцию (Strategy), оставив бизнес-логику в одном классе. Если нет — удалить kafka-реализации, заменить `RestClient` на `Feign` (как в остальных сервисах проекта).

### 4.2. customer-service (один контекст с примесями)

**Репозиторий:** `client/backend/`  
**3 контроллера, 14 эндпоинтов**

customer-service реализует единый ограниченный контекст **«Управление клиентами»** (Customer Management). Регистрация, профиль, рефералы, 2FA — всё это тесно связанные функции, которые меняются по одной причине (изменение в клиенте). Выделение их в отдельные сервисы привело бы к распределённым транзакциям при регистрации.

Однако есть две проблемы:

**Проблема 1: инфраструктура смешана с бизнесом.** `CustomerControllerImpl` зависит от двух сервисов: `CustomerService` (бизнес-логика) и `KeyCloakService` (инфраструктура идентификации). Однако в текущей архитектуре customer-service выступает **провайдером identity** для клиентского фронта — это допустимо как ограниченный контекст «Клиент + Идентификация». Выносить аутентификацию в отдельный `identity-service` имеет смысл только при появлении второй системы, потребляющей те же токены. Проблема не критична, но стоит зафиксировать: если в будущем появится другой клиент (мобильное приложение, партнёрский API), зависимость от Keycloak нужно будет обобщить.

**Проблема 2: налоговые данные.** Эндпоинт `/customers/tax-info` возвращает данные для формы 2-НДФЛ — это функция домена «Бухгалтерия и налоги», а не «Управление клиентами». Налоговый расчёт имеет свою модель и свои причины для изменения, отличные от клиентского профиля.

| Компонент | Эндпоинты | Контекст | Примечание |
|---|---|---|---|
| Аутентификация / Регистрация | `/auth`, `/refresh-token`, `/checklogin`, `/registration`, `/forgot-password`, `/change-password` | Управление клиентами | Инфраструктурная зависимость от KeyCloakService |
| Профиль клиента | `/customers` GET/PATCH, `/customers-list` | Управление клиентами | Чисто |
| 2FA | `/customers-security` PATCH/GET | Управление клиентами | Чисто |
| Рефералы | `/referral/link`, `/referral` | Управление клиентами | Чисто |
| Данные 2-НДФЛ | `/customers/tax-info` | **Бухгалтерия** | Чужой домен |

### 4.3. management-service-pb (2 домена)

**Репозиторий:** `backend/`

| Компонент | Контроллеры | Домен по DDD | Описание |
|---|---|---|---|
| Управление портфелями | PortfolioController + др. | **Ядро инвестиционной торговли** | CRUD готовых портфелей, комиссии, тейк-профит, торговые статусы, история транзакций |
| Администрирование обучения | CourseController, TopicController, LessonController, CategoryController, QuizController | **Образование** | CRUD курсов, тем, уроков, категорий, тесты (quiz) |

**Архитектурная проблема:** management-service-pb нарушает SRP, объединяя управление инвестиционными портфелями (ядро бизнеса) и администрирование образовательного контента (периферийный домен). Эти два набора функций не имеют бизнес-связи — портфели — это финансы, курсы — это обучение.

Сервис также имеет внешние связи с двумя разными доменами:
- `mgmt_portfolio` → `catalog-service` (Feign: `changePortfolio`, `getAllPortfolios`) — Ядро
- `mgmt_portfolio` → `financialtransactions-service` (Feign: `getTransactionsByCustomerId`) — Бухгалтерия

### 4.4. employee-service (2 домена)

**Репозиторий:** `backend/`  
**6 контроллеров, 20 эндпоинтов**

| Компонент | Контроллеры | Домен по DDD | Описание |
|---|---|---|---|
| Управление персоналом | ApplicationEmployeesController, ApplicationPassportController, WorkplaceController, ApplicationTasksController, ApplicationAuditController | **Управление персоналом** | CRUD сотрудников, паспорта, рабочие места (employee/privileged/admin), задачи, аудит-трейл |
| Тикеты поддержки | SupportEmployeeController | **Поддержка** | Создание тикета техподдержки (`CreateTicketRequest` с `customerId`, `supOrderId`) через `SupportTicketService` |

**Архитектурная проблема:** `SupportEmployeeController` расположен по пути `/api/v1/Support/Employee` и использует собственный `SupportTicketService` с DTO `CreateTicketRequest`/`CreateTicketResponse`. Создание тикета поддержки с указанием `customerId` и `supOrderId` — это функциональность домена «Поддержка», не связанная с управлением персоналом. Наличие отдельного сервиса `SupportTicketService` внутри employee-service подтверждает, что это отдельный bounded context, ошибочно помещённый в чужой сервис.

---

## 5. Дублирование сервисов

### 5.1. account-service ↔ account-service-test

| Аспект | account-service (`client/backend/`) | account-service-test (`backend/`) |
|---|---|---|
| Пакет | `com.astondevs` | `com.astondevs.accountservice` |
| Контроллеры | BrokerAccount, Accounts, CustomerAssets, TradeHistory, Operations, OperationHistory | BrokerAccount, Accounts, CustomerAssets, TradeHistory, Operations, OperationHistory |
| Базовые пути | `/api/v1/account-service/**` | `/api/v1/account-service/**` |
| Доп. функции | OTP, маржинальные счета, рефералы, Kafka (consumer + producer) | Только REST (no Kafka) |
| Название | Понятное | Обманчивое: суффикс "-test" |

**6 контроллеров с почти идентичными путями.** Оба сервиса работают с одними и теми же сущностями — брокерские счета, активы, история операций. Разница в том, что `account-service` (client) более развитый.

Это прямое нарушение DDD: **один и тот же ограниченный контекст (брокерские счета) реализован дважды** в разных репозиториях. Каждый из них имеет свою БД, свою схему, свою логику. Рассинхронизация неизбежна.

### 5.2. document-service ↔ document-service-pb

| Аспект | document-service (`client/backend/`) | document-service-pb (`backend/`) |
|---|---|---|
| Ядро | Одинаковое (generate/save) | Одинаковое (generate/save) |
| Доп. функции | 2-НДФЛ, скачивание, предпросмотр | Только генерация |
| Deprecated | Есть deprecated-эндпоинты | Старая реализация |

document-service — более развитая версия, document-service-pb — старый back-office вариант с тем же ядром генерации. По DDD это один ограниченный контекст «Документооборот», размазанный на два репозитория.

---

## 6. Мёртвые и полумёртвые сервисы

| Сервис | Статус | Описание |
|---|---|---|
| **newsfeed-service** | Мёртвый | Нет контроллеров, нет JPA, нет Kafka listeners. Заглушка `App.java`. Занимает resources (Docker-образ, Helm chart, маршрут в API Gateway) |
| **support-service** | Полумёртвый | `OrderController` полностью закомментирован. Работает только чтение шаблонов ответов (активных/неактивных). Создание заявок невозможно |
| **criticalfeedbackchannel** | Минимальный + уязвимость | Один публичный POST-эндпоинт **без авторизации** — потенциальная дыра в безопасности: можно залить мусор или провести DoS-атаку. Group ID `org.example` — placeholder |

---

## 7. Анализ по DDD-принципам

### 7.1. Bounded Context (Ограниченный контекст)

**Статус: НЕ СОБЛЮДАЕТСЯ**

Ни один из 12 доменов не является «чистым» bounded context:

| Домен | Реализован в репозиториях | Количество сервисов | Кросс-доменные включения |
|---|---|---|---|
| Ядро инвестиционной торговли | client/ + backend/ | 6+ | management-service-pb, userinfo-service содержат части ядра |
| Клиенты | client/ | 1 | customer-service — единый контекст, но с инфраструктурной зависимостью (Keycloak) |
| CRM | backend/ | 1 | userinfo-service смешан с Комплаенс, Маркетинг, Ядро |
| Безопасность | client/ + backend/ | 3 | customer-service содержит аутентификацию |
| Управление персоналом | backend/ | 1 | employee-service содержит Поддержку |
| Бухгалтерия | backend/ | 2 | customer-service содержит tax-info, userinfo-service содержит торговую историю |
| Документооборот | client/ + backend/ | 2 | Дублирование между репозиториями |
| Образование | backend/ | 2+ | management-service-pb содержит CRUD курсов |
| Поддержка | backend/ | 2 | employee-service содержит создание тикетов |

### 7.2. Ubiquitous Language (Единый язык)

**Статус: ЧАСТИЧНО СОБЛЮДАЕТСЯ**

В DDD единый язык существует **внутри каждого ограниченного контекста**, а не глобально. Разные термины в разных контекстах — это нормально, если они осознанны и документированы:

| Сущность | Контекст CRM (userinfo) | Контекст Клиенты (customer) | Контекст Безопасность (auth) | Корректно? |
|---|---|---|---|---|
| Человек | `client` | `customer` | `user` | Да — разные роли в разных контекстах |
| Сотрудник | `manager` | — | `admin` | Да — разные роли |
| Брокерский счёт | `BrokerAccounts` | `BrokerAccount` | — | Частично — два торговых контекста с разными терминами |
| Заявка | `ticket` | — | `supOrder` / `order` | Нет — путаница между контекстами Поддержки |

**Проблема:** в некоторых случаях разница терминов — не осознанный выбор контекста, а отсутствие координации. Особенно `ticket` vs `supOrder` vs `order` — три разных названия для заявки в поддержке, которые не отражают разные модели, а просто результат независимой разработки. Аналогично `BrokerAccount` vs `BrokerAccounts` (множественное число) — не разные модели, а отсутствие конвенции именования.

**Рекомендация:** не унифицировать термины глобально, а зафиксировать язык в каждом bounded context и описать трансляцию на границах (Context Map). Устранить случайные расхождения (ticket/supOrder, BrokerAccount/BrokerAccounts).

### 7.3. Aggregate Root (Корень агрегата)

**Статус: ЧАСТИЧНО СОБЛЮДАЕТСЯ** (management-service-pb, trading-service, частично account-service)

Aggregate Root — группа связанных сущностей, которые всегда изменяются вместе в одной транзакции. Корень — единственная «точка входа»: внешний код ссылается только на корень, а не на вложенные сущности. Корень гарантирует консистентность всей группы.

**Важно:** в DDD связи между **разными агрегатами** должны быть через идентификаторы (UUID), а не через JPA-ссылки. Отсутствие `@ManyToOne` между Task и Employee — это **корректно**, если они разные агрегаты. Отсутствие FK constraint — это проблема целостности данных, но не обязательно нарушение DDD. Ниже анализируются агрегаты с учётом этого разделения.

#### management-service-pb — правильные агрегаты

Единственный сервис с корректными агрегатами:

```
QuizModel (корень, @OneToMany orphanRemoval=true)
  ├── QuestionModel (orphanRemoval=true)
  │     └── AnswerModel (orphanRemoval=true)
  └── QuizAttemptModel (cascade=ALL)
        └── UserAnswerModel (cascade=ALL, orphanRemoval=true)
```

Гарантии:
- Нельзя создать вопрос без квиза — привязан через FK
- Удаление квиза автоматически удаляет все вопросы и ответы (`orphanRemoval=true`)
- Внешний код не обращается к `AnswerModel` через репозиторий напрямую — только через корень

Аналогично: `CourseModel` → `LessonModel` (cascade=ALL, orphanRemoval=true), `PortfolioCreateBriefcaseEntity` → `PortfolioCreateAssetEntity` + `PortfolioCreateAllocationEntity` (cascade=ALL, orphanRemoval=true).

#### account-service — корректный агрегат

```java
// BrokerAccount — корень агрегата «Брокерский счёт»
@OneToOne(mappedBy = "brokerAccount", cascade = CascadeType.ALL)
private DepoAccount depoAccount;  // cascade=ALL — правильно, депо-счёт — часть агрегата
```

`BrokerAccount` управляет жизненным циклом `DepoAccount` — это корректно: депо-счёт не существует без брокерского.

```java
// TradeHistory — ссылка на агрегат через идентификатор
@ManyToOne(optional = false, fetch = LAZY)
private BrokerAccount brokerAccount;  // без cascade — правильно
```

**Отсутствие cascade на TradeHistory — правильное решение.** История торгов — это неизменяемые события, которые должны сохраняться для отчётности и аудита после закрытия счёта. TradeHistory — отдельный агрегат (или часть агрегата «Операция»), который ссылается на BrokerAccount через идентификатор (FK). Удаление счёта не должно каскадно удалять историю.

#### trading-service — корректный агрегат

```java
// Portfolio — корень агрегата
@OneToMany(mappedBy = "portfolio", cascade = ALL, fetch = LAZY)
private List<PortfolioManagement> statusHistory;  // статус — часть агрегата

@OneToMany(mappedBy = "portfolio", cascade = ALL, fetch = LAZY)
private List<Order> assetOrders;  // ордера — часть агрегата
```

Portfolio владеет своими ордерами и историей статусов — корректно. `OrderStatusHistory` ссылается на `Order` через `@ManyToOne` — это отдельный агрегат (read model), что тоже допустимо.

#### userinfo-service — проблемы с транзакционными границами

6 сущностей без JPA-связей. Часть из этого — корректно (ссылки на агрегаты в других сервисах через UUID), часть — проблема:

**Корректно:** `VerificationEntity.eventId` ссылается на `EventEntity` через UUID. Если Event и Verification — разные агрегаты (событие может существовать без верификации), то UUID-ссылка правильна по DDD.

**Проблема: нет транзакционной границы при подтверждении верификации.** Даже если Event и Verification — разные агрегаты, workflow подтверждения должен гарантировать атомарность:

```java
EventDto event = eventService.getByEventId(eventId);         // шаг 1: найти событие
verificationService.registerVerification(event, employeeId);  // шаг 2: создать верификацию
kafkaTemplate.send("tickets", eventId, response);             // шаг 3: отправить Kafka
```

Если шаг 2 упадёт — событие найдено, верификация не создана. Если шаг 3 упадёт — верификация создана, другие сервисы не узнают. Нет ни агрегатной обёртки, ни Outbox Pattern.

**Проблема: Dialog и Message — логически один агрегат, но не формализован.**

```java
// MessageEntity.java
UUID dialogId;  // UUID-ссылка на DialogEntity
```

Если Dialog — корень агрегата, а Message — вложенная сущность, то:
- Создание/удаление сообщений должно идти через Dialog (а не через отдельный `MessageRepository`)
- Удаление диалога должно удалять сообщения (orphanRemoval или application-level cascade)

Сейчас Message создаётся через `MessageRepository` напрямую, минуя Dialog — это нарушение инварианта агрегата.

**Однако:** в высоконагруженном чате (особенно с WebSocket) часто сознательно делают Message самостоятельным агрегатом, чтобы избежать блокировок на Dialog при массовой вставке сообщений. Это компромисс между консистентностью и производительностью — допустимый инженерный trade-off, который стоило бы зафиксировать в документации. Если текущая реализация осознанная — это не проблема, а архитектурное решение.

#### employee-service — корректные границы агрегатов

6 сущностей, 0 JPA-связей. Ссылки через сырые UUID:

```java
// TaskEntity.java
UUID employeeId;  // ссылка на другой агрегат через ID — корректно по DDD

// SupportTicketEntity.java
UUID employeeId;  // ссылка на другой агрегат через ID — корректно
UUID customerId;  // ссылка на другой агрегат через ID — корректно
```

Task и Employee — разные агрегаты: задача может существовать для уволенного сотрудника, а сотрудник — без задач. Прямая JPA-связь `@ManyToOne` создала бы жёсткую зависимость и проблему lazy loading при удалении сотрудника. UUID-ссылка — правильное решение.

Аналогично SupportTicket: тикет ссылается на сотрудника и клиента через UUID, потому что это отдельный агрегат, который не владеет их жизненным циклом.

**Единственный вопрос:** отсутствие FK constraints на уровне БД. Это не нарушение DDD (агрегаты общаются через ID), но снижает целостность данных. В распределённой системе это допустимо, если консистентность обеспечивается на уровне приложения.

### 7.4. Domain Events (Доменные события)

**Статус: ЧАСТИЧНО СОБЛЮДАЕТСЯ**

Kafka используется для доменных событий, но без формализации:

| Событие | Формат | Корректно? |
|---|---|---|
| `order_request` / `order_result` | DTO через interservice-lib | Да — асинхронный торговый конвейер |
| `actual_stocks` / `actual_bonds` | DTO через interservice-lib | Да — пайплайн котировок |
| `otp_notification` | DTO через interservice-lib | Да |
| `user_auth_notification` | DTO через interservice-lib | Да |
| `register-account` / `register-result` | DTO через interservice-lib | Да — конвейер регистрации |
| Блокировка клиента | REST/Kafka через userinfo → customer | Синхронный fallback при недоступности Kafka |
| KYC-верификация | Kafka-событие в userinfo-service | Локальное событие без формального доменного события |

Outbox Pattern реализован только в trading-service и emulator-service. Остальные сервисы публикуют Kafka-события без гарантии at-least-once.

**CRITICAL: отправка outbox-сообщений отключена в trading-service.** Метод `sendStatusChangeNotificationBatch()` в trading-service содержит **закомментированный** вызов `sendBatchMessages()`. Это означает, что доменные события об изменении статуса ордеров (executed, rejected, expired, cancelled) **никогда не публикуются в Kafka**, несмотря на наличие Outbox Pattern. Downstream-сервисы (notification-service, account-service) не получают уведомления об изменении статуса ордеров. Это нарушение одного из ключевых принципов DDD: доменные события должны быть опубликованы надёжно и своевременно.

### 7.5. Context Map (Карта контекстов)

**Статус: ОТСУТСТВУЕТ**

Context Map — стратегический паттерн DDD, описывающий отношения между bounded contexts: кто кому предоставляет данные, в каком направлении идёт зависимость, и как происходит трансляция моделей. В проекте нет формальной Context Map. Ниже — анализ фактических отношений.

#### Upstream/Downstream (Поставщик/Потребитель)

Один контекст (Upstream) предоставляет API, другой (Downstream) потребляет. Downstream зависит от модели Upstream.

**customer-service — главный Upstream проекта.** Его вызывают 5 сервисов:

```
                        customer-service (UPSTREAM)
                        Модель: Customer, registration, auth
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     account-service  notification  userinfo-service
     (DOWNSTREAM)      (DOWNSTREAM)  (DOWNSTREAM)
     document-service  otp-service   customercare-service
     (DOWNSTREAM)      (DOWNSTREAM)  (DOWNSTREAM)
```

Если customer-service изменит структуру ответа `/customers` или уберёт поле — все 5 потребителей сломаются. Нет контрактных тестов, нет явного API-контракта, нет версии API.

#### Conformist (Конформист)

Downstream принимает модель Upstream без попыток адаптации.

Все 5 потребителей customer-service — конформисты:

```java
// document-service — использует модель customer-service как есть
@FeignClient(name = "CustomerServiceClient")
public interface CustomerServiceApiClient {
    @GetMapping("/customers")
    CustomerInfoResponse getCustomerInfo(@RequestHeader String customer_id);
}
```

document-service не трансформирует модель — использует `CustomerInfoResponse` напрямую. Если customer-service добавит/удалит поле — document-service либо проигнорирует (Jackson lenient), либо сломается. Для стабильного API это допустимо, для развивающегося — рискованно.

#### Customer/Supplier (Заказчик/Поставщик)

Downstream может влиять на API Upstream. Upstream учитывает потребности Downstream.

**tax-service → account-service:**

```
tax-service (CUSTOMER)  ──Feign──►  account-service (SUPPLIER)
"Мне нужен getBrokerAccounts()      "Вот метод, используй"
 для расчёта НДФЛ"
```

tax-service для расчёта НДФЛ вызывает account-service. Но фактически это **Conformist**, а не Customer/Supplier: tax-service не может повлиять на API account-service. Нет контрактных тестов, нет координации изменений.

#### Anti-Corruption Layer (Слой защиты от коррупции)

Downstream создаёт слой трансляции между своей моделью и моделью Upstream, чтобы чужая модель не «протекла» в его домен.

**userinfo-service — неформальный ACL:**

```
userinfo-service
  ┌─────────────────────────────────┐
  │     Внутренняя модель:          │
  │     DetailClientResponse,       │
  │     ManagerDataResponse         │
  │           │                     │
  │     CustomerServiceLogic        │  ← интерфейс (ACL)
  │       │         │               │
  │   [web]       [kafka]           │  ← две реализации трансляции
  │   RestClient   KafkaMapper      │
  └─────┼────────────┼──────────────┘
        │            │
   customer-     Kafka topic
   service       "customer"
```

userinfo-service НЕ использует модель customer-service напрямую — вызывает через `CustomerServiceLogic`, трансформирует в свою модель (`DetailClientResponse`). Это неформальный ACL. Но реализован неграмотно: вместо одного слоя трансляции — два (web/kafka), плюс DTO userinfo почти 1:1 совпадают с ответами customer-service, то есть модель всё равно «протекает».

#### Shared Kernel (Разделяемое ядро)

Несколько контекстов разделяют общую часть модели (DTO). Изменения согласовываются между всеми участниками.

**interservice-interaction-dto-lib:**

```
┌─────────────────────────────────────┐
│  interservice-interaction-dto-lib   │
│  (Shared Kernel)                    │
│                                     │
│  OrderRequestDto                    │
│  OrderResultDto                     │
│  AccountRequestDto                  │
│  OtpNotificationDto                 │
│  ...                                │
└──────────┬──────────────────────────┘
           │
    ┌──────┼──────┐
    │      │      │
 trading  emulator  account
 service  service   service
```

Правильная идея: DTO для Kafka-топиков вынесены в общую библиотеку. Но:

- **3 версии** (0.0.3, 0.0.3a, 0.0.3f) — Shared Kernel рассинхронизирован
- emulator-service может быть на 0.0.3, а trading-service на 0.0.3f — `OrderRequestDto` может отличаться
- Нет Schema Registry — совместимость Kafka-сообщений не проверяется
- **Нарушение DDD:** Shared Kernel должен изменяться только с согласия всех участников. Сейчас каждый сервис тянет свою версию

#### Partnership (Партнёрство)

Два контекста координируются напрямую — изменения в одном требуют синхронных изменений в другом.

**trading-service ↔ emulator-service:**

```
trading-service  ──order_request──►  emulator-service
                 ◄──order_result───
                 ◄──order_errors───
```

Торговый конвейер не работает, если эти два сервиса не согласованы. Формат `OrderRequestDto` и `OrderResultDto` из Shared Kernel должен совпадать. Добавление нового типа ордера в trading-service требует обработки этого типа в emulator-service.

Проблема: сервисы в **разных репозиториях** (`backend/` и `client/backend/`). Координация изменений — ручная.

#### Итоговая Context Map проекта

```
                    ┌─────────────────────┐
                    │   Keycloak (OHS)    │
                    │   External IdP      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   API Gateway       │
                    │   (routing only)    │
                    └──────────┬──────────┘
                               │
    ┌──────────────────────────┼───────────────────────────┐
    │                          │                           │
    ▼                          ▼                           ▼
┌───────────┐          ┌──────────────┐           ┌───────────────┐
│ customer- │◄─Conform─│   userinfo-  │           │   trading-    │
│ service   │◄─Conform─│   service    │           │   service     │
│ (Upstream)│          │   (BFF/ACL)  │           │               │
└─────┬─────┘          └──────┬───────┘           └───────┬───────┘
      │                       │                           │
      │                  ┌────┴────┐                Partnership
  Conformist           Conformist │                (order pipeline)
      │                  │        │                      │
      ▼                  ▼        ▼                      ▼
┌───────────┐    ┌──────────┐ ┌──────────┐      ┌──────────────┐
│ account-  │    │ employee-│ │customerc│      │  emulator-   │
│ service   │    │ service  │ │ are-svc │      │  service     │
│ (Upstream)│    └──────────┘ └─────────┘      └──────┬───────┘
└─────┬─────┘                                          │
      │                                          ┌─────┴──────┐
  Customer/                                    Shared Kernel
  Supplier                                     (Kafka DTOs,
      │                                         3 версии)
  ┌───┼───────────────┐
  │   │               │
  ▼   ▼               ▼
tax  document     catalog
svc  service      service
```

**Ключевые проблемы:**

1. Нет формальной Context Map — отношения между контекстами подразумеваются, а не документируются
2. customer-service и account-service — два Upstream без Open Host Service (нет версионированного API, нет контрактных тестов)
3. Shared Kernel рассинхронизирован (3 версии DTO-библиотеки)
4. Partnership между trading-service и emulator-service затруднён разными репозиториями

### 7.6. Repository Pattern

**Статус: СОБЛЮДАЕТСЯ (формально)**

Все сервисы используют Spring Data JPA repositories для доступа к данным. JPA-сущности во многих случаях выступают одновременно как доменные объекты — в `management-service-pb` (CourseModel, QuizModel) и `trading-service` (Portfolio, Order) сущности содержат бизнес-методы и JPA-аннотации. В Spring Data JPA это нормальная практика: entity не обязана быть «анемичной».

Однако:

- userinfo-service хранит данные из **чужих доменов** (Relationship, Verification, Event) в своей локальной БД — это проблема принадлежности данных, а не паттерна Repository
- Не во всех сервисах агрегатные границы формализованы — часть репозиториев позволяет обращаться к вложенным сущностям напрямую, минуя корень агрегата

---

## 8. Рекомендации

### 8.1. Приоритет: HIGH — Разделение кросс-доменных сервисов

| Сервис | Действие | Целевые сервисы |
|---|---|---|
| **userinfo-service** | Превратить в **тонкий BFF-фасад**: оставить агрегацию чтения (HistoryTrade, AccountData, CustomersData GET, EmployeeData) и простые оркестрации. Убрать владение чужими доменными данными (таблицы Relationship, Verification, Event). Вынести доменные workflow: KYC-верификацию → в compliance-service, аудит → в audit-service. Рефералы и чат — опционально (можно оставить в BFF как часть UI-опыта). Удалить kafka-реализации dual-profile, перейти на Feign. Цель — не уничтожить BFF, а освободить от чужой БД и бизнес-логики других доменов. | 2-3 новых сервиса + чистый BFF |
| **customer-service** | Один контекст «Управление клиентами» — не разделять. Вынести зависимость от KeyCloakService за пределы доменного слоя (шаблон Domain Service + Infrastructure Adapter). tax-info → перенести в tax-service. | 1 перераспределение + рефакторинг |
| **management-service-pb** | Разделить на management-portfolio-service (Ядро) и education-admin-service (Образование). | 2 сервиса |
| **employee-service** | Вынести SupportEmployeeController → support-service или отдельный ticket-service. | 1 перераспределение |

### 8.2. Приоритет: HIGH — Устранение дублирования

| Действие | Описание |
|---|---|
| Объединить account-service + account-service-test | Один сервис в одном репозитории. Удалить account-service-test (обманчивое название, дублирующий функционал). Дополнить account-service back-office эндпоинтами при необходимости. |
| Объединить document-service + document-service-pb | Один сервис. document-service-pb — старая реализация, заменить на client-версию. |
| Удалить newsfeed-service | Пустой сервис без реализации. Удалить Docker-образ, Helm chart, маршрут в API Gateway. |
| Решить судьбу support-service | Либо восстановить закомментированный OrderController, либо удалить сервис и перенести шаблоны в employee-service/support-ticket-service. |

### 8.3. Приоритет: MEDIUM — Реструктуризация репозиториев

| Действие | Описание |
|---|---|
| Ввести правила изоляции контекстов | Оставить раздельные репозитории, но ввести правила: API Gateway как единая точка входа, нет прямых Feign-вызовов между bounded contexts (только через публичный API или Kafka). Монорепозиторий не решит проблему — он сделает кросс-доменные вызовы проще и незаметнее. |
| Создать Context Map | Формализовать отношения между bounded contexts: Upstream/Downstream, Conformist, ACL, Shared Kernel. |
| Зафиксировать Ubiquitous Language по контекстам | В каждом bounded context — свой единый язык. В контексте CRM сущность — `Client`, в торговом — `Investor`, в налоговом — `Taxpayer`. Не унифицировать глобально — это противоречит DDD. При интеграции контекстов использовать ACL для трансляции терминов. |
| Стандартизировать interservice-interaction-dto-lib | Одна версия для всех сервисов. Контрактное тестирование. |

### 8.4. Приоритет: LOW — Зрелость DDD

| Действие | Описание |
|---|---|
| Ввести доменные события | Формализовать все Kafka-топики как доменные события с версионированием схемы (Schema Registry). |
| Outbox Pattern для критических событий | Outbox нужен только там, где потеря события недопустима (ордера, платежи, верификация). Для некритичных событий (уведомления, логи, аналитика) достаточно обычного Kafka-продюсера с идемпотентностью на стороне consumer. Не применять Outbox повсеместно без оценки необходимости. |
| Ввести Aggregate Roots | Выделить корни агрегатов в коде (отдельные классы, отдельные репозитории). Запретить прямое изменение вложенных сущностей. Учитывать инженерные trade-offs: в высоконагруженных сценариях (чаты, потоки событий) допустимо делать вложенные сущности самостоятельными агрегатами для производительности. |
| Ввести Domain Layer | Выделить доменный слой (entities, value objects, domain services) отдельно от инфраструктурного (JPA repositories, Kafka producers, Feign clients). JPA-entities могут быть доменными объектами — это нормальная практика Spring Data JPA. |
