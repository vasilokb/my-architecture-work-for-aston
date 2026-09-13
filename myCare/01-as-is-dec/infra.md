```
my-care-infra/
├── 📁 my-care/                           # Основная директория инфраструктуры
│   ├── 📁 api-gateway/                   # API Gateway сервис
│   │   └── 📄 .env
│   │
│   ├── 📁 auto-service/                  # Сервис автострахования
│   │   ├── 📄 .env
│   │   └── 📁 auto-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 aviation-service/              # Сервис авиастрахования
│   │   ├── 📄 .env
│   │   └── 📁 aviation-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 client-service/                # Сервис клиентов
│   │   ├── 📄 .env
│   │   └── 📁 client-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 dms-service/                   # Document Management System
│   │   ├── 📄 .env
│   │   ├── 📄 docker-compose.yml
│   │   └── 📁 dms-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 email-notification-service/    # Сервис email-уведомлений
│   │   ├── 📄 .env
│   │   └── 📁 notification-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 employee-service/              # Сервис сотрудников
│   │   ├── 📄 .env
│   │   └── 📁 employee-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 eureka-server/                 # Service Discovery (Eureka)
│   │   ├── 📄 .env
│   │   └── 📄 docker-compose.yml
│   │
│   ├── 📁 info-service/                  # Информационный сервис
│   │   ├── 📄 .env
│   │   └── 📁 info-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 kafka/                         # Кафка (message broker)
│   │   ├── 📄 docker-compose.yml
│   │   └── 📁 env/
│   │       └── 📄 kafka.env
│   │
│   ├── 📁 keycloak/                      # Identity & Access Management
│   │   ├── 📄 .env
│   │   ├── 📄 docker-compose.yml
│   │   ├── 📁 import/
│   │   │   └── 📄 my-care-realm.json
│   │   ├── 📁 init-db/
│   │   │   └── 📄 init-db.sql
│   │   └── 📁 themes/
│   │       ├── 📁 MyCare/
│   │       │   └── 📁 login/
│   │       │       ├── 📄 error.ftl
│   │       │       ├── 📄 info.ftl
│   │       │       ├── 📄 login-update-password.ftl
│   │       │       ├── 📄 theme.properties
│   │       │       ├── 📁 messages/
│   │       │       │   ├── 📄 messages_en.properties
│   │       │       │   └── 📄 messages_ru.properties
│   │       │       └── 📁 resources/
│   │       │           ├── 📁 css/
│   │       │           │   └── 📄 styles.css
│   │       │           ├── 📁 img/
│   │       │           │   ├── 📄 favicon.ico
│   │       │           │   ├── 📄 show.svg
│   │       │           │   └── 📄 unshow.svg
│   │       │           └── 📁 js/
│   │       │               └── 📄 password-validation.js
│   │       └── 📁 email-theme/
│   │           └── 📁 email/
│   │               ├── 📄 theme.properties
│   │               └── 📁 html/
│   │                   ├── 📄 email-verification.ftl
│   │                   ├── 📄 executeActions.ftl
│   │                   └── 📄 password-reset.ftl
│   │
│   ├── 📁 mongo-db/                      # MongoDB
│   │   ├── 📄 .env
│   │   └── 📁 mongo-db-docker-compose/
│   │       └── 📄 docker-compose.yml
│   │
│   ├── 📁 promo-service/                 # Сервис промоакций
│   │   ├── 📄 .env
│   │   └── 📁 promo-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 property-service/              # Сервис имущественного страхования
│   │   ├── 📄 .env
│   │   └── 📁 property-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 rabbitmq/                      # RabbitMQ (message broker)
│   │   └── 📄 .env
│   │
│   ├── 📁 redis/                         # Redis (кеширование)
│   │   └── 📄 .env
│   │
│   ├── 📁 risks-service/                 # Сервис оценки рисков
│   │   ├── 📄 .env
│   │   └── 📁 risks-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 storage-service/               # Сервис хранения файлов (MinIO)
│   │   ├── 📄 .env
│   │   └── 📁 minio-docker-compose/
│   │       └── 📄 docker-compose.yml
│   │
│   ├── 📁 travel-service/                # Сервис туристического страхования
│   │   ├── 📄 .env
│   │   └── 📁 travel-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   ├── 📁 user-service/                  # Сервис пользователей
│   │   ├── 📄 .env
│   │   └── 📁 user-db-docker-compose/
│   │       ├── 📄 docker-compose.yml
│   │       └── 📁 init-scripts/
│   │           └── 📄 init.sql
│   │
│   └── 📁 zipkin/                        # Distributed Tracing
│       ├── 📄 docker-compose.yml
│       └── 📁 sql/
│           └── 📄 schema.sql
│
├── 📄 .gitignore
└── 📄 README.md
```

## 📋 **Краткое описание инфраструктуры:**

### **🎯 Основные компоненты:**
1. **Микросервисы** (12+ сервисов) - каждая бизнес-домен имеет свой сервис
2. **Базы данных** - PostgreSQL для большинства сервисов, MongoDB для документов
3. **Message Brokers** - Kafka и RabbitMQ для асинхронной коммуникации
4. **Сервисы инфраструктуры** - Eureka, Zipkin, MinIO

### **🔐 Безопасность:**
- **Keycloak** - единая система аутентификации/авторизации
- Кастомизированные темы для логина и email-рассылок
- Поддержка русского и английского языков

### **🗄️ Базы данных:**
Каждый сервис имеет свою БД с:
- Docker Compose для развертывания
- Init скриптами для инициализации схемы
- Изоляцией данных

### **📦 Хранение:**
- **MinIO** - S3-совместимое object storage
- Отдельный сервис для управления документами (DMS)

### **🔍 Мониторинг и трассировка:**
- **Zipkin** - распределенная трассировка
- **Eureka** - service discovery
- **Redis** - кеширование

### **🌐 Сеть:**
- **API Gateway** - единая точка входа
- Сервисная сеть на основе Docker Compose
- Настройки окружения через `.env` файлы

### **Особенности:**
- Полная изоляция сервисов
- Готовая к продакшену инфраструктура
- Поддержка нескольких языков (RU/EN)
- Модульная архитектура
- Документированные настройки для каждого компонента