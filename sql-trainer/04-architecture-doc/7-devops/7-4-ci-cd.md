### 7.4. CI/CD и путь поставки изменений

Данный раздел описывает конвейер CI/CD для SQL Trainer и его связь с продовым развёртыванием системы.

---

#### 7.4.1. Общая схема процесса

Изменения в SQL Trainer проходят следующие этапы:

1. **Разработка и работа с Git**

    * Исходный код хранится в Git-репозитории, включающем:

        * frontend (React SPA);
        * backend-сервисы (Users/Auth, Courses/Tasks, Execution, Progress/Reporting);
        * миграции для App DB и Training DB;
        * инфраструктурные манифесты (Helm-chart или kustomize).
    * Разработчики работают в feature-ветках и выполняют merge в:

        * `develop` — для Dev/Test;
        * `main` — для релизных версий (Prod).

2. **Этап CI: сборка и тесты**

   При push/merge в целевые ветки CI-сервер (Jenkins / GitLab CI / иной инструмент) выполняет:

    * Сборку frontend:

        * установка зависимостей;
        * линтеры и unit-тесты;
        * сборка production-бандла SPA.
    * Сборку backend:

        * сборка Java/Spring-проектов;
        * unit-тесты и, при наличии, интеграционные тесты;
        * базовые проверки качества (линтеры, статический анализ — опционально).
    * Проверку инфраструктурных артефактов:

        * lint Helm-chart’ов / манифестов;
        * проверку корректности конфигурационных файлов.

3. **Сборка Docker-образов и публикация**

    * По результатам успешного CI создаются Docker-образы:

        * `sql-trainer-frontend`;
        * `sql-trainer-users`;
        * `sql-trainer-courses`;
        * `sql-trainer-execution`;
        * `sql-trainer-progress`.
    * Образы тегируются (номер версии и/или хэш коммита) и публикуются во внутренний Docker Registry.

4. **Деплой в Kubernetes (Dev / Test / Prod)**

    * **Dev**:

        * автоматический деплой в namespace `sql-trainer-dev` после успешного CI;
        * применение Helm-chart’а/манифестов для Dev;
        * запуск миграций App DB и Training DB для Dev;
        * среда используется разработчиками для ручной проверки и отладки.
    * **Test**:

        * продвижение версии на Test выполняется с ручным подтверждением (manual approve) в CI;
        * деплой в namespace `sql-trainer-test` с использованием конкретного набора образов, прошедшего Dev;
        * запуск миграций App DB и Training DB для Test;
        * выполнение интеграционных и, при необходимости, нагрузочных тестов.
    * **Prod (учебный стенд)**:

        * деплой на Prod выполняется только из версии, прошедшей Test;
        * используется тот же набор образов, что и на Test;
        * применяется конфигурация `sql-trainer-prod`;
        * выполняются миграции App DB и Training DB для Prod;
        * запуск деплоя на Prod требует ручного подтверждения ответственного лица (архитектор/тимлид/владелец продукта).

5. **Роль DevOps**

    * настройка и поддержка pipeline’ов CI/CD;
    * управление Helm-chart’ами и манифестами;
    * настройка ресурсов, переменных окружения, секретов;
    * управление конфигурацией Nginx (раздача статики SPA и маршрутизация API).

---

#### 7.4.2. Учёт миграций баз данных

Миграции для App DB и Training DB являются частью артефактов репозитория и выполняются с помощью стандартного инструмента (например, Flyway или Liquibase):

* для Dev — автоматически при каждом деплое версии;
* для Test — при деплое релизного билда, перед тестированием;
* для Prod — как отдельный шаг пайплайна (или как часть деплоя) с обязательным контролем результата.

Миграции App DB и Training DB выполняются раздельно, чтобы избежать пересечения схем и упростить откат.

---

#### 7.4.3. Схема CI/CD и продового развёртывания (PlantUML)

```plantuml
@startuml SQLTrainer_Deployment_CICD
skinparam monochrome true
skinparam linetype ortho

title CI/CD + Deployment (Prod) – SQL Trainer

' === Actors ===
actor Dev as DEV
actor DevOps as DEVOPS
actor "User\n(Стажёр / Методист / Админ)" as USER

' === CI/CD зона ===
node "CI/CD Zone" as CICD {
  node "Git-репозиторий\n(sql-trainer\nfrontend/backend\n+ DB migrations)" as GIT
  node "CI/CD Server\n(Jenkins / GitLab CI / др.)" as CI
  node "Docker Registry\n(внутренний)" as REG
}

' === Корпоративная инфраструктура Hetzner (Prod) ===
rectangle "Hetzner – Internal Infrastructure (Prod)" as HETZNER {

  ' --- Prod Kubernetes Cluster ---
  node "Prod Kubernetes Cluster\nnamespace: sql-trainer-prod" as K8S {

    node "Ingress / Nginx\n+ Static UI (React SPA)" as NGINX

    rectangle "Backend Services\n(Java + Spring)" as BE_SERVICES {
      component "Users/Auth Service" as USERS_SVC
      component "Courses/Tasks Service" as COURSES_SVC
      component "Execution Service" as EXEC_SVC
      component "Progress/Reporting Service" as PROGRESS_SVC
    }
  }

  database "App DB\nPostgreSQL\nservice data" as APPDB
  database "Training DB\nPostgreSQL\ntraining data" as TRAINDB
}

' === SSO зона ===
node "Corporate SSO Zone" as SSOZONE {
  node "Keycloak / SSO" as KEYCLOAK
  node "Active Directory" as AD
}

' === VPN периметр ===
cloud "TLS/SSL VPN\nкорпоративный доступ" as VPN

' === CI/CD потоки ===
DEV --> GIT : commit / push\nsource code
GIT --> CI : webhook / git pull

CI --> REG : build & push\nDocker images
CI --> K8S : deploy/upgrade\n(Helm / kubectl)
CI --> APPDB : run DB migrations\n(App DB)
CI --> TRAINDB : run DB migrations\n(Training DB)

DEVOPS --> CI : управление\npipelines / approvals
DEVOPS --> NGINX : управление\nконфигурацией

' === Рабочий трафик пользователей ===
USER --> VPN : подключение\nTLS/SSL VPN
VPN --> NGINX : HTTPS 443\nsql-trainer.internal

NGINX --> USERS_SVC    : HTTP(S) /api/users
NGINX --> COURSES_SVC  : HTTP(S) /api/courses
NGINX --> EXEC_SVC     : HTTP(S) /api/execute
NGINX --> PROGRESS_SVC : HTTP(S) /api/progress

' === Взаимодействие backend-а с БД и SSO ===
USERS_SVC    --> APPDB   : JDBC 5432\nпользователи, роли
COURSES_SVC  --> APPDB   : JDBC 5432\nкурсы, задачи
PROGRESS_SVC --> APPDB   : JDBC 5432\nпопытки, прогресс

EXEC_SVC     --> TRAINDB : JDBC 5432\nучебные SQL-запросы

' === Интеграция с SSO ===
NGINX --> KEYCLOAK : HTTPS\nOIDC/OAuth2 (аутентификация)
KEYCLOAK --> AD    : LDAP/LDAPS\nкорпоративный каталог

@enduml
```

Данная схема объединяет в одном представлении:

* конвейер CI/CD (Git → CI → Registry → Kubernetes + миграции БД);
* структуру продового окружения (Nginx/Ingress, backend-сервисы, App DB, Training DB, Keycloak/AD, VPN, пользователи).
