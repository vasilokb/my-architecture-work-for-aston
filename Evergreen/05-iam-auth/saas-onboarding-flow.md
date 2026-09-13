Вот финальная версия документа. В **Шаг 4** добавлен развернутый пример структуры настроечного бандла (data.json), входного контекста (input.json) и универсальной политики OPA (authz.rego), демонстрирующий изоляцию тенантов и разделение основных и дополнительных ролей.

---

## Регистрация на SAAS платформе новых сотрудников и ролей от тенанта

Один большой флоу целиком — от появления банка до рабочего дня сотрудника.

**Шаг 1. Регистрация банка**

Менеджер платформы через Admin UI нажимает "Подключить банк", пишет название и email владельца. Дальше система работает сама.

Admin Service получает команду и идёт в Keycloak через Keycloak Admin API. Это единственный способ что-то создать в Keycloak — прямая запись в его базу недопустима, так как ломает кэши.

Admin Service создаёт в Keycloak пользователя с этим email (Keycloak Admin API: POST /admin/realms/{realm}/users) и назначает ему глобальную realm-роль bank_admin (Keycloak Admin API: POST /admin/realms/{realm}/users/{user-id}/role-mappings/realm) — это одна из 5 базовых ролей платформы, которые общие для всех банков. Затем Admin Service инициирует в Keycloak триггер на смену пароля (Keycloak Admin API: PUT /admin/realms/{realm}/users/{user-id}/execute-actions-email с телом ["UPDATE_PASSWORD"]). Keycloak сам отправляет владельцу email со ссылкой (живет один час). Владелец переходит по ссылке и задаёт пароль. Пароли в открытом виде нигде не передаются и не логируются.

**Шаг 2. Как банк добавляет свои роли и привязывает их к методам**

Владелец банка в своём UI создаёт роль (например, senior_operator). Admin Service создаёт её как **client-роль**, привязанную строго к конкретному клиенту (банку) внутри Keycloak (Keycloak Admin API: POST /admin/realms/{realm}/clients/{client-uuid}/roles). Это обеспечивает изоляцию на уровне IAM — чужие client-роли банкам не видны.

Далее владелец отмечает галочками, какие методы АБС разрешены для senior_operator.
Admin Service сохраняет этот маппинг в свою выделенную реляционную БД **PostgreSQL** (схема/БД admin_db, SQL: INSERT/UPDATE в таблицу role_permissions).

> **Архитектурная изоляция таблицы role_permissions:**
> Эта таблица используется исключительно как *мастер-система для хранения конфигурации* (она просто фиксирует, какие именно галочки админ нажал в UI). База логически или физически отделена от бизнес-данных АБС.
> * **Кто использует эту таблицу:** Только сам Admin Service (чтобы считать настройки и отрисовать их в интерфейсе владельца банка) и **OPA Bundle Server** (чтобы выгрузить текущий слепок связей «роль-метод» и превратить его в плоский JSON).
> * **Кто в эту таблицу НИКОГДА не ходит:** Ни API Gateway (Kong), ни бэкенд АБС, ни сам движок OPA не делают никаких SQL-запросов к этой базе при обработке запросов пользователей. Это полностью исключает деградацию производительности БД при высокой операционной нагрузке.
> 
> 

Чтобы новые права применились без задержек (до 30-60 секунд), Admin Service синхронно вызывает внутренний API выделенного микросервиса — **OPA Bundle Server** (POST /internal/v1/bundle/trigger).

Получив этот синхронный сигнал, **OPA Bundle Server** запускает асинхронный процесс (воркер): выгребает актуальные связи из таблицы role_permissions в PostgreSQL, формирует из них файл data.json и пушит обновленный бандл напрямую в OPA (OPA REST API: PUT /v1/policies/bundle).

Если синхронный вызов от Admin Service до OPA Bundle Server не прошел (например, из-за временного сетевого сбоя), в качестве страховки (fallback) внутри **OPA Bundle Server** работает периодический cron-джоб, который раз в 5 минут самостоятельно инициирует пересборку и доставку бандла. Git для хранения динамических маппингов ролей не используется, что исключает мусорные авто-коммиты и конфликты слияния.

**Шаг 3. Как владелец банка добавляет сотрудников**

