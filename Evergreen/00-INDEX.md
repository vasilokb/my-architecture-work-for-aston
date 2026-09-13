# Индекс артефактов — проект «Эвергрин × АБС»

Копия рабочих артефактов архитектора (Василий, `v4sil-burkin`) из `D:\Астон\evergreen`.
Назначение: разбор утверждения о «нескоростности» по фактическому материалу.

## Сводка

| Папка | Файлов | Что доказывает |
|---|---|---|
| 01-architecture-decisions | 8 | Ключевые архитектурные решения: MVP v1.0, async-контур v1.2, идемпотентность |
| 02-meeting-protocols | 5 | Полные расшифровки встреч (19.06, 24.08, 28.08) — ход проработки |
| 03-c4-abs-diagrams | 13 | C4-база АБС: контекст → контейнеры → инфраструктура → MVP |
| 04-rls-multitenancy | 6 | Изоляция тенантов на уровне БД, готовый SQL |
| 05-iam-auth | 12 | IAM-контур: runbook, онбординг, sequence, диаграммы |
| 06-sandbox-stand | 9 | Работающий стенд: план, README, отчёт 9/9 тестов, конфигурация |
| 07-domain-tutorials | 7 | Погружение в банковский домен (счета, кредиты, платежи) |
| 08-students-docs | 3 | Работа с аналитиками, сентябрь |
| 09-consulting | 7 | Консультационная поддержка и наставничество: 6 направлений, 30.04–07.09 |
| 10-early-as-is | 6 | Ранние AS-IS (12.2025–02.2026) + эталон кредитования + ранние версии tutorials |

## Хронология артефактов (даты изменения файлов)

```
2025-12-25        as-is-detailed.puml — самый ранний артефакт темы (10-early-as-is)
2026-01-22        etalon/as-is.md + .puml — эталонная схема кредитования (БКИ, госреестры)
2026-02-17        client/credit-service — клон репо (код банка писала команда разработки, не Василий)
2026-03-21..22    tutorials: clients, accounts, accountment, payments (домен; ранние версии basic/credit 21.03 — в 10-early-as-is)
2026-03-21        c4-context-diagram.puml/.md
2026-03-25        rls-* (5 файлов), c4-container-diagram.puml
2026-04-28        c4-container-diagram.md
2026-05-07        mvp-abs/deployment.puml
2026-06-19        встреча IAM → протокол 19062026 (файлы 22.06)
2026-06-22        tutorials: basic, credit; saas-onboarding-flow
2026-07-01        abs-sandbox весь стенд, коммит v4sil-burkin 01.07 20:30
2026-07-01        c4-infrastructure, iam-deploy-runbook, TEST_REPORT 9/9 OK
2026-08-24        встреча архитектуры интеграции → mvp-architecture.md v1.0
2026-08-25        docs/24082026.md (расшифровка), c4-component-diagram
2026-08-27        async-контур v1.0-1.1, идемпотентность (mmd + drawio)
2026-08-28        docs/28082026.md, async-contour-architecture.md v1.2
2026-09-01        c4-container-diagram-top.puml, async-channel-contracts.docx
2026-09-03        students-docs: services-flow, top
2026-09-07        students-docs: c4_container_abs
```

## Файлы

### 01-architecture-decisions
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| mvp-architecture.md | `docs/` | 2026-08-25 | Архитектурное решение v1.0 (24.08): 3 sync REST, SLA 300 мс |
| async-contour-architecture.md | `docs/` | 2026-08-28 | Async-контур v1.2: таблица состояний, DLQ, конверт §7.1 |
| async-channel-contracts.docx | `docs/` | 2026-09-01 | Контракты async-каналов |
| c4-component-diagram.md | `docs/` | 2026-08-25 | Верхнеуровневая схема async-контура |
| c4-component-diagram.mmd | `docs/` | 2026-08-27 | Исходник mermaid |
| c4-component-diagram-idempotency.mmd | `docs/` | 2026-08-27 | Идемпотентность inbox/outbox |
| c4-component-diagram-idempotency.drawio | `docs/` | 2026-08-27 | Drawio-версия, 2 листа |
| c4-container-diagram-top.puml | `docs/` | 2026-09-01 | C4 Container: sync ≤300 мс + async 202/вебхук |

