# Архитектурный обзор Liberty Investment

Документ описывает текущее (as-is) состояние архитектуры системы на верхнем уровне с явно зафиксированной границей между клиентской и административной частями. Источник — `minutes-full.md`, ревизия исходного кода. Графическая часть — три диаграммы в нотации C4: контекстная (`c1-context.puml`, рис. 1), контейнерная клиентской части (`c2-client-containers.puml`, рис. 2), контейнерная административной части (`c2-admin-containers.puml`, рис. 3).

Цветовая маркировка на диаграммах: `#5B9BD5` — клиентская часть, `#70AD47` — административная часть, `#3CB371` — общая инфраструктура, `#F4B400` — компонент с архитектурным дефицитом или дефектом защиты.

## 0. Термины и определения

**Клиентская часть** — функциональная подсистема, обеспечивающая выполнение бизнес-операций конечным пользователем (инвестором). Включает торговлю, управление портфелем, доступ к счетам и активам, формирование документов, каталог инструментов и уведомления. Точкой доступа выступает публичное клиентское веб-приложение; аутентификация пользователей выполняется внешним поставщиком удостоверений Keycloak с проверкой токенов в `JwtFilter` на уровне API Gateway. Подсистема реализует ядро учёта инвестиционных операций.

**Административная часть** — функциональная подсистема, обеспечивающая выполнение внутренних операций сотрудниками компании (менеджерами). Включает ведение клиентов (CRM), поддержку, управление сотрудниками (HR), формирование образовательного контента, управление готовыми портфелями, финансовую аналитику и подключение платных услуг. Точкой доступа выступает внутренний интерфейс; аутентификация менеджеров выполняется внутренним сервисом `auth-service` с проверкой токенов в `AuthJwtFilter` на уровне API Gateway.

Граница между подсистемами проходит по типу пользователя и контексту операций: клиентская часть обслуживает внешних инвесторов в публичном контуре, административная часть — внутренних сотрудников в корпоративном контуре. Компоненты API Gateway, Kafka и внешние системы (MOEX, Keycloak, SMTP) являются общими и не относятся ни к одной из подсистем.

## 1. Архитектурный контекст (рис. 1)

Система Liberty Investment реализована как экосистема микросервисов, функционально разделённая на две подсистемы.

**Акторы:**
- Клиент (инвестор) — конечный пользователь, выполняющий торговые операции и управляющий портфелем через клиентский веб-интерфейс.
- Менеджер компании — внутренний пользователь, осуществляющий back-office-операции.

**Внешние системы:**
- MOEX — источник рыночных котировок и справочной информации по инструментам.
- Keycloak — внешний поставщик удостоверений, обеспечивающий выпуск и интроспекцию JWT-токенов клиентской части.
- Почтовый сервер — транспорт уведомлений и OTP-сообщений (SMTP).

Между подсистемами установлены двусторонние интеграционные потоки: административная часть агрегирует клиентские данные через Feign-клиенты и Kafka-топики; клиентская часть получает справочные и контентные данные (готовые портфели, курсы обучения, тесты) из административных сервисов.

**Рис. 1. Контекстная диаграмма (C4 L1).**

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

title Контекстная диаграмма (C4 L1) — Liberty Investment (AS-IS)

LAYOUT_TOP_DOWN()
skinparam linetype ortho
skinparam nodesep 40
skinparam ranksep 30
skinparam backgroundColor transparent

' ЛЕГЕНДА ЦВЕТОВ (AS-IS — по физическому/требуемому положению):
'   #5B9BD5 = клиентская часть
'   #70AD47 = административная часть
'   #F4B400 = проблема архитектуры (долг / дыра)

' === АКТОРЫ ===
Person(клиент, "Клиент\n(Инвестор)", "Регистрируется, торгует,\nуправляет портфелем")
Person(менеджер, "Менеджер\nкомпании", "Ведёт клиентов, поддержка,\nHR, образование, финансы")

' === ВНЕШНИЕ СИСТЕМЫ ===
System_Ext(moex, "MOEX", "Котировки")
System_Ext(keycloak, "Keycloak (IdP)", "Аутентификация клиентов\n(только клиентская часть)")