* **Ручной режим (по одному):** Владелец вводит email, ФИО и выбирает роль. Система создаёт пользователя (Keycloak Admin API: POST /admin/realms/{realm}/users), мапит выбранную роль и вызывает триггер отправки письма (Keycloak Admin API: PUT /admin/realms/{realm}/users/{user-id}/execute-actions-email). Keycloak шлет сотруднику письмо для установки пароля.
* **Bulk-режим (списком):** Владелец загружает CSV-файл. UI отправляет его в Admin Service (REST API: POST /api/v1/employees/import), который мгновенно отвечает 202 Accepted и возвращает task_id. Далее работает фоновый воркер: он читает строки и по одной вызывает Keycloak Admin API в рамках асинхронной джобы.

**Идемпотентность и обработка ошибок:** Обработка CSV не требует распределенных транзакций. Если строка содержит ошибку (например, дубликат email), воркер фиксирует её статус и **продолжает работу**. Успешно созданные учётки начинают работать сразу. Владелец видит по task_id отчёт (REST API: GET /api/v1/employees/import/tasks/{task_id}): "создано 998, ошибок 2 (причины)".

**Шаг 4. Рабочий день сотрудника**

Сотрудник логинится через UI банка по OAuth 2.0 Authorization Code + PKCE. UI редиректит на Keycloak auth endpoint с `code_challenge`, сотрудник вводит логин/пароль В Keycloak, Keycloak редиректит обратно с `code`, UI обменивает `code` на токен (`POST /realms/abs/protocol/openid-connect/token` с `grant_type=authorization_code` и `code_verifier`). Keycloak выдаёт JWT (TTL 1 час) + `refresh_token`. JWT содержит: `sub` (id сотрудника), `tenant_id`, `realm_access.roles` (5 базовых), `resource_access.bank-007.roles` (client-роли банка). Пароль никогда не попадает в UI-клиент.

Каждый запрос к АБС проходит через API Gateway (Kong), который делает три вещи:

1. Проверяет подпись JWT математически, используя публичные ключи (Keycloak JWKS API: GET /realms/{realm}/protocol/openid-connect/certs).
2. **Проверяет Redis blacklist:** проверяет наличие ключей блокировки пользователя или тенанта (Redis API: EXISTS или MGET по ключам blacklist:user:{user_id} and blacklist:tenant:{tenant_id}).
3. Вызывает OPA, передавая контекст запроса (OPA Data API: `POST /v1/data/abs.rbac.authz/allow`).

OPA сверяет контекст со своим in-memory кэшем (тем самым data.json, который ему прислал OPA Bundle Server).

> ### Структурный пример конфигурации OPA (Конфиг и Логика)
> 
> 
> **1. Динамические данные в памяти OPA (data.json):**
> Формируется автоматически на основе таблицы role_permissions для всех тенантов. Показывает разделение на базовые (основные) и кастомные (дополнительные) роли.
> json
> {
>   "tenants": {
>     "bank-007": {
>       "name": "Альфа-Банк",
>       "status": "active",
>       "roles": {
>         "bank_admin": {
>           "description": "Основная роль: Администратор",
>           "allowed_methods": ["*"]
>         },
>         "senior_operator": {
>           "description": "Дополнительная роль: Старший операционист",
>           "allowed_methods": [
>             "GET /api/v1/clients/*",
>             "POST /api/v1/loans/approve"
>           ]
>         }
>       }
>     },
>     "bank-008": {
>       "name": "Омега-Банк",
>       "status": "blocked",
>       "roles": {
>         "auditor": {
>           "description": "Дополнительная роль: Аудитор",
>           "allowed_methods": ["GET /api/v1/reports/*"]
>         }
>       }
>     }
>   }
> }
> 
> 
> 
> 
> **2. Входной запрос от Kong (input.json):**
> Контекст, извлеченный из JWT токена сотрудника и HTTP-запроса.
> json
> {
>   "input": {
>     "tenant_id": "bank-007",
>     "roles": ["senior_operator"],
>     "method": "POST",
>     "path": "/api/v1/loans/approve"
>   }
> }
> 
> 
> 
> 
> **3. Универсальные правила авторизации (authz.rego в Git):**
> Статичный код политики, обрабатывающий входящий контекст на основе переданной даты.
> rego
> package abs.rbac.authz
> import future.keywords.in
> 
> default allow = false
> 
> # Проверка активности банка
> is_tenant_active {
>     data.tenants[input.tenant_id].status == "active"
> }
> 
> # Основное правило авторизации по массиву ролей
> allow {
>     is_tenant_active
>     some user_role in input.roles
>     allowed_endpoints := data.tenants[input.tenant_id].roles[user_role].allowed_methods
>     some endpoint in allowed_endpoints
>     match_endpoint(endpoint, input.method, input.path)
> }
> 
> match_endpoint(endpoint, _, _) { endpoint == "*" }
> match_endpoint(endpoint, method, path) { endpoint == sprintf("%s %s", [method, path]) }
> match_endpoint(endpoint, method, path) {
>     endswith(endpoint, "*")
>     prefix := trim_suffix(endpoint, "*")
>     startswith(sprintf("%s %s", [method, path]), prefix)
> }
> 
> 
> 
> 