### 02-meeting-protocols
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| 24082026.md | `docs/` | 2026-08-25 | Расшифровка встречи 24.08 (75 КБ): Kafka, мультитенантность, шаги конвейера |
| 28082026.md | `docs/` | 2026-08-28 | Расшифровка встречи 28.08 (85 КБ): async-контур, модульный монолит, PDP |
| 19062026.md | `git/abs/docs/meetings/` | 2026-06-22 | Протокол IAM 19.06: Keycloak+OPA+Kong+Istio, TTL, audit |
| 19062026.docx | `git/abs/docs/meetings/` | 2026-06-22 | Исходник docx |
| 257760380_...274.pdf | `git/abs/docs/meetings/` | 2026-06-21 | Запись/материал встречи 21.06 |

### 03-c4-abs-diagrams
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| c4-context-diagram.md | `git/abs/docs/` | 2026-03-22 | C4 контекст АБС |
| c4-context-diagram.puml | `git/abs/docs/` | 2026-03-21 | Исходник |
| c4-container-diagram.md | `git/abs/docs/` | 2026-04-28 | C4 контейнеры production |
| c4-container-diagram.puml | `git/abs/docs/` | 2026-03-25 | Исходник |
| c4-infrastructure-container-diagram.{md,puml,png,svg} | `git/abs/docs/` | 2026-07-01 | Инфраструктура (4 формата) |
| c4-mvp-container-diagram.{md,puml,png,svg} | `git/abs/docs/mvp-abs/` | 2026-07-01 | MVP-контейнеры (опорная диаграмма) |
| deployment.puml | `git/abs/docs/mvp-abs/` | 2026-05-07 | Деплой-схема MVP |

### 04-rls-multitenancy
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| rls-diagram-description.md | `git/abs/docs/` | 2026-03-25 | Описание RLS-подхода |
| rls-implementation.md | `git/abs/docs/` | 2026-03-25 | Имплементация, 52 КБ |
| rls-implementation-diagram.puml | `git/abs/docs/` | 2026-03-25 | Диаграмма имплементации |
| rls-shared-schema-diagram.puml | `git/abs/docs/` | 2026-03-25 | Shared-schema |
| rls-simple-diagram.puml | `git/abs/docs/` | 2026-03-25 | Упрощённая |
| rls-role-setup.sql | `git/abs/docs/` | 2026-03-25 | Готовый SQL настройки ролей |

### 05-iam-auth
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| iam-deploy-runbook.md / .docx | `git/abs/docs/meetings/` | 2026-07-01 | Runbook деплоя IAM в прод (52 КБ) |
| saas-onboarding-flow.md / .docx | `git/abs/docs/meetings/` | 2026-07-01 | Онбординг тенантов |
| auth-flow-sequence.{puml,png,svg} | `git/abs/docs/meetings/` | 2026-07-01 | Sequence аутентификации |
| c4-auth-container.{puml,png,svg} | `git/abs/docs/meetings/` | 2026-07-01 | Auth-контейнеры |
| reference.docx | `git/abs/docs/meetings/` | 2026-06-22 | Референс |

### 06-sandbox-stand
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| README.md | `abs-sandbox/` | 2026-07-01 | Описание стенда: стек, границы, отклонения (16 КБ) |
| TEST_REPORT.md | `abs-sandbox/` | 2026-07-01 | Прогон 9/9 сценариев OK от 01.07.2026 |
| plan.md | `git/abs/sandbox/docs/` | 2026-07-01 | Детальный план стенда (47 КБ) |
| sandbox-container-diagram.md / .puml | `abs-sandbox/docs/` | 2026-07-01 | C4 стенда |
| docker-compose.yml | `abs-sandbox/` | 2026-07-01 | Все сервисы стенда |
| kong.yml | `abs-sandbox/kong/` | 2026-07-01 | Kong + custom Lua plugin blacklist-guard |
| authz.rego | `abs-sandbox/opa/policies/abs/rbac/` | 2026-07-01 | Rego-политика RBAC |
| realm-export.json | `abs-sandbox/keycloak/` | 2026-07-01 | Конфигурация Keycloak realm |

