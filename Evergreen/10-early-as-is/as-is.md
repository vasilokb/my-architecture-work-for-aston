@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

title Кредитование — упрощённая, но «приближённая к реальности» компонентная схема

skinparam componentStyle rectangle
skinparam shadowing false
LAYOUT_LEFT_RIGHT()

' ====== Акторы/каналы ======
Person(customer, "Клиент", "Подаёт заявку, подписывает, получает деньги, платит")
Person(agent, "Сотрудник фронт-линии", "Оформляет/помогает клиенту, сопровождает заявку")

System_Ext(bki, "БКИ", "История/скоринг-сигналы")
System_Ext(gov, "Госреестры/проверки", "Документы, ФИО, адрес, ограничения")
System_Ext(sign, "Провайдер ЭП", "Подписание договора")
System_Ext(paynet, "Платёжная инфраструктура", "Переводы, погашения, автоплатежи")
System_Ext(notify, "Уведомления", "SMS/Push/Email")

System_Boundary(bank, "Банк: платформа кредитования") {

' ====== Периметр/доступ ======
Container_Boundary(edge, "Каналы и периметр") {
Component(mobile, "Мобильный банк", "UI", "Заявка/статусы/подписание/платежи")
Component(web, "Интернет-банк", "UI", "Заявка/статусы/подписание/платежи")
Component(fo, "Рабочее место фронт-линии", "UI", "Оформление/проверки/статусы")
Component(apigw, "API Gateway", "HTTP", "Единая точка входа, маршрутизация")
Component(pep, "PEP (Policy Enforcement Point)", "Security", "Проверка доступа/политик на входе")
}

' ====== Оркестрация кредитного потока ======
Container_Boundary(flow, "Кредитный поток (оркестрация)") {
Component(bpm, "Оркестратор процесса (BPM/Workflow)", "Workflow", "Шаги процесса, таймауты, ретраи, ручные задачи")
Component(case, "Case/Task Management", "Case", "Очереди задач для подразделений, статусы, SLA")
Component(audit, "Журнал аудита решений", "Audit", "Кто/что/когда решил, основания и артефакты")
}

' ====== Доменные сервисы кредитования ======
Container_Boundary(domain, "Доменные сервисы кредитования") {
Component(app, "Сервис заявки", "Service", "Заявка, статусы, версия анкеты, вложения")
Component(profile, "Профиль клиента", "Service", "Персональные данные, контакты, согласия")
Component(product, "Каталог кредитных продуктов", "Service", "Правила продукта, ограничения, параметры офферов")
Component(offer, "Генератор оффера", "Service", "Калькуляция условий, несколько офферов, персонализация")
Component(decision, "Decision Engine", "Service", "Агрегация сигналов и вынесение решения")
Component(scoring, "Скоринг/модели", "ML/Rules", "Скоринговые модели, фичи, пороги")
Component(kyc, "KYC/AML проверки", "Service", "Идентификация, санкции, подозрительность, лимиты")
Component(fraud, "Антифрод проверки", "Service", "Риск мошенничества по заявке/каналу/устройству")
Component(doc, "Документы и договор", "Service", "Генерация договоров, пакеты документов, печатные формы")
Component(contract, "Сервис договора", "Service", "Открытие договора, график, параметры, жизненный цикл")
Component(disb, "Выдача кредита", "Service", "Поручение на выдачу, контроль условий, подтверждения")
Component(repay, "Погашение", "Service", "Начисления, платежи, автосписания, распределение по долгам")
Component(coll, "Просрочка/взыскание", "Service", "Триггеры просрочки, стратегии, коммуникации")
}

' ====== Данные и инфраструктура интеграций ======
Container_Boundary(infra, "Интеграция и данные") {
Component(kafka, "Шина событий (Kafka)", "Messaging", "События домена и интеграционные события")
Component(esb, "ESB/Integration Layer", "Integration", "Синхронные интеграции, трансформации, маршрутизация")
Component(dwh, "Хранилище/витрины", "DWH", "Отчётность, риск-аналитика, контроль качества данных")
Component(obs, "Наблюдаемость", "Logs/Metrics/Traces", "Трассировка потока заявки, алерты, SLO")
}

' ====== Core/учёт/бэк-офис ======
Container_Boundary(core, "Учёт и бэк-офис") {
Component(corebank, "Core Banking/АБС", "Core", "Счета, проводки, остатки, начисления, операции")
Component(gl, "Главная книга/учёт", "Accounting", "Проводки/баланс, закрытия, контроллинг")
Component(dms, "Архив/ECM", "DMS", "Хранение подписанных документов и приложений")
}
}

