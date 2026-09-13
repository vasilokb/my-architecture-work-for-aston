# Микросервисы или распределённый монолит? Аудит архитектуры

**Дата:** 2026-05-24  
**Вердикт:** **Распределённый монолит (microlith)**

---

## Содержание

1. [Вердикт](#1-вердикт)
2. [Критерии оценки](#2-критерии)
3. [Автономность сервисов](#3-автономность)
4. [Связанность через данные](#4-данные)
5. [Связанность через код (shared libs)](#5-код)
6. [Связанность через вызовы (temporal coupling)](#6-вызовы)
7. [Связанность через события (Kafka)](#7-kafka)
8. [Инфраструктурная зрелость](#8-инфраструктура)
9. [Итоговая таблица](#9-scorecard)

---

## 1. Вердикт <a name="1-вердикт"></a>

Проект Liberty Investment **не является микросервисной архитектурой**. По совокупности признаков это **распределённый монолит (microlith)** — система, которая выглядит как микросервисы (23 независимых процесса, REST + Kafka), но лишена их главных преимуществ: автономности, отказоустойчивости и независимого развёртывания.

### Чего нет (критерии микросервисов):

| Критерий | Статус |
|---|---|
| Service Discovery | **Нет** — hardcoded URL |
| Circuit Breaker на межсервисных вызовах | **65% без защиты** |
| Database-per-service (строго) | **Нарушено** — 2 сервисы делят БД |
| Async communication (преимущественно) | **Нет** — 20 Feign vs 25 Kafka listeners |
| Graceful degradation | **Нет** — каскадные сбои |
| Independent deployment | **Нет** — порядок деплоя имеет значение |
| Auto-scaling | **Нет** — все 1 replica, нет HPA |
| Health probes | **Нет** — K8s не управляет lifecycle |

### Что есть (признаки монолита):

| Признак | Пример |
|---|---|
| Общие DTO между сервисами | `interservice-interaction-dto-lib` → 8 сервисов |
| Кольцевые зависимости | account-service ↔ document-service |
| Синхронные цепочки 4 хопа | trading → catalog → account → document → tax |
| Shared database | account-service + account-service-test = одна БД |
| Hub-сервисы (SPOF) | account-service, customer-service — по 6 вызывающих |
| Outbox отключён | События не публикуются — данные не расходятся |
| Одинаковые версии Spring Boot | Единый стек = признак единого деплоя |

---

## 2. Критерии оценки <a name="2-критерии"></a>

Оценка проведена по 6 осям, каждая из которых отражает уровень «микросервисности»:

| Ось | Вес | Измеряет |
|---|---|---|
| **Автономность** | 20% | Могут ли сервисы разрабатываться, развёртываться и масштабироваться независимо? |
| **Связанность через данные** | 20% | Разделяют ли сервисы базы данных? Есть ли database-per-service? |
| **Связанность через код** | 15% | Есть ли общие библиотеки с бизнес-логикой/DTO, создающие скрытую связь? |
| **Связанность через вызовы** | 20% | Насколько глубоки синхронные цепочки? Есть ли кольцевые зависимости? |
| **Связанность через события** | 15% | Надёжна ли асинхронная коммуникация? Есть ли retry, DLT, outbox? |
| **Инфраструктурная зрелость** | 10% | Есть ли Service Discovery, health probes, resource limits, auto-scaling? |

---

## 3. Автономность сервисов <a name="3-автономность"></a>

### 3.1. Независимое развёртывание

**Не обеспечено.** Порядок запуска сервисов имеет значение:

```
1. PostgreSQL, Kafka, Redis, Keycloak   ← инфраструктура
2. customer-service                      ← leaf, нет исходящих
3. account-service                       ← зависит от customer-service, document-service
4. catalog-service                       ← зависит от account-service
5. trading-service                       ← зависит от catalog-service, account-service
6. emulator-service                      ← зависит от Kafka (trading → emulator)
7. document-service                      ← зависит от account-service, customer-service, tax-service
8. management-service-pb                 ← зависит от financialtransactions, catalog
9. ...остальные                          ← можно в любом порядке
```

Если `account-service` не запущен — **6 сервисов** не могут корректно обработать запросы. Это не независимое развёртывание, а **скрытая зависимость запуска**.

### 3.2. Независимое масштабирование

**Не обеспечено.** Все сервисы работают с `replicaCount: 1`. HPA отсутствует. При увеличении нагрузки на trading-service его нельзя масштабировать независимо — нет resource limits, нет metrics, нет HPA.

### 3.3. Независимая разработка

**Частично.** Сервисы в разных Git-репозиториях, но:
- `interservice-interaction-dto-lib` — общая библиотека DTO для 8 сервисов. Изменение контракта одного сервиса требует перезапуска Nexus + обновления зависимостей во всех потребителях.
- 12 из 12 DDD-доменов пересекают границу `client/backend/` ↔ `backend/`. Команда, разрабатывающая домен «Торговля», вынуждена работать в двух репозиториях одновременно.

### 3.4. Оценка автономности: **3/10**

---

## 4. Связанность через данные <a name="4-данные"></a>

### 4.1. Database-per-service: нарушено

Принцип «каждый сервис владеет своей базой данных» нарушён в двух местах:

#### Нарушение #1: account-service + account-service-test = общая БД

```
account-service      → jdbc:postgresql://172.17.1.26:31421/account_service_db
account-service-test → jdbc:postgresql://172.17.1.26:31421/account_service_db
```

Два независимых сервиса читают и пишут в **одну и ту же базу данных**. Schema shared, data shared.

#### Нарушение #2: criticalfeedbackchannel → financialtransactions DB (misconfiguration)

Из-за copy-paste конфигурации (`application.yaml` от financialtransactions-service), `criticalfeedbackchannel` подключается к `release_financialtransactions_service_db` вместо своей собственной БД.

### 4.2. Shared PostgreSQL instances

Все сервисы группы используют один PostgreSQL-инстанс:

| Инстанс | Кол-во БД | Сервисов |
|---|---|---|
| `172.17.1.26:31421` | 5 | account, customer, catalog, emulator, notification |
| `postgres.dev:5432` | 3 | management, userinfo, financialtransactions |

Это **инфраструктурная связанность** — при падении инстанса PostgreSQL падают все 5 (или 3) сервисов одновременно. Database-per-service на уровне схемы, но не на уровне infrastructure.

### 4.3. Shared Redis

OTP-коды (`otp-service`) и кэш (`customer-service`) оба используют Redis DB 6 — потенциальный конфликт при росте нагрузки.

### 4.4. Оценка: **5/10**

Database-per-service соблюдается на уровне **имён баз данных и схем** — каждый сервис работает со своей схемой данных, нет общих таблиц. Это лучше, чем прямой shared schema. Однако:
- **Практическое нарушение:** `account-service-test` делит БД с `account-service` (shared data)
- **Инфраструктурная связанность:** shared PostgreSQL instances (5 и 3 сервисов на одном хосте) — при падении хоста падает группа сервисов
- Оценка повышена до 5/10 (было 4/10), т.к. нарушение database-per-service точечное, а не системное

---

## 5. Связанность через код (shared libs) <a name="5-код"></a>

### 5.1. `interservice-interaction-dto-lib` — главная проблема

Библиотека содержит **все DTO всех сервисов** в одном артефакте:

```
ru.aston.interserviceinteractiondtolib.
├── accountservice.dto.response    → 9 DTO
├── customerservice.dto.response   → 3 DTO
├── customerservice.dto.request    → 1 DTO
├── documentservice.dto.request    → 1 DTO
├── notificationservice.dto.kafka  → 1 DTO
├── catalogservice.*               → N DTO
└── enums                          → 2 enum
```

**Потребители:** 8 сервисов, версии 0.0.3, 0.0.3a, 0.0.3f.

**Проблема:** Изменение контракта `account-service` (например, добавление поля в `BrokerAccountResponse`) требует:
1. Обновить `interservice-interaction-dto-lib` (опубликовать в Nexus)
2. Обновить версию в `build.gradle` у **всех 8 потребителей**
3. Пересобрать и передеплоить **все 8 сервисов**

Это классический признак **распределённого монолита** — shared DTO library создаёт связанность на уровне компиляции, как если бы сервисы были модулями одного приложения.

### 5.2. `globalexceptionhandler-starter` — фрагментация

9 потребителей, **4 разные версии**: 0.0.5, 0.0.5b, 0.0.5c, 0.0.5db. Это указывает на то, что библиотека часто меняется с нарушением обратной совместимости — каждый патч-релиз ломает потребителей.

### 5.3. Shared starters

| Библиотека | Потребителей | Риск |
|---|---|---|
| `interservice-interaction-dto-lib` | 8 | HIGH — контракты всех сервисов в одном месте |
| `globalexceptionhandler-starter` | 9 | MEDIUM — фрагментация версий |
| `logger-starter` | 7 | LOW — инфраструктурный, без бизнес-логики |
| `otphandler-starter` | 2 | LOW — узкоспециализированный |

### 5.4. Оценка: **3/10**

Shared DTO library — это прямое нарушение принципа автономности микросервисов. Правильный подход: каждый сервис владеет своими DTO, потребители генерируют свои модели из OpenAPI-контракта или дублируют нужные им поля.

---

## 6. Связанность через вызовы (temporal coupling) <a name="6-вызовы"></a>

### 6.1. Синхронные цепочки

Система содержит **20 Feign-клиентов** для синхронных REST-вызовов. Это создаёт **temporal coupling** — вызывающий сервис блокируется до ответа downstream.

Самые длинные цепочки — **4 синхронных хопа**:

```
trading-service → catalog-service → account-service → document-service → tax-service
                  (4 network hops, ~200ms+ latency при нормальной работе,
                   секунды при degradation)
```

В микросервисной архитектуре синхронные цепочки длиннее 2 хопов считаются анти-паттерном. Здесь 4 хопа — через критический бизнес-процесс.

### 6.2. Кольцевые зависимости

Обнаружены **3 кольцевые зависимости**:

```
ЦИКЛ 1:  account-service ←→ document-service         (прямой)
ЦИКЛ 2:  account-service → document-service → tax-service → account-service
ЦИКЛ 3:  (тот же цикл 2, вход через tax-service)
```

**Цикл 1** особенно опасен: `account-service` вызывает `document-service` для генерации документов при открытии/закрытии счёта, а `document-service` вызывает `account-service` для проверки доступа к брокерскому счёту. При насыщении thread pools оба сервиса заблокируют друг друга (distributed deadlock).

### 6.3. Hub-сервисы (SPOF)

| Сервис | Кол-во вызывающих | Роль |
|---|---|---|
| **account-service** | 6 | Единая точка отказа для торгов, каталога, документов, налогов, тарифов |
| **customer-service** | 6 | Единая точка отказа для аккаунтов, OTP, уведомлений, документов |

Падение `account-service` выводит из строя:
- trading-service (не может проверить счёт)
- catalog-service (не может получить активы)
- document-service (не может проверить доступ)
- tax-service (не может рассчитать налоги)
- customercare-service (не может подключить услугу)
- financialtransactions-service (не может записать транзакцию)

Это **6 из 23 сервисов** — более четверти системы — полностью зависят от одного сервиса.

### 6.4. Resilience: 65% без защиты

| Уровень защиты | Кол-во | Процент |
|---|---|---|
| Полная (Resilience4j) | 1 | 5% |
| Circuit Breaker (wrapper) | 6 | 30% |
| **Без защиты** | **13** | **65%** |

13 Feign-клиентов НЕ имеют circuit breaker. При недоступности downstream-сервиса:
- вызывающий сервис **блокирует thread pool** на timeout (default: 60s)
- при множественных запросах — **exhaustion thread pool** → сервис становится недоступным
- **каскадный сбой** распространяется вверх по цепочке вызовов

**Дополнительно:**
- **Idempotency keys** — отсутствуют. Повторный запрос (например, при network timeout + retry) может создать дублирующую запись (повторный ордер, повторную транзакцию). API Gateway передаёт заголовок `idempotency_key` (видно в CORS-конфигурации), но сервисы его **не обрабатывают**.
- **Client-side retry** — `management-service-pb` явно устанавливает `Retryer.NEVER_RETRY`, остальные сервисы используют Feign default (no retry). Ни один сервис не реализует осознанную retry-политику с exponential backoff.

### 6.5. Визуализация связанности

*(Кольцевые зависимости описаны в п.6.2 — здесь показана общая карта)*

```
  management-service-pb ──┬──→ financialtransactions-service ──→ account-service* ──→ document-service*
                          └──→ catalog-service ──→ account-service*
                                                       ↑              ↓
  trading-service ───────→ catalog-service ──→ account-service*  document-service* ──→ tax-service ──→ account-service*
                          └──→ account-service*                         ↓
                                                              customer-service*
                                                       ↑              ↑
  customercare-service ──→ document-service* ──→ customer-service* ←──┘
                       └──→ customer-service*       ↑
                       └──→ account-service*     notification-service
                                                  otp-service
                                                  account-service-test

  * = SPOF (3+ вызывающих)
  → = синхронный Feign-вызов без circuit breaker
```

### 6.6. Оценка: **2/10**

Длинные синхронные цепочки, кольцевые зависимости, hub-сервисы как SPOF, отсутствие circuit breaker — это не микросервисы, а распределённый монолит с сетевой связанностью.

---

## 7. Связанность через события (Kafka) <a name="7-kafka"></a>

### 7.1. Отключённый Outbox (CRITICAL)

В `trading-service` метод `sendStatusChangeNotificationBatch()` содержит **закомментированный** вызов:

```java
@Scheduled(fixedRate = 5000)
public void sendStatusChangeNotificationBatch() {
    List<OutboxMessage> messages = outboxRepository.findBySentFalse();
    if (!messages.isEmpty()) {
        // sendBatchMessages(messages);  ← ЗАКОММЕНТИРОВАНО
    }
}
```

**Последствия:**
- События изменения статуса ордеров (`executed`, `rejected`, `expired`, `cancelled`) **никогда не публикуются**
- `account-service` не узнаёт об исполнении ордеров через Kafka
- Вместо этого он полагается на **синхронные вызовы** (temporal coupling)

Это делает **ключевой механизм асинхронной коммуникации сломанным** — события изменения статуса ордеров не расходятся, синхронизация происходит через REST. Kafka по-прежнему используется для `order_request` / `order_status` между trading и emulator, но **критические бизнес-события** (исполнение, отклонение, отмена ордеров) не доходят до account-service.

### 7.2. Kafka без retry/DLT

Из 25 `@KafkaListener`-методов:

| Защита | Кол-во | Сервисы |
|---|---|---|
| @RetryableTopic + DLT + backoff | **1** | notification-service (эталон) |
| DLT без retry (attempts=1) | **3** | emulator-service |
| **Без защиты** | **21** | trading, account, customer, support, userinfo, account-test |

**21 из 25 listeners** не имеют retry или DLT. При исключении в обработчике:
- Если `enable.auto.commit = true` (по умолчанию) — **сообщение теряется**
- Если `enable.auto.commit = false` — consumer **зависает** на этом сообщении навсегда

### 7.3. Двойная коммуникация

Торговый конвейер использует **обе модели** для одной и той же цели:

```
Синхронная (Feign):
  trading-service → (REST) → catalog-service → (REST) → account-service

Асинхронная (Kafka, отключена):
  trading-service → [order_request] → emulator-service → [order_status] → trading-service
  trading-service → [order_executed] → account-service (Outbox закомментирован!)
```

Вместо того чтобы Kafka была основным каналом (как в микросервисах), система дублирует синхронные вызовы поверх асинхронных событий. Это не Event-Driven Architecture, а **заплатка**.

### 7.4. Оценка: **2/10**

Kafka не выполняет свою роль децентрализующего механизма. Outbox отключён, retry нет, DLT нет. Асинхронная коммуникация номинальная.

---

## 8. Инфраструктурная зрелость <a name="8-инфраструктура"></a>

### 8.1. Service Discovery

**Клиент-сторонний Service Discovery отсутствует.** 8 сервисов имеют зависимость `spring-cloud-starter-netflix-eureka-client` в build.gradle, но **ни один не настроен** — Eureka server не развёрнут.

Kubernetes предоставляет **DNS-based service discovery** (имена сервисов типа `account-service.default.svc.cluster.local`), и часть конфигураций использует имена K8s-сервисов вместо IP-адресов. Однако это не осознанный выбор, а побочный эффект — многие конфигурации содержат **hardcoded IP + NodePort** (`172.17.1.26:31421`), а не DNS-имена. При horizontal scaling новые инстансы невидимы, load balancing на уровне сервиса не работает.

**Уточнение:** проблема не в отсутствии discovery как такового (K8s DNS работает), а в том, что приложение его **не использует осознанно** — URL зашиты в `application.yaml`, нет client-side load balancing.

### 8.2. Kubernetes: deploy mechanism, не platform

Kubernetes используется как **механизм развёртывания** (запустить Pod), а не как платформа оркестрации:

| Возможность K8s | Статус | Значение |
|---|---|---|
| Health probes (liveness/readiness) | **Нет** | K8s не перезапускает зависшие Pod'ы |
| Resource limits | **Нет** | Нет защиты от OOM, нет HPA |
| HPA (auto-scaling) | **Нет** | Ручное масштабирование |
| Network Policies | **Нет** | Любой Pod может обратиться к любому |
| PodDisruptionBudget | **Нет** | Нет гарантии доступности при maintenance |
| Service type | **NodePort** | Не для production |

По сути Kubernetes работает как **Docker Compose с ручным управлением** — Pod'ы запускаются, но платформа не управляет их жизненным циклом.

### 8.3. Docker: insecure defaults

26 контейнеров, все с небезопасными настройками по умолчанию:
- Все работают от **root** (нет `USER` директивы)
- Нет **HEALTHCHECK** — Docker не знает, жив ли контейнер
- Нет **multi-stage builds** — JDK вместо JRE, лишние слои
- Базовый образ ~450 MB вместо ~200 MB (JRE)

### 8.4. Оценка: **2/10**

Инфраструктура не обеспечивает ни одну из capabilities, необходимых микросервисам: discovery, orchestration, self-healing, auto-scaling.

---

## 9. Итоговая таблица <a name="9-scorecard"></a>

> **Методологическое ограничение:** данный аудит основан на **статическом анализе кода и конфигураций**. Мы не располагаем данными о реальных инцидентах (каскадных отказах, потере сообщений, недоступности сервисов в продакшене). Приведённые риски — оценка по архитектурным признакам, а не по историческим данным мониторинга.

### 9.1. Оценка по осям

| Ось | Вес | Оценка | Взвешенная | Ключевой аргумент |
|---|---|---|---|---|
| Автономность | 20% | 3/10 | 0.6 | Порядок запуска имеет значение, shared DTO |
| Связанность через данные | 20% | 5/10 | 1.0 | Shared DB (account-test), shared PostgreSQL instances, но schema-level разделение соблюдается |
| Связанность через код | 15% | 3/10 | 0.45 | `interservice-interaction-dto-lib` = все DTO в одном месте |
| Связанность через вызовы | 20% | 2/10 | 0.4 | 4-hop chains, циклы, 2 SPOF, 65% без CB |
| Связанность через события | 15% | 2/10 | 0.3 | Outbox отключён, 21/25 без retry/DLT |
| Инфраструктура | 10% | 2/10 | 0.2 | Нет SD, нет probes, нет limits, нет HPA |
| **Итого** | **100%** | | **2.95/10** | |

### 9.2. Сравнительная таблица

| Характеристика | Монолит | Распределённый монолит | Микросервисы | **Liberty Investment** |
|---|---|---|---|---|
| Один процесс | ✅ | ❌ | ❌ | ❌ |
| Множество процессов | ❌ | ✅ | ✅ | ✅ (23) |
| Network communication | ❌ | ✅ | ✅ | ✅ (REST + Kafka) |
| Independent deployment | ✅ | ❌ | ✅ | ❌ (порядок важен) |
| Database per service | — | ❌ | ✅ | ❌ (shared DB) |
| Service Discovery | — | ❌ | ✅ | ❌ |
| Circuit Breaker | — | ❌ | ✅ | ❌ (65% без) |
| Async-first | ❌ | ❌ | ✅ | ❌ (sync chains) |
| Graceful degradation | ❌ | ❌ | ✅ | ❌ (cascading) |
| Auto-scaling | ❌ | ❌ | ✅ | ❌ |
| Shared code/libraries | ✅ | ✅ | ❌ | ✅ (shared DTO) |
| Circular dependencies | ✅ | ✅ | ❌ | ✅ (3 цикла) |

**Liberty Investment попадает в колонку «Распределённый монолит» по всем критериям.**

### 9.3. Почему это плохо

Распределённый монолит сочетает **недостатки обоих подходов**:

| Проблема монолита | Проблема микросервисов | Итого |
|---|---|---|
| Единая точка отказа | + Сетевая задержка | Медленный + ненадёжный |
| Каскадные сбои | + Распределённая отладка | Сложно найти причину |
| Общая модель данных | + Distributed transactions | Несогласованность данных |
| Медленный деплой | + Координация 23 сервисов | Медленный + сложный деплой |
| Shared code | + Network overhead | Связанность + latency |

### 9.4. Roadmap: от microlith к микросервисам

#### Фаза 1 (1-2 месяца): Стабилизация

| # | Действие | Цель |
|---|---|---|
| 1 | Раскомментировать `sendBatchMessages()` в trading-service | Восстановить Outbox |
| 2 | Добавить Circuit Breaker ко всем Feign-клиентам | Предотвратить каскадные сбои |
| 3 | Добавить @RetryableTopic + DLT ко всем Kafka listeners | Предотвратить потерю сообщений |
| 4 | Добавить health probes + resource limits в Helm | K8s platform basics |

#### Фаза 2 (2-4 месяца): Развязка

| # | Действие | Цель |
|---|---|---|
| 5 | Разорвать кольцевую зависимость account ↔ document | Один вызов заменить на Kafka event |
| 6 | Убрать `interservice-interaction-dto-lib`, перейти на OpenAPI codegen | Автономные контракты |
| 7 | Внедрить Service Discovery (Spring Cloud Kubernetes) | Динамическая маршрутизация |
| 8 | Разделить общие PostgreSQL instances | Infrastructure isolation |

#### Фаза 3 (4-6 месяцев): Зрелость

| # | Действие | Цель |
|---|---|---|
| 9 | Перевести trading pipeline на async-first | Eliminate 4-hop sync chains |
| 10 | Настроить HPA для критичных сервисов | Auto-scaling |
| 11 | Внедрить distributed tracing (Zipkin → Grafana Tempo) | Observability |
| 12 | Network Policies + PodSecurityPolicies | Security in depth |
