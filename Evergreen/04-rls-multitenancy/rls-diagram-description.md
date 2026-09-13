# Диаграмма реализации Row-Level Security (RLS)

## Обзор диаграммы

Диаграмма [`docs/rls-implementation-diagram.puml`](docs/rls-implementation-diagram.puml) показывает полный поток реализации RLS в облачной АБС для обеспечения многотенантности.

## Ключевые компоненты диаграммы

### 1. **Цветовая схема**
- **Оранжевый (`#FFE5CC`)**: Клиент/Тенант
- **Голубой (`#CCE5FF`)**: Приложение (API Gateway, бизнес-сервисы)
- **Зеленый (`#CCFFCC`)**: База данных (PostgreSQL)
- **Красный (`#FFCCCC`)**: Безопасность (Keycloak)

### 2. **Основные компоненты**

#### **API Gateway**
- **JWT Parser**: Извлекает JWT токен из запроса
- **Tenant Extractor**: Извлекает `tenant_id` из claims токена
- **Добавление заголовка**: Добавляет `X-Tenant-ID` к внутренним запросам

#### **Бизнес-сервис (Модуль клиентов)**
- **TenantInterceptor**: Spring Interceptor, устанавливающий tenant_id в ThreadLocal
- **TenantContext**: ThreadLocal контейнер для хранения tenant_id в рамках запроса
- **Service Layer**: Бизнес-логика приложения
- **Repository**: Слой доступа к данным

#### **Connection Pool**
- **TenantAwareDataSource**: DataSource, устанавливающий сессионную переменную в PostgreSQL
- **Connection Wrapper**: Обертка над соединением, гарантирующая установку `app.current_tenant`

#### **PostgreSQL Cluster**
- **Схема tenant_alfa**: Отдельная схема для банка "Альфа"
- **Схема tenant_beta**: Отдельная схема для банка "Бета"
- **RLS Policy**: Политика безопасности на уровне строк:
  ```sql
  tenant_id = current_setting('app.current_tenant', true)
  ```

#### **Keycloak**
- Централизованная аутентификация
- Выдача JWT токенов с claim `tenant_id`

## Поток данных (29 шагов)

### Фаза 1: Аутентификация (шаги 1-5)
1. Клиент отправляет HTTPS запрос с JWT токеном
2. API Gateway валидирует токен в Keycloak
3. Keycloak возвращает результат валидации
4. JWT Parser извлекает `tenant_id` из токена
5. Добавляется заголовок `X-Tenant-ID: alfa`

### Фаза 2: Обработка в бизнес-сервисе (шаги 6-9)
6. Запрос передается в бизнес-сервис с заголовком
7. TenantInterceptor устанавливает `tenant_id` в ThreadLocal
8. Выполняется бизнес-логика
9. Вызывается репозиторий для доступа к данным

### Фаза 3: Работа с базой данных (шаги 10-23)
10. Запрос соединения из пула
11. Получение connection
12. Установка сессионной переменной: `SET app.current_tenant = 'alfa'`
13. Доступ к схеме `tenant_alfa`
14. Запрос к таблице `clients`
15. Применение RLS политики
16. Возврат только строк с `tenant_id = 'alfa'`
17-23. Возврат отфильтрованных данных через все слои

### Фаза 4: Завершение обработки (шаги 24-29)
24. Преобразование в объекты домена
25. Очистка ThreadLocal контекста
26. Завершение обработки в интерцепторе
27. Формирование ответа
28. REST API ответ
29. HTTP ответ клиенту

## Пример изоляции

Диаграмма показывает пример изоляции:
- Если `tenant_id = 'alfa'`, запрос к `tenant_beta.clients` вернет 0 записей
- RLS политика гарантирует, что каждый тенант видит только свои данные

## Техническая реализация

### PostgreSQL Configuration
```sql
-- Включение RLS
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

-- Создание политики
CREATE POLICY tenant_isolation_policy
ON clients USING (tenant_id = 
    current_setting('app.current_tenant', true));

-- Установка переменной
SET app.current_tenant = 'alfa';
```

### Spring Configuration
```java
@Component
public class TenantInterceptor implements HandlerInterceptor {
    
    @Override
    public boolean preHandle(HttpServletRequest request,
                           HttpServletResponse response,
                           Object handler) {
        String tenantId = extractFromJWT(request);
        TenantContext.setCurrentTenant(tenantId);
        return true;
    }
}
```

## Преимущества реализации

1. **Безопасность**: Изоляция на уровне СУБД, даже при ошибках приложения
2. **Производительность**: Минимальный overhead при правильной индексации
3. **Масштабируемость**: Поддержка сотен тенантов в одном кластере
4. **Гибкость**: Возможность настройки разных политик для разных ролей
5. **Аудит**: Полная трассируемость доступа к данным

## Визуализация диаграммы

Для просмотра диаграммы:
1. Установите PlantUML плагин в VS Code
2. Откройте файл [`docs/rls-implementation-diagram.puml`](docs/rls-implementation-diagram.puml)
3. Нажмите `Alt+D` для предпросмотра

Или используйте онлайн-рендерер PlantUML, скопировав содержимое файла.

## Связанные документы

- [`docs/rls-implementation.md`](docs/rls-implementation.md) - Детальное описание реализации RLS
- [`docs/c4-infrastructure-container-diagram.md`](docs/c4-infrastructure-container-diagram.md) - Инфраструктурная диаграмма АБС
- [`docs/c4-container-diagram.md`](docs/c4-container-diagram.md) - Контейнерная диаграмма бизнес-доменов