' === ГЛАВНАЯ СИСТЕМА: ДВЕ ЧАСТИ AS-IS ===
System_Boundary(liberty, "Liberty Investment") {

    System(клиент_часть, "Клиентская часть\n(ядро учёта)", "account, catalog, customer (+auth!),\ndocument, emulator, notification, otp,\ntrading (+API Gateway как точка входа)\n\n⚠ безопасность клиента РАЗМАЗАНА:\n  customer-service держит auth/registration/2FA") #5B9BD5

    System(админ_часть, "административная часть\n(модули)", "userinfo, support, employee, auth,\neducation, test, management-pb,\nfinancialtransactions, tax, customercare\n\n⚠ безопасность менеджера в auth-service,\nНО @PreAuthorize только в management-pb/education;\nuserinfo — БЕЗ авторизации операций") #70AD47
}

' === СВЯЗИ АКТОРОВ ===
Rel(клиент, клиент_часть, "HTTPS / WebSocket", "Торгует, портфель")
Rel(менеджер, админ_часть, "HTTPS", "Back-office")

' === ВЗАИМОДЕЙСТВИЕ ЧАСТЕЙ ===
Rel(админ_часть, клиент_часть, "Feign/Kafka", "Агрегация клиентских данных")
Rel(клиент_часть, админ_часть, "REST/Kafka (read)", "Курсы, портфели, тесты")

' === ВНЕШНИЕ ===
Rel(клиент_часть, moex, "Котировки", "HTTPS/Feign")
Rel(клиент_часть, keycloak, "Token introspection", "HTTPS")
Rel(админ_часть, keycloak, "косвенно через клиентские сервисы", "Feign")

legend right
  |= Цвет |= Значение |
  |<back:#5B9BD5>   </back>| Клиентская часть |
  |<back:#70AD47>   </back>| административная часть |
  |<back:#F4B400>   </back>| Проблема архитектуры (долг / дыра) |
endlegend