### 07-domain-tutorials
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| acounts.md | `git/abs/docs/tutorials/` | 2026-03-21 | Домен: счета |
| acountment.md | `git/abs/docs/tutorials/` | 2026-03-21 | Домен: проводки |
| payments.md | `git/abs/docs/tutorials/` | 2026-03-21 | Домен: платежи |
| payments-vs-acountments.md | `git/abs/docs/tutorials/` | 2026-03-21 | Различия платежи/проводки |
| clients.md | `git/abs/docs/tutorials/` | 2026-03-21 | Домен: клиенты |
| basic.md | `git/abs/docs/tutorials/` | 2026-06-22 | Базовый курс по домену |
| credit.md | `git/abs/docs/tutorials/` | 2026-06-22 | Домен: кредиты |

### 08-students-docs
| Файл | Исходный путь | Дата | Что доказывает |
|---|---|---|---|
| c4-container-diagram-services-flow.puml | `docs/students-docs/` | 2026-09-03 | Схема потоков сервисов для аналитиков |
| c4-container-diagram-top.puml | `docs/students-docs/` | 2026-09-03 | Верхнеуровневая для аналитиков |
| c4_container_abs.puml | `docs/students-docs/` | 2026-09-07 | Актуальная версия |

### 09-consulting
| Файл | Что доказывает |
|---|---|
| 00-consulting-index.md | Реестр направлений консультаций + метрики времени отклика |
| C1-iam-docs-review.md | Ревью Keycloak/PDP/API Gateway для команды LAAS: 7 замечаний, все отработаны; отклик 4–5 минут, схема развёртывания за 42 минуты |
| C2-keycloak-block-sync.md | Отклонён CDC для блокировки банка (окно уязвимости), согласован sync Admin API; ответ за 9 минут, полный цикл наставничества |
| C3-mentoring-ivan-c4.md | Менторинг аналитика (июнь–сентябрь): User Story, модульный монолит, C4 за 2 итерации ревью; методичка по C4 в чате |
| C4-kong-oauth-proxy.md | Ответ на вопрос Kong Enterprise/Lua/OAuth2 Proxy — работающим стендом; отклонены лицензия и лишний сервис |
| C5-email-notifications.md | Уведомления: возврат к бизнес-сценариям, YAGNI-проверка, перенос решения с другого проекта |
| C6-db-storage-migrations.md | Топология БД (схема-на-сервис + RLS + Patroni) и выбор Flyway — ADR в одном сообщении, вопрос закрыт с первого прохода |

### 10-early-as-is
| Файл | Исх. путь | Дата | Что доказывает |
|---|---|---|---|
| as-is-detailed.puml | `be/` | 2025-12-25 | Самый ранний артефакт темы: детальный AS-IS банковского бэкенда |
| as-is.md | `etalon/` | 2026-01-22 | Эталонная схема кредитования «приближённая к реальности» (БКИ, госреестры, фронт-линия) |
| as-is.puml | `etalon/` | 2026-01-22 | Диаграмма эталона |
| as-is.puml | `be/` | 2026-02-26 | AS-IS бэкенда, февральская итерация |
| early-versions/basic-2026-03-21.md | `abs/` | 2026-03-21 | Ранняя редакция tutorial (поздняя 22.06 — в 07-domain-tutorials): итеративность доменных курсов |
| early-versions/credit-2026-03-21.md | `abs/` | 2026-03-21 | Ранняя редакция tutorial по кредитам |

Папка добавлена по итогам сверки с `D:\Documents\Dasha\Diagrams\aston\evergreen`
(проверено хэшами: 5 из 7 tutorials там — дубликаты; отличались basic и credit —
взяты ранние версии; прочее — новые артефакты). Хронология темы расширена:
работа над Эвергрином началась не в марте, а 25.12.2025 — 8,5 месяцев
непрерывной линии.

## Исходное дерево

```
D:\Астон\evergreen\
├── docs\                        ← рабочие документы интеграции
├── client\credit-service\       ← репо банка (код НЕ Василия)
├── abs-sandbox\                 ← auth/authz стенд АБС (автор v4sil-burkin)
└── git\abs\                     ← клон репо АБС (docs, meetings, tutorials, mvp-abs, rls)
```
