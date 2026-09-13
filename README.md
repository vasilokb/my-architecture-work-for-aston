# Архитектурная работа в Астон — доказательная база

Артефакты архитектурной работы Василия Буркина (`vasilokb`) в лаборатории
Астон: сентябрь 2025 — сентябрь 2026. Периодическая доп. активность
архитектора параллельно с основной работой (см. [C10](career-aggregator/04-consulting/C10-cerber-integration-final.md)).

Каждая папка — отдельный проект с собственным `00-INDEX.md`
(файл → исходный путь → дата → что доказывает).

## Проекты

| Папка | Проект | Период | Что внутри |
|---|---|---|---|
| [Evergreen/](Evergreen/) | Интеграция банка «Эвергрин» с мультитенантной АБС | 12.2025 — 09.2026 | Архитектурные решения (MVP, async-контур, идемпотентность), C4-база, RLS-мультитенантность, IAM-контур, auth-стенд (9/9 тестов), доменные туториалы, 6 консультаций |
| [Investment/](Investment/) | Liberty Investment — инвестиционная платформа (28 сервисов) | 05–07.2026 | Аудит за 2 дня (2500+ строк, вердикт «microlith»), DDD-аудит, as-is с C1/C2, пакет схем авторизации |
| [career-aggregator/](career-aggregator/) | Карьерный агрегатор / Career Planner | 03–09.2026 | Три итерации: код (hexagonal, pgvector-прототип — полностью авторский), ТЗ, 5 версий диаграмм, архитектура v1.2 + консультации C8–C10 |
| [myCare/](myCare/) | My Care Insurance — страховая платформа | 12.2025 — 03.2026 | AS-IS 6 доменов, фабрика продуктов, Lightweight AVD v2.0 + собственный стандарт AVD |
| [dynamic-presale/](dynamic-presale/) | AI-платформа оценки пресейлов | 01–03.2026 | Полный цикл: эскизы → требования → AVD v2.1 «Утверждено» + руководство стажёрам |
| [sql-trainer/](sql-trainer/) | SQL Trainer / SQL Academy | 09–12.2025 | Диаграммы → работающий MVP в K8s (код) → архитектурный документ (5 ADR, SEI) |
| [capital-bank/](capital-bank/) | Capital Bank — аудит НФТ | 11.2025 | Enterprise-аудит за 72 часа: разбор НФТ, 10 сценариев качества, план трансформации |
| [competency-center/](competency-center/) | ИИ-оценка проектов — консультация | 01–03.2026 | C7: RAG/чанкинг/ollama, spike-культура |

## Консультационная линия (10 направлений, сквозная нумерация)

| # | Тема | Папка |
|---|---|---|
| C1 | Ревью IAM-документации (Keycloak/PDP/Gateway), 7 замечаний — все отработаны | [Evergreen/09-consulting/](Evergreen/09-consulting/C1-iam-docs-review.md) |
| C2 | Блокировка банка: отклонён CDC (окно уязвимости), согласован sync Admin API | [Evergreen/09-consulting/](Evergreen/09-consulting/C2-keycloak-block-sync.md) |
| C3 | Менторинг аналитика: User Story → модульный монолит → C4 за 2 итерации | [Evergreen/09-consulting/](Evergreen/09-consulting/C3-mentoring-ivan-c4.md) |
| C4 | Kong: ответ на вопрос Enterprise/Lua/OAuth2 Proxy — работающим стендом | [Evergreen/09-consulting/](Evergreen/09-consulting/C4-kong-oauth-proxy.md) |
| C5 | Уведомления: возврат к бизнес-сценариям (YAGNI-проверка) | [Evergreen/09-consulting/](Evergreen/09-consulting/C5-email-notifications.md) |
| C6 | Топология БД: схема-на-сервис + RLS + Patroni + выбор Flyway — ADR в одном ответе | [Evergreen/09-consulting/](Evergreen/09-consulting/C6-db-storage-migrations.md) |
| C7 | ИИ-оценка: RAG, чанки, ollama-стенд, Excel-расчёты | [competency-center/](competency-center/C7-ai-project-assessment.md) |
| C8 | Источник вакансий: Цербер vs HH.ru — due diligence зависимости | [career-aggregator/04-consulting/](career-aggregator/04-consulting/C8-vacancy-source-decision.md) |
| C9 | pgvector: сомнение команды снято прототипом «для затравки» | [career-aggregator/04-consulting/](career-aggregator/04-consulting/C9-pgvector-prototype-reassurance.md) |
| C10 | Финал: интеграция с Цербером решена в день стопа доп. активности | [career-aggregator/04-consulting/](career-aggregator/04-consulting/C10-cerber-integration-final.md) |

Метрики отклика собраны в [Evergreen/09-consulting/00-consulting-index.md](Evergreen/09-consulting/00-consulting-index.md):
медиана первого отклика — минуты/часы; ответы на следующий день компенсируются
методической полнотой; в C4 и C9 сомнения команды закрывались работающими
прототипами, а не объяснениями.

## Методология (сквозная по всем темам)

- **Spike-культура:** гипотеза → личный прототип → передача результатов
  команде (abs-sandbox, pgvector-прототип, ollama, Excel-расчёты, MVP в K8s)
- **SEI-дисциплина:** атрибуты качества, сценарии «стимул → метрика»,
  ADR (sql-trainer, capital-bank)
- **Итеративность:** версии диаграмм v1→v5, восемь AS-IS-итераций,
  трекер качества документа
- **Кросс-проектная синергия:** PDP/ABAC, CDC, PERT, модульный монолит,
  Transaction Outbox — решения переносятся между темами
- **Документация как код:** PlantUML/C4 исходники, ER в двух нотациях

## Хронология (непрерывно, без «простоев»)

```
2025-09-29 → 12-08   sql-trainer: диаграммы → MVP в K8s → архитектурный документ
2025-11-29 → 12-01   capital-bank: аудит НФТ за 72 часа
2025-12-09 → 12-30   mycare: AS-IS + фабрика продуктов + gpt-итерации
2025-12-25 → 09-07   evergreen: 8,5 месяцев — АБС, IAM, стенд, консультации
2026-01-14 → 03-30   dynamic-presale: полный цикл до AVD «Утверждено»
2026-01-13 → 03-16   competency-center: консультация C7
2026-03-29 → 09-10   career-aggregator: три итерации, код + архитектура
2026-05-23 → 07-23   investment: аудиты, as-is, авторизация
2026-09-10           стоп доп. активности лаборатории (C10) — работа
                     передана в работоспособном виде
```

## Статистика

~360 файлов | 8 проектных тем | 10 консультационных направлений |
60+ диаграмм (PlantUML/C4/Mermaid/drawio) | 4 архитектурных документа
(АВД/AVD) | 2 аудита | работающий стенд + 2 MVP-прототипа в коде