@enduml
```

## 2. Контейнерная декомпозиция

### 2.1 Инфраструктурные компоненты

**API Gateway** (Spring Cloud Gateway WebFlux) — единая точка входа, реализующая маршрутизацию запросов, термирование нагрузки (Circuit Breaker) и политики CORS. На уровне Gateway функционируют два фильтра аутентификации:
- `JwtFilter` — проверка валидности токена Keycloak клиентской части;
- `AuthJwtFilter` — проверка внутреннего JWT менеджеров административной части.

Маршрутизация фильтров по эндпоинтам: `AuthJwtFilter` применяется исключительно к `/auth-service/**` и `/employee-service/**`; все прочие маршруты, включая административные `userinfo-service`, `management-service-pb`, `tax-service`, `customercare-service`, `financialtransactions-service`, проходят через `JwtFilter`.

### 2.2 Клиентская часть (рис. 2)

**Рис. 2. Контейнерная диаграмма клиентской части (C4 L2).**

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

title Контейнерная диаграмма (C4 L2) — КЛИЕНТСКАЯ ЧАСТЬ (AS-IS)

LAYOUT_TOP_DOWN()
skinparam linetype ortho
skinparam nodesep 35
skinparam ranksep 20
skinparam backgroundColor transparent
skinparam ContainerFontSize 11
skinparam BoundaryFontSize 12

Person(клиент, "Клиент\n(Инвестор)", "Торгует, видит портфель")

System_Ext(moex, "MOEX", "Котировки")
System_Ext(keycloak, "Keycloak (IdP)", "JWT клиентов")
System_Ext(mail, "Почтовый сервер", "Email + OTP")

Boundary(infra, "Инфраструктура") {
    Container(api_gw, "API Gateway", "Spring Cloud Gateway WebFlux", "Единая точка входа.\nJwtFilter (Keycloak) проверяет токен клиента на маршруте.\nТОЛЬКО аутентификация, НЕ авторизация уровня операций") #3CB371
}

Boundary(client_part, "Клиентская часть (ядро учёта)") {
    Container(react_app, "React SPA", "React 18, Vite, RTK Query", "Клиентское инвестиционное приложение") #5B9BD5
    Container(account_svc, "account-service", "Spring Boot 3.5.0", "Брокерские/депо/маржинальные счета, активы, история операций") #5B9BD5
    Container(catalog_svc, "catalog-service", "Spring Boot 3.5.0", "Каталог инструментов, котировки, портфели, избранное") #5B9BD5
    Container(customer_svc, "customer-service", "Spring Boot 3.5.0", "Профиль клиента, рефералы +\nauth/registration/2FA/refresh/forgot-password\n⚠ смешивает профиль и безопасность — долг") #F4B400
    Container(document_svc, "document-service", "Spring Boot 3.5.0", "PDF, 2-НДФЛ, скачивание") #5B9BD5
    Container(emulator_svc, "emulator-service", "Kotlin + Spring Boot", "Эмулятор биржи, обработка ордеров") #5B9BD5
    Container(notification_svc, "notification-service", "Spring Boot 3.5.0", "Push/SSE/Email") #5B9BD5
    Container(otp_svc, "otp-service", "Spring Boot 3.5.0", "Генерация/валидация OTP (security-функция)") #5B9BD5
    Container(trading_svc, "trading-service", "Spring Boot 3.5.0", "Ордера, портфели, комиссии, Outbox\n⚠ физически в backend/, по требованиям — клиентский") #F4B400
}

System_Ext(admin_part, "административная часть\n(см. рис. 3)", "education, management-service-pb,\ntax, financialtransactions —\nпоставляют read-данные")

Rel(клиент, react_app, "HTTPS / WebSocket", "Торгует")
Rel(react_app, api_gw, "REST + SSE", "HTTPS")
Rel(api_gw, account_svc, "", "REST")
Rel(api_gw, catalog_svc, "", "REST")
Rel(api_gw, customer_svc, "", "REST")
Rel(api_gw, document_svc, "", "REST")
Rel(api_gw, emulator_svc, "", "REST")
Rel(api_gw, notification_svc, "", "REST")
Rel(api_gw, otp_svc, "", "REST")
Rel(api_gw, trading_svc, "", "REST")
Rel(api_gw, keycloak, "Token introspection", "HTTPS")
Rel(emulator_svc, moex, "Котировки", "HTTPS/Feign")
Rel(notification_svc, mail, "Email", "SMTP")
Rel(customer_svc, otp_svc, "verify OTP", "Feign")
Rel(catalog_svc, admin_part, "Готовые портфели, курсы (read)", "REST/Feign")
Rel(trading_svc, admin_part, "Каталог комиссий (read)", "Feign")

legend right
  |= Цвет |= Значение |
  |<back:#5B9BD5>   </back>| Клиентский сервис |
  |<back:#3CB371>   </back>| Общая точка входа (Gateway) |
  |<back:#F4B400>   </back>| Проблема архитектуры (долг / смешение) |
endlegend

@enduml
```

| Контейнер | Функциональная ответственность |
|---|---|
| React SPA | Клиентский интерфейс инвестора |
| account-service | Брокерские, депозитарные и маржинальные счета, активы, история операций |
| catalog-service | Каталог инструментов, котировки, портфели, избранное |
| customer-service | Профиль клиента, реферальная программа, аутентификация и регистрация, 2FA, refresh-token, восстановление пароля |
| document-service | PDF-документы, формы 2-НДФЛ, скачивание |
| emulator-service | Эмулятор биржи, обработка ордеров, получение котировок MOEX |
| notification-service | Push-, SSE- и email-уведомления |
| otp-service | Генерация и валидация одноразовых кодов подтверждения |
| trading-service | Ордера, портфели, комиссии, паттерн Outbox |

Интеграция с внешними системами реализована через Feign-клиенты (`emulator-service` ↔ MOEX, `notification-service` ↔ SMTP) и REST-вызовы к Keycloak для интроспекции токенов.

### 2.3 Административная часть (рис. 3)

**Рис. 3. Контейнерная диаграмма административной части (C4 L2).**

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

title Контейнерная диаграмма (C4 L2) — административная часть (AS-IS)

LAYOUT_TOP_DOWN()
skinparam linetype ortho
skinparam nodesep 30
skinparam ranksep 18
skinparam backgroundColor transparent
skinparam ContainerFontSize 11
skinparam BoundaryFontSize 12

Person(менеджер, "Менеджер\nкомпании", "Back-office")

System_Ext(keycloak, "Keycloak (IdP)", "JWT клиентов\n(косвенно)")

Boundary(infra, "Инфраструктура") {
    Container(api_gw, "API Gateway", "Spring Cloud Gateway WebFlux", "AuthJwtFilter (внутр. JWT) только для /auth-service/**, /employee-service/**\nJwtFilter (Keycloak) для ОСТАЛЬНЫХ маршрутов\n⚠ НЕСООТВЕТСТВИЕ: административные маршруты (userinfo, management-pb и др.)\nидут через КЛИЕНТСКИЙ фильтр") #3CB371
}

System_Ext(client_part, "Клиентская часть\n(см. рис. 2)", "customer, account, trading,\ndocument, catalog —\nисточник данных")

Boundary(admin_part, "административная часть (модули для менеджеров)") {

    Boundary(mod_crm, "Модуль: CRM / Клиенты") {
        Container(userinfo_svc, "userinfo-service", "Spring Boot 3.5.0", "Back-office по клиентам: просмотр/редактирование,\nистория торгов, счета, экспорт PDF\n⚠ ДЫРА: НЕТ @PreAuthorize, идёт через JwtFilter (клиентский).\nСодержит чужую доменную логику (KYC, аудит)") #F4B400
    }

    Boundary(mod_comm, "Модуль: Коммуникации") {
        Container(chat_svc, "chat-service (планируется)", "Spring Boot", "Чат клиента с менеджером\n⚠ кандидат на вынос в общий сервис") #F4B400
    }

    Boundary(mod_support, "Модуль: Поддержка") {
        Container(support_svc, "support-service", "Spring Boot 3.5.6", "Тикеты, шаблоны\n⚠ создание заявок закомментировано (полумёртв)") #70AD47
    }

    Boundary(mod_hr, "Модуль: HR / Сотрудники") {
        Container(employee_svc, "employee-service", "Spring Boot 3.5.0", "Сотрудники, рабочие места, задачи, аудит\n⚠ содержит тикеты поддержки (чужой домен)") #70AD47
    }

    Boundary(mod_security, "Модуль: Безопасность (аутентификация менеджеров)") {
        Container(auth_svc, "auth-service", "Spring Boot 3.5.5", "Аутентификация менеджеров (JWT, OTP 2FA),\nроли, права, refresh, logout") #70AD47
    }

    Boundary(mod_education, "Модуль: Образование") {
        Container(education_svc, "education-service", "Spring Boot 3.5.0", "Каталог курсов (read-side для клиента)") #70AD47
        Container(test_svc, "test-service", "Spring Boot 3.5.0", "Квалификационные тесты") #70AD47
        Container(mgmt_edu, "management-service-pb\n(образование)", "Spring Boot 3.5.0", "CRUD курсов/тем/уроков/категорий\n@PreAuthorize: ADMIN/PRIVILEGED_EMPLOYEE/EMPLOYEE\n⚠ смешан с портфелями — долг") #70AD47
    }

    Boundary(mod_portfolio, "Модуль: Портфели (админ)") {
        Container(mgmt_pf, "management-service-pb\n(портфели)", "Spring Boot 3.5.0", "Готовые портфели: CRUD, комиссии, тейк-профит\n@PreAuthorize: TRADING_TP_EDIT\n⚠ смешан с образованием — долг") #70AD47
    }

    Boundary(mod_finance, "Модуль: Финансовая аналитика") {
        Container(financial_svc, "financialtransactions-service", "Spring Boot 3.5.0", "История транзакций клиента\n⚠ старый сервис, статус уточняется") #F4B400
        Container(tax_svc, "tax-service", "Spring Boot 3.5.0", "Расчёт НДФЛ (batch), 2-НДФЛ\n⚠ граница клиент/админ не определена") #F4B400
    }

    Boundary(mod_tariff, "Модуль: Тарифы / Услуги") {
        Container(customercare_svc, "customercare-service", "Spring Boot 3.5.0", "Подключение платных услуг, договор\n⚠ статус спорный, вызывает клиентские сервисы") #F4B400
    }
}

Rel(менеджер, api_gw, "HTTPS", "Back-office")
Rel(api_gw, userinfo_svc, "", "REST")
Rel(api_gw, support_svc, "", "REST")
Rel(api_gw, employee_svc, "", "REST")
Rel(api_gw, auth_svc, "", "REST")
Rel(api_gw, education_svc, "", "REST")
Rel(api_gw, test_svc, "", "REST")
Rel(api_gw, mgmt_edu, "", "REST")
Rel(api_gw, mgmt_pf, "", "REST")
Rel(api_gw, financial_svc, "", "REST")
Rel(api_gw, tax_svc, "", "REST")
Rel(api_gw, customercare_svc, "", "REST")

Rel(auth_svc, employee_svc, "register-account", "Kafka")
Rel(employee_svc, userinfo_svc, "register-result", "Kafka")

Rel(userinfo_svc, client_part, "getCustomerInfo, blockClient", "Feign")
Rel(userinfo_svc, client_part, "getAccounts, getOrders", "Feign/Kafka")
Rel(mgmt_pf, client_part, "changePortfolio, getAllPortfolios", "Feign")
Rel(mgmt_pf, financial_svc, "getTransactionsByCustomerId", "Feign")
Rel(financial_svc, client_part, "getTransactions", "Feign")
Rel(tax_svc, client_part, "taxWithdraw", "Feign")
Rel(customercare_svc, client_part, "getCustomer, getBrokerAccounts, generateDocument", "Feign")

Rel(менеджер, chat_svc, "WebSocket", "Чат с клиентом")

legend right
  |= Цвет |= Значение |
  |<back:#70AD47>   </back>| административный сервис |
  |<back:#3CB371>   </back>| Общая точка входа (Gateway) |
  |<back:#F4B400>   </back>| Проблема: долг / дыра / нет авторизации |
endlegend

@enduml
```

| Модуль | Контейнеры | Ответственность |
|---|---|---|
| CRM / Клиенты | userinfo-service | Back-office по клиентам, история торгов, экспорт PDF, KYC, аудит |
| Коммуникации | chat-service (планируется) | Чат клиента с менеджером |
| Поддержка | support-service | Тикеты, шаблоны ответов |
| HR / Сотрудники | employee-service | Сотрудники, рабочие места, задачи, аудит |
| Безопасность | auth-service | Аутентификация менеджеров, JWT, OTP 2FA, роли и права, refresh, logout |
| Образование | education-service, test-service, management-service-pb (образование) | Каталог курсов, квалификационные тесты, CRUD учебного контента |
| Портфели | management-service-pb (портфели) | Готовые портфели, комиссии, тейк-профит, торговые статусы |
| Финансовая аналитика | financialtransactions-service, tax-service | История транзакций, расчёт НДФЛ, 2-НДФЛ |
| Тарифы / Услуги | customercare-service | Подключение платных услуг, договоры |

Регистрация менеджера выполняется асинхронно через топики Kafka: `auth-service` публикует событие `register-account`, обрабатываемое `employee-service`, который далее инициирует событие `register-result` в `userinfo-service`.

*Примечание: наличие консьюмера `register-result` в `userinfo-service` требует сверки с прод-стендом (в локальном репозитории не подтверждается).*

## 3. Открытые вопросы

Текущее as-is отнесение сервисов к клиентской или административной части зафиксировано в §2 по факту и требованиям (см. `minutes-full.md`, таблицу состава сервисов). Финальные решения по перечисленным ниже пунктам на встрече 14.07.2026 не приняты и по решению №6 протокола зафиксированы как долги для отдельного обсуждения.

1. **`trading-service`** — as-is отнесён к клиентской части (по требованиям, решение №2 протокола; физически остаётся в `backend/`). Открыто: входит ли физическое перемещение репозитория в scope.
2. **`customercare-service`** — as-is отнесён к административной части (модуль «Тарифы / Услуги»). Открыто: остаётся в админке, удаляется или становится общим сервисом.
3. **`financialtransactions-service`** — as-is отнесён к административной части (модуль «Финансовая аналитика»), помечен как старый. Открыто: технический долг или кандидат на удаление; кто реально использует по требованиям.
4. **`tax-service`** — as-is отнесён к административной части (модуль «Финансовая аналитика»). Открыто: граница клиент/админ — клиентская (2-НДФЛ для клиента) или административная (расчёт для отчётности).
5. **`education-service`** — as-is отнесён к административной части (модуль «Образование»). Открыто: есть ли разделение на read-сторону (клиент) и write-сторону (менеджер).
6. **Чат клиента с менеджером** — as-is отнесён к административной части (модуль «Коммуникации», пометка «планируется»). Открыто: подтверждаем вынос в общий сервис; сроки.
7. **Фронтенд административной части** — в §2 не описан. Открыто: входит ли в scope архитектурного описания, или рассматривается только бэкенд.