' ====== Связи каналов и периметра ======
Rel(customer, mobile, "Подаёт заявку / подписывает / платит")
Rel(customer, web, "Подаёт заявку / подписывает / платит")
Rel(agent, fo, "Оформляет и сопровождает заявку")

Rel(mobile, apigw, "HTTP")
Rel(web, apigw, "HTTP")
Rel(fo, apigw, "HTTP")
Rel(apigw, pep, "Контроль доступа")
Rel(pep, bpm, "Запуск/продолжение процесса", "HTTP")

' ====== Оркестрация ↔ доменные сервисы ======
Rel(bpm, app, "Создать/обновить заявку, статус", "HTTP")
Rel(bpm, profile, "Чтение/обновление данных клиента", "HTTP")
Rel(bpm, kyc, "Запрос проверок KYC/AML", "HTTP")
Rel(bpm, fraud, "Запрос антифрода", "HTTP")
Rel(bpm, offer, "Сформировать офферы", "HTTP")
Rel(bpm, decision, "Запрос решения", "HTTP")
Rel(bpm, doc, "Сформировать документы", "HTTP")
Rel(bpm, contract, "Открыть договор", "HTTP")
Rel(bpm, disb, "Инициировать выдачу", "HTTP")
Rel(bpm, repay, "Запросить состояние погашений/графика", "HTTP")
Rel(bpm, case, "Поставить/снять задачу подразделению", "HTTP")
Rel(bpm, audit, "Записать шаг/решение/основание", "Event/HTTP")

' ====== Decision/Scoring: реальная «начинка» ======
Rel(decision, scoring, "Запрос скоринга/фичей", "HTTP")
Rel(decision, kyc, "Учитывает результаты проверок", "Event/HTTP")
Rel(decision, fraud, "Учитывает антифрод-сигналы", "Event/HTTP")

Rel(scoring, bki, "Кредитная история/атрибуты", "API")
Rel(kyc, gov, "Проверки по реестрам", "API")

' ====== Документы/подписание/архив ======
Rel(doc, sign, "Подписание", "API")
Rel(doc, dms, "Архивирование пакета", "API")
Rel(doc, app, "Связь документов с заявкой", "HTTP")

' ====== Договор/учёт/выдача/погашение ======
Rel(contract, corebank, "Открытие договора/график/параметры", "API")
Rel(disb, corebank, "Поручение на выдачу", "API")
Rel(repay, corebank, "Начисления/платежи/остатки", "API")
Rel(repay, paynet, "Приём платежей/автоплатежи", "API")
Rel(coll, repay, "Состояние просрочки/платежей", "Event/HTTP")

' ====== События и интеграция (как в жизни: гибрид sync+async) ======
Rel(app, kafka, "Публикация событий заявки", "Event")
Rel(profile, kafka, "События профиля/согласий", "Event")
Rel(kyc, kafka, "События результатов проверок", "Event")
Rel(fraud, kafka, "Антифрод-события", "Event")
Rel(decision, kafka, "События решения", "Event")
Rel(contract, kafka, "События договора/графика", "Event")
Rel(repay, kafka, "События платежей/начислений", "Event")

Rel(esb, corebank, "Интеграция со счетами/проводками", "API")
Rel(esb, notify, "Отправка уведомлений", "API")
Rel(kafka, dwh, "Загрузка событий/витрины", "ETL/Streaming")

' ====== Наблюдаемость ======
Rel(apigw, obs, "Метрики/логи/трейсы", "OTel/Logs")
Rel(bpm, obs, "Трейсы процесса/тайминги шагов", "OTel")
Rel(decision, obs, "Метрики качества/времени решения", "Metrics")
Rel(corebank, obs, "Тех. метрики/инциденты", "Metrics/Logs")

@enduml