Если OPA отвечает allow, Kong проксирует запрос в бэкенд АБС. Бэкенд считывает tenant_id из токена и применяет **RLS (Row-Level Security)** в своей бизнес-БД PostgreSQL (SQL: выполняется пре-хук SET LOCAL app.current_tenant = 'bank-007'). Даже при гипотетической ошибке OPA банк физически не сможет прочитать чужие данные из соседнего тенанта.

**Шаг 5. Изменения в процессе работы**

* **Сотрудник уволен:** Владелец нажимает "Уволить". Admin Service синхронно добавляет user_id в Redis стоп-лист (Redis API: SET blacklist:user:{user_id} true EX 3600) с **TTL записи равным 1 часу** (максимальное время жизни токена), чтобы ключ автоматически удалился и не забивал память RAM. Затем асинхронно выставляет флаг блокировки в профиле (Keycloak Admin API: PUT /admin/realms/{realm}/users/{user-id} с телом {"enabled": false}).
* **Сотрудник сменил роль:** Admin Service обновляет маппинг ролей пользователя (Keycloak Admin API: POST /admin/realms/{realm}/users/{user-id}/role-mappings/clients/{client-uuid} и DELETE для старой роли). Новый токен при авто-refresh подтянет обновленный массив ролей.
* **Появился новый метод АБС для существующих парадигм:** Разработчик выкатывает метод. Архитектору **не нужно править Rego**. Метод просто регистрируется в БД admin_db через миграцию или внутренний эндпоинт, становится доступен в UI для галочек и попадает в OPA через data.json.
* **Появилась принципиально новая парадигма (например, доступ по расписанию):** Только в этом случае архитектор правит .rego файлы в Git. CI собирает новый базовый bundle и деплоит его в OPA.

**Шаг 6. Смена статуса самого банка**

При блокировке банка менеджер меняет статус в Admin UI. Сценарий выполняется в две фазы:

1. **Синхронно:** Admin Service добавляет идентификатор тенанта в Redis стоп-лист **без TTL** (Redis API: SET blacklist:tenant:{tenant_id} true). С этой миллисекунды Kong на входе рубит любые запросы этого банка.
2. **Асинхронно:** Задача на полную блокировку сущностей отправляется в очередь сообщений (Broker API: BasicPublish в RabbitMQ/Kafka). Фоновый воркер вычитывает задачу и планомерно деактивирует клиентское приложение банка (Keycloak Admin API: PUT /admin/realms/{realm}/clients/{client-uuid} -> {"enabled": false}) и обходит пользователей. Использование гарантированной очереди с настроенными Retry и Dead Letter Queue (DLQ) обеспечивает **eventual consistency** даже в случае временной недоступности Keycloak на момент блокировки.

---

### Архитектурные Решения (ADR Summary)

* **Изоляция (Defense in Depth):** Реализована на 3 уровнях: client-роли (Keycloak), tenant-check + role mapping (OPA), RLS (PostgreSQL).
* **Разделение логики и данных авторизации:** Политики (Rego) живут в Git и меняются редко. Данные маппингов (JSON) живут в реляционной БД PostgreSQL (admin_db), управляются через UI и поставляются в OPA динамически в виде плоских кэшей через выделенный компонент **OPA Bundle Server**. При проверке прав онлайн-запросов к реляционной БД нет.
* **Управление секретами:** Платформа не генерирует и не хранит пароли в открытом виде. Используется нативный механизм Keycloak UPDATE_PASSWORD через отправку писем на почту сотрудников.
* **Отказоустойчивость массовых операций:** Все bulk-операции (импорт, блокировка тенанта) выполняются асинхронно через брокер с поддержкой DLQ и отслеживанием статуса по task_id.
* **Мгновенная инвалидация:** Реализована через паттерн API Gateway + Redis Blacklist. Очистка кэша Redis для учетных записей автоматизирована через TTL, равный времени жизни JWT. Блокировка тенантов персистентна.