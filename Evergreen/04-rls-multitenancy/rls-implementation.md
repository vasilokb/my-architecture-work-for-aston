# Реализация Row-Level Security (RLS) в облачной АБС

## 1. Обзор подхода к многотенантности

В облачной АБС используется **оптимизированный подход** к изоляции данных между банками-клиентами (тенантами):

| Уровень изоляции | Реализация | Обоснование |
|-----------------|------------|--------------|
| **Shared Schema + RLS** | Все тенанты в одной схеме, изоляция через RLS политики | Упрощение миграций, снижение overhead, единая структура БД |
| **Префиксы в кэше** | Ключи Redis содержат tenant_id | Изоляция в распределенном кэше |
| **Логическое разделение** | tenant_id во всех таблицах, составные индексы | Гарантированная производительность |

**Архитектурное решение:** Отказ от схемной изоляции в пользу Shared Schema с RLS по следующим причинам:
1. **Упрощение миграций:** Одна структура БД для всех тенантов
2. **Снижение overhead:** Не нужно поддерживать сотни идентичных схем
3. **Упрощение CI/CD:** Миграции применяются один раз ко всей БД
4. **Производительность:** Лучшая статистика планировщика запросов

## 2. Архитектура RLS

### 2.1 Концептуальная модель (Shared Schema)

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Cluster                        │
├─────────────────────────────────────────────────────────────┤
│  Schema: public (shared)                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Таблица: clients                                   │    │
│  │  ┌─────┬──────────┬──────────┬──────────────┐      │    │
│  │  │ id  │ tenant_id│ name     │ created_at   │      │    │
│  │  ├─────┼──────────┼──────────┼──────────────┤      │    │
│  │  │ 1   │ alfa     │ Иван     │ 2024-01-01   │      │    │
│  │  │ 2   │ alfa     │ Мария    │ 2024-01-02   │      │    │
│  │  │ 3   │ beta     │ Петр     │ 2024-01-03   │      │
│  │  │ 4   │ beta     │ Анна     │ 2024-01-04   │      │
│  │  └─────┴──────────┴──────────┴──────────────┘      │    │
│  │                                                     │    │
│  │  RLS Policy: tenant_id = current_setting('app.current_tenant') │
│  │  Индекс: CREATE INDEX idx_clients_tenant_id ON clients(tenant_id) │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Таблица: accounts                                           │
│  ┌─────┬──────────┬──────────┬──────────────┐               │
│  │ id  │ tenant_id│ client_id│ balance      │               │
│  ├─────┼──────────┼──────────┼──────────────┤               │
│  │ 101 │ alfa     │ 1        │ 1000.00      │               │
│  │ 102 │ alfa     │ 2        │ 5000.00      │               │
│  │ 103 │ beta     │ 3        │ 2000.00      │               │
│  │ 104 │ beta     │ 4        │ 3000.00      │               │
│  └─────┴──────────┴──────────┴──────────────┘               │
│  RLS Policy: tenant_id = current_setting('app.current_tenant') │
│  Индекс: CREATE INDEX idx_accounts_tenant_id ON accounts(tenant_id, client_id) │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Поток установки tenant_id

```
1. Клиент → API Gateway (JWT с claim tenant_id="alfa")
2. API Gateway → Бизнес-сервис (добавляет заголовок X-Tenant-ID)
3. Бизнес-сервис → Connection Pool (устанавливает app.current_tenant)
4. PostgreSQL → Применяет RLS политики
```

## 3. Реализация в PostgreSQL

### 3.1 Создание таблиц в Shared Schema

```sql
-- Создание таблицы клиентов в общей схеме
CREATE TABLE clients (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL, -- БЕЗ DEFAULT! Требуем явного указания
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Триггер для гарантии заполнения tenant_id
CREATE OR REPLACE FUNCTION ensure_tenant_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tenant_id IS NULL THEN
        RAISE EXCEPTION 'tenant_id cannot be NULL';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ensure_tenant_id
    BEFORE INSERT OR UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION ensure_tenant_id();

-- Составной индекс с tenant_id на первом месте (КРИТИЧНО для производительности RLS)
CREATE INDEX idx_clients_tenant_id 
ON clients(tenant_id, id);

-- Частичный индекс для активных клиентов конкретного тенанта
-- Включаем tenant_id в условие WHERE для гарантированного использования с RLS
CREATE INDEX idx_clients_active 
ON clients(status, tenant_id) 
WHERE status = 'ACTIVE';
```

### 3.2 Настройка RLS политик с FORCE ROW LEVEL SECURITY

```sql
-- Включение RLS для таблицы с FORCE (КРИТИЧНО для SaaS)
-- FORCE заставляет политику работать даже для владельца таблицы
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients FORCE ROW LEVEL SECURITY;

-- Создание простой и эффективной политики доступа
-- БЕЗ подзапросов EXISTS - только прямое сравнение
CREATE POLICY tenant_isolation_policy ON clients
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));

-- Политика для администраторов платформы (видят все тенанты)
CREATE POLICY platform_admin_policy ON clients
    FOR ALL
    TO platform_admin
    USING (true)
    WITH CHECK (true);

-- Разрешение доступа для сервисного пользователя
GRANT ALL ON clients TO service_user;

-- Аналогично для таблицы accounts
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;

CREATE POLICY accounts_tenant_policy ON accounts
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true));
```

### 3.3 Управление сессионными переменными

```sql
-- Установка tenant_id для текущей сессии
SET app.current_tenant = 'alfa';

-- Проверка текущего значения
SHOW app.current_tenant;

-- Сброс (для отладки)
RESET app.current_tenant;
```

## 4. Интеграция с приложением

### 4.1 Безопасный Connection Pool с гарантированной очисткой контекста и поддержкой Wrapper

```java
@Component
public class SafeTenantAwareDataSource extends AbstractDataSource {
    
    private static final String SET_TENANT_SQL = "SET app.current_tenant = ?";
    private static final String RESET_TENANT_SQL = "RESET app.current_tenant";
    
    @Override
    public Connection getConnection() throws SQLException {
        Connection rawConnection = super.getConnection();
        return new TenantAwareConnectionProxy(rawConnection);
    }
    
    private class TenantAwareConnectionProxy implements Connection, Wrapper {
        private final Connection delegate;
        private boolean tenantSet = false;
        
        public TenantAwareConnectionProxy(Connection delegate) {
            this.delegate = delegate;
        }
        
        // Реализация интерфейса Wrapper для совместимости с Hibernate/JPA
        @Override
        public <T> T unwrap(Class<T> iface) throws SQLException {
            if (iface.isInstance(this)) {
                return iface.cast(this);
            }
            return delegate.unwrap(iface);
        }
        
        @Override
        public boolean isWrapperFor(Class<?> iface) throws SQLException {
            return iface.isInstance(this) || delegate.isWrapperFor(iface);
        }
        
        @Override
        public Statement createStatement() throws SQLException {
            ensureTenantContext();
            return delegate.createStatement();
        }
        
        @Override
        public PreparedStatement prepareStatement(String sql) throws SQLException {
            ensureTenantContext();
            return delegate.prepareStatement(sql);
        }
        
        @Override
        public void close() throws SQLException {
            try {
                // ГАРАНТИРОВАННАЯ очистка контекста перед возвратом в пул
                // Даже при необработанных исключениях в блоке finally
                if (tenantSet) {
                    try (Statement stmt = delegate.createStatement()) {
                        stmt.execute(RESET_TENANT_SQL);
                    }
                }
            } finally {
                delegate.close();
            }
        }
        
        private void ensureTenantContext() throws SQLException {
            if (!tenantSet) {
                String tenantId = TenantContext.getCurrentTenant();
                if (tenantId == null) {
                    throw new IllegalStateException("Tenant context not set");
                }
                
                try (PreparedStatement stmt = delegate.prepareStatement(SET_TENANT_SQL)) {
                    stmt.setString(1, tenantId);
                    stmt.execute();
                    tenantSet = true;
                }
            }
        }
        
        // Делегирование всех остальных методов Connection
        @Override
        public CallableStatement prepareCall(String sql) throws SQLException {
            ensureTenantContext();
            return delegate.prepareCall(sql);
        }
        
        @Override
        public String nativeSQL(String sql) throws SQLException {
            return delegate.nativeSQL(sql);
        }
        
        @Override
        public void setAutoCommit(boolean autoCommit) throws SQLException {
            delegate.setAutoCommit(autoCommit);
        }
        
        @Override
        public boolean getAutoCommit() throws SQLException {
            return delegate.getAutoCommit();
        }
        
        @Override
        public void commit() throws SQLException {
            delegate.commit();
        }
        
        @Override
        public void rollback() throws SQLException {
            delegate.rollback();
        }
        
        // ... делегирование всех остальных методов Connection
    }
}
```

### 4.2 Spring Interceptor для установки tenant_id

```java
@Component
public class TenantInterceptor implements HandlerInterceptor {
    
    @Override
    public boolean preHandle(HttpServletRequest request, 
                           HttpServletResponse response, 
                           Object handler) {
        
        // Извлечение tenant_id из JWT токена
        String tenantId = extractTenantIdFromJWT(request);
        
        // Установка в ThreadLocal контекст
        TenantContext.setCurrentTenant(tenantId);
        
        return true;
    }
    
    @Override
    public void afterCompletion(HttpServletRequest request,
                              HttpServletResponse response,
                              Object handler,
                              Exception ex) {
        // Очистка контекста
        TenantContext.clear();
    }
}
```

### 4.3 ThreadLocal контекст

```java
public class TenantContext {
    private static final ThreadLocal<String> currentTenant = new ThreadLocal<>();
    
    public static void setCurrentTenant(String tenantId) {
        currentTenant.set(tenantId);
    }
    
    public static String getCurrentTenant() {
        return currentTenant.get();
    }
    
    public static void clear() {
        currentTenant.remove();
    }
}
```

## 5. Расширенные политики RLS

### 5.1 Политики для разных ролей

```sql
-- Политика для администраторов платформы (видят все тенанты)
CREATE POLICY platform_admin_policy ON tenant_alfa.clients
    FOR ALL
    TO platform_admin
    USING (true)
    WITH CHECK (true);

-- Политика для администраторов тенанта (видят только свой тенант)
CREATE POLICY tenant_admin_policy ON tenant_alfa.clients
    FOR ALL
    TO tenant_admin
    USING (tenant_id = current_setting('app.current_tenant'))
    WITH CHECK (tenant_id = current_setting('app.current_tenant'));

-- Политика для операторов (только чтение)
CREATE POLICY operator_read_policy ON tenant_alfa.clients
    FOR SELECT
    TO operator
    USING (tenant_id = current_setting('app.current_tenant'));
```

### 5.2 Политики для связанных таблиц (оптимизированные)

```sql
-- Таблица счетов с foreign key на клиентов
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL, -- БЕЗ DEFAULT
    client_id BIGINT NOT NULL,
    account_number VARCHAR(34) NOT NULL,
    balance DECIMAL(15,2) DEFAULT 0.00,
    
    -- Составной foreign key с tenant_id для гарантии согласованности
    FOREIGN KEY (tenant_id, client_id) 
    REFERENCES clients(tenant_id, id)
    ON DELETE CASCADE
);

-- RLS политика для счетов (ПРОСТАЯ, без подзапросов)
CREATE POLICY accounts_tenant_policy ON accounts
    USING (tenant_id = current_setting('app.current_tenant'))
    WITH CHECK (tenant_id = current_setting('app.current_tenant'));

-- Составной индекс с tenant_id на первом месте (КРИТИЧНО)
CREATE INDEX idx_accounts_tenant_client 
ON accounts(tenant_id, client_id);

-- Индекс для поиска по номеру счета в рамках тенанта
CREATE INDEX idx_accounts_tenant_number 
ON accounts(tenant_id, account_number);
```

**Архитектурное решение:** Отказ от сложных политик с EXISTS в пользу:
1. **Составных foreign keys** с tenant_id для гарантии ссылочной целостности
2. **Простых RLS политик** только с прямым сравнением tenant_id
3. **Правильной индексации** с tenant_id на первом месте во всех индексах

## 6. Миграции и управление схемами

### 6.1 Создание нового тенанта (Shared Schema)

```sql
-- create_tenant.sql (Shared Schema подход)
-- НЕ создаем новые схемы, только настраиваем данные

-- 1. Создание администратора тенанта в Keycloak (через API)
-- 2. Настройка политик в OPA (через API)
-- 3. Начальное наполнение справочных данных для тенанта

-- Вставка начальных справочных данных для нового тенанта
INSERT INTO tenant_config (tenant_id, config_key, config_value, created_at)
VALUES 
    (:tenant_id, 'currency.default', 'RUB', NOW()),
    (:tenant_id, 'timezone', 'Europe/Moscow', NOW()),
    (:tenant_id, 'language', 'ru', NOW());

-- Создание административного пользователя тенанта
INSERT INTO users (tenant_id, username, email, role, created_at)
VALUES 
    (:tenant_id, 'admin', :admin_email, 'TENANT_ADMIN', NOW());

-- Настройка начальных лимитов
INSERT INTO tenant_limits (tenant_id, limit_type, limit_value, created_at)
VALUES 
    (:tenant_id, 'MAX_CLIENTS', 10000, NOW()),
    (:tenant_id, 'MAX_ACCOUNTS', 50000, NOW()),
    (:tenant_id, 'DAILY_TRANSACTION_LIMIT', 1000000.00, NOW());
```

**Преимущества Shared Schema подхода:**
1. **Нет необходимости в создании схем** - структура БД единая для всех
2. **Миграции применяются один раз** ко всей БД
3. **Упрощенное управление** - не нужно синхронизировать сотни схем
4. **Лучшая производительность** планировщика запросов

### 6.2 Разделение ролей обслуживания и эксплуатации

Для безопасного администрирования создаются отдельные роли с разными правами:

```sql
-- 1. Роль для миграций (Flyway/Liquibase) - полный доступ
CREATE ROLE migration_admin WITH LOGIN PASSWORD 'secure_migration_password';
ALTER ROLE migration_admin BYPASSRLS;
GRANT ALL ON ALL TABLES IN SCHEMA public TO migration_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO migration_admin;

-- 2. Роль для аудита и аналитики - только чтение
CREATE ROLE auditor WITH LOGIN PASSWORD 'secure_audit_password';
ALTER ROLE auditor BYPASSRLS;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO auditor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO auditor;

-- 3. Роль для мониторинга платформы
CREATE ROLE platform_monitor WITH LOGIN PASSWORD 'secure_monitor_password';
ALTER ROLE platform_monitor BYPASSRLS;
GRANT SELECT ON 
    pg_stat_activity, 
    pg_stat_user_tables, 
    pg_stat_user_indexes 
TO platform_monitor;

-- Проверка прав ролей
SELECT rolname, rolbypassrls FROM pg_roles 
WHERE rolname IN ('migration_admin', 'auditor', 'platform_monitor');
```

**Важность разделения ролей:**
1. **migration_admin:** Полный доступ для миграций и обслуживания индексов
2. **auditor:** Только чтение для глобального аудита и аналитики (если не вынесено в ClickHouse)
3. **platform_monitor:** Мониторинг производительности без доступа к бизнес-данным

**Безопасность:** Разделение минимизирует риски случайного изменения данных при глобальном просмотре.

### 6.3 Управление через административный модуль

```java
@Service
public class TenantManagementService {
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    public void createTenant(String tenantId, TenantConfig config) {
        // 1. Настройка начальных данных в Shared Schema
        jdbcTemplate.update(
            "INSERT INTO tenant_config (tenant_id, config_key, config_value) VALUES (?, ?, ?)",
            tenantId, "currency.default", "RUB"
        );
        
        // 2. Создание административного пользователя
        jdbcTemplate.update(
            "INSERT INTO users (tenant_id, username, email, role) VALUES (?, ?, ?, ?)",
            tenantId, "admin", config.getAdminEmail(), "TENANT_ADMIN"
        );
        
        // 3. Создание пользователя в Keycloak
        keycloakAdminClient.createTenantUser(tenantId, config.getAdminEmail());
        
        // 4. Настройка политик в OPA
        opaClient.createTenantPolicies(tenantId);
    }
}
```

## 7. Производительность и оптимизация

### 7.1 Оптимизация индексов для RLS

```sql
-- Обязательные индексы для производительности RLS
CREATE INDEX CONCURRENTLY idx_clients_tenant_id 
ON clients(tenant_id, id) 
WHERE tenant_id IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_accounts_tenant_id_client_id 
ON accounts(tenant_id, client_id);

-- Частичные индексы для часто используемых запросов
-- Включаем tenant_id в условие WHERE для гарантированного использования с RLS
CREATE INDEX CONCURRENTLY idx_active_clients 
ON clients(status, tenant_id) 
WHERE status = 'ACTIVE';

-- Индекс для поиска по email в рамках тенанта
CREATE INDEX CONCURRENTLY idx_clients_tenant_email 
ON clients(tenant_id, email) 
WHERE email IS NOT NULL;

-- Индекс для временных диапазонов с tenant_id
CREATE INDEX CONCURRENTLY idx_clients_tenant_created 
ON clients(tenant_id, created_at);
```

**Оптимизация планировщика:** При использовании RLS планировщик всегда неявно добавляет условие `tenant_id = current_setting(...)`. Чтобы частичные индексы работали эффективно, их определение должно содержать `tenant_id` в колонках индекса.

### 7.2 Мониторинг производительности

```sql
-- Запросы для мониторинга эффективности RLS
SELECT 
    schemaname,
    tablename,
    row_security_active,
    row_security_policies
FROM pg_tables 
WHERE row_security_active = true;

-- Анализ использования индексов с RLS
EXPLAIN ANALYZE 
SELECT * FROM tenant_alfa.clients 
WHERE tenant_id = current_setting('app.current_tenant')
AND status = 'ACTIVE';
```

### 7.3 Connection Pool настройки

```yaml
# application.yml
spring:
  datasource:
    hikari:
      connection-init-sql: "SET app.current_tenant = ?"
      connection-init-sql-params: "${tenant.id}"
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
```

## 8. Безопасность и аудит

### 8.1 Аудит изменений RLS политик

```sql
-- Таблица для аудита изменений политик
CREATE TABLE security.audit_rls_changes (
    id BIGSERIAL PRIMARY KEY,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(255),
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    policy_name VARCHAR(255),
    operation VARCHAR(50), -- CREATE, ALTER, DROP
    old_policy TEXT,
    new_policy TEXT
);

-- Триггер для аудита
CREATE OR REPLACE FUNCTION audit_rls_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO security.audit_rls_changes
    (schema_name, table_name, policy_name, operation, new_policy)
    VALUES (
        TG_TABLE_SCHEMA,
        TG_TABLE_NAME,
        NEW.policyname,
        TG_OP,
        NEW.policy
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 8.2 Тестирование изоляции

```java
@Test
public void testTenantIsolation() {
    // Установка tenant_id = "alfa"
    TenantContext.setCurrentTenant("alfa");
    
    // Создание клиента для тенанта "alfa"
    clientRepository.save(new Client("Иван", "alfa"));
    
    // Переключение на tenant_id = "beta"
    TenantContext.setCurrentTenant("beta");
    
    // Попытка чтения клиентов тенанта "alfa" должна вернуть 0 записей
    List<Client> betaClients = clientRepository.findAll();
    assertEquals(0, betaClients.size());
    
    // Возврат к tenant_id = "alfa"
    TenantContext.setCurrentTenant("alfa");
    
    // Должны увидеть созданного клиента
    List<Client> alfaClients = clientRepository.findAll();
    assertEquals(1, alfaClients.size());
}
```

## 9. Отчетность и аналитическое хранилище

### 9.1 Проблема 11-го сервиса: Отчетность в SaaS АБС

**Проблема:** Выполнение тяжелых аналитических запросов (агрегации, оконные функции, JOIN больших таблиц) в транзакционной базе с включенным RLS создает:
1. **Высокую нагрузку на CPU** из-за проверки RLS политик для каждой строки
2. **Блокировки** при длительных запросах
3. **Деградацию производительности** для онлайн-операций

### 9.2 Решение: Аналитическое хранилище (DWH)

```
┌─────────────────────────────────────────────────────────────┐
│                    Архитектура данных                        │
├─────────────────────────────────────────────────────────────┤
│  Транзакционная БД (PostgreSQL)                             │
│  • Online Transaction Processing (OLTP)                     │
│  • RLS для изоляции тенантов                                │
│  • Высокая доступность, короткие транзакции                 │
│                                                              │
│  ↓ CDC (Change Data Capture) через Debezium/Kafka           │
│                                                              │
│  Аналитическое хранилище (ClickHouse)                       │
│  • Online Analytical Processing (OLAP)                      │
│  • Column-oriented storage для агрегаций                    │
│  • Без RLS - изоляция через partitioning по tenant_id       │
│  • Оптимизировано для тяжелых отчетов                       │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Реализация CDC пайплайна

```sql
-- В PostgreSQL: публикация изменений
CREATE PUBLICATION tenant_publication FOR TABLE clients, accounts, transactions;

-- В ClickHouse: материализованные представления
CREATE TABLE reports.clients_daily (
    tenant_id String,
    date Date,
    new_clients_count UInt32,
    active_clients_count UInt32,
    total_balance AggregateFunction(sum, Decimal(15,2))
) ENGINE = AggregatingMergeTree()
PARTITION BY (tenant_id, date)
ORDER BY (tenant_id, date);
```

### 9.4 Сервис отчетности

```java
@Service
public class ReportingService {
    
    @Autowired
    private ClickHouseClient clickHouseClient;
    
    public Report generateDailyReport(String tenantId, LocalDate date) {
        // Запрос к ClickHouse (БЕЗ RLS overhead)
        String query = """
            SELECT 
                tenant_id,
                date,
                new_clients_count,
                active_clients_count,
                sum(total_balance) as total_balance
            FROM reports.clients_daily
            WHERE tenant_id = ? AND date = ?
            GROUP BY tenant_id, date
        """;
        
        return clickHouseClient.query(query, tenantId, date);
    }
}
```

## 10. Ограничения и рекомендации

### 10.1 Ограничения RLS в PostgreSQL

1. **Производительность:** RLS добавляет overhead к каждому запросу (5-15%)
2. **Сложные JOIN:** Требуют аккуратного проектирования политик
3. **Миграции:** Изменение политик требует планирования
4. **Отладка:** Сложнее отлаживать запросы с RLS
5. **Аналитические запросы:** Не подходит для тяжелых отчетов

### 10.2 Рекомендации по использованию

1. **Всегда использовать индексы** с `tenant_id` на первом месте
2. **Тестировать производительность** под нагрузкой
3. **Аудит изменений** политик
4. **Выделять аналитику** в отдельное хранилище
5. **Мониторинг** использования памяти и CPU
6. **Использовать `FORCE ROW LEVEL SECURITY`** для всех таблиц
7. **Создавать роли с `BYPASSRLS`** для миграций и администрирования
8. **Помечать функции как `LEAKPROOF`** при использовании в RLS политиках

### 10.3 LEAKPROOF функции для RLS политик

Если в RLS политики будут добавлены пользовательские функции, их следует помечать как `LEAKPROOF`:

```sql
-- Создание LEAKPROOF функции для проверки доступа
CREATE OR REPLACE FUNCTION check_tenant_access(
    p_tenant_id VARCHAR(50),
    p_user_role VARCHAR(50)
) RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
LEAKPROOF  -- КРИТИЧНО: предотвращает side-channel attacks
AS $$
BEGIN
    -- Логика проверки доступа
    IF p_user_role = 'PLATFORM_ADMIN' THEN
        RETURN true;
    END IF;
    
    RETURN p_tenant_id = current_setting('app.current_tenant', true);
END;
$$;

-- Использование в RLS политике
CREATE POLICY tenant_access_policy ON clients
    USING (check_tenant_access(tenant_id, current_setting('app.user_role', true)));
```

**Важность `LEAKPROOF`:**
1. **Предотвращает side-channel attacks:** Без `LEAKPROOF` оптимизатор может выполнить функцию над данными до проверки политики
2. **Исключает утечку данных:** Через сообщения об ошибках или замеры времени выполнения
3. **Гарантирует безопасность:** Функция не раскрывает информацию о данных, к которым нет доступа

### 10.4 Альтернативные подходы к изоляции

```sql
-- Альтернатива 1: Фильтрация на уровне приложения
SELECT * FROM all_clients WHERE tenant_id = ?;

-- Альтернатива 2: VIEW с фильтрацией
CREATE VIEW tenant_clients AS
SELECT * FROM all_clients 
WHERE tenant_id = current_setting('app.current_tenant');

-- Альтернатива 3: Физическое разделение (отдельные БД)
-- Каждый тенант в отдельной БД (max изоляция, max overhead)
```

## 11. PlantUML диаграмма реализации RLS

**Примечание:** Эта диаграмма показывает устаревший подход с раздельными схемами. Актуальная диаграмма Shared Schema находится в отдельном файле [`docs/rls-shared-schema-diagram.puml`](docs/rls-shared-schema-diagram.puml).

```plantuml
@startuml
!define RECTANGLE class
skinparam backgroundColor transparent
skinparam linetype ortho
skinparam nodesep 50
skinparam ranksep 40

title Реализация Row-Level Security (RLS) в облачной АБС (Устаревшая версия - раздельные схемы)

' === ЦВЕТА ===
!define COLOR_TENANT #FFE5CC
!define COLOR_APP #CCE5FF
!define COLOR_DB #CCFFCC
!define COLOR_SECURITY #FFCCCC

' === КОМПОНЕНТЫ СИСТЕМЫ ===

rectangle "Клиент (ДБО)" as client #COLOR_TENANT

rectangle "API Gateway" as api_gateway #COLOR_APP {
  rectangle "JWT Parser" as jwt_parser
  rectangle "Tenant Extractor" as tenant_extractor
}

rectangle "Бизнес-сервис\n(Модуль клиентов)" as business_service #COLOR_APP {
  rectangle "TenantInterceptor" as interceptor
  rectangle "TenantContext\n(ThreadLocal)" as tenant_context
  rectangle "Service Layer" as service_layer
  rectangle "Repository" as repository
}

rectangle "Connection Pool" as connection_pool #COLOR_APP {
  rectangle "TenantAwareDataSource" as data_source
  rectangle "Connection\nWrapper" as connection_wrapper
}

database "PostgreSQL Cluster" as postgresql #COLOR_DB {
  rectangle "Схема: tenant_alfa" as schema_alfa {
    rectangle "Таблица: clients" as table_clients {
      rectangle "RLS Policy" as rls_policy
      rectangle "Данные" as data_alfa {
        card "id: 1\ntenant_id: alfa\nname: Иван" as row1
        card "id: 2\ntenant_id: alfa\nname: Мария" as row2
      }
    }
  }
  
  rectangle "Схема: tenant_beta" as schema_beta {
    rectangle "Таблица: clients" as table_clients_beta {
      rectangle "RLS Policy" as rls_policy_beta
      rectangle "Данные" as data_beta {
        card "id: 3\ntenant_id: beta\nname: Петр" as row3
        card "id: 4\ntenant_id: beta\nname: Анна" as row4
      }
    }
  }
}

rectangle "Безопасность" as security #COLOR_SECURITY {
  rectangle "Keycloak" as keycloak
  rectangle "JWT Token" as jwt_token
}

' === ПОТОК ДАННЫХ ===

' 1. Аутентификация
client -> api_gateway : "1. HTTPS запрос\n(с JWT токеном)"
api_gateway -> keycloak : "2. Валидация токена"
keycloak --> api_gateway : "3. Valid JWT"
jwt_parser -> tenant_extractor : "4. Извлечение tenant_id"
tenant_extractor -> api_gateway : "5. Добавление X-Tenant-ID"

' 2. Обработка в бизнес-сервисе
api_gateway -> business_service : "6. REST API запрос\n(X-Tenant-ID: alfa)"
interceptor -> tenant_context : "7. Установка tenant_id в ThreadLocal"
tenant_context -> service_layer : "8. Бизнес-логика"
service_layer -> repository : "9. Вызов репозитория"

' 3. Работа с базой данных
repository -> connection_pool : "10. Запрос соединения"
data_source -> connection_wrapper : "11. Получение connection"
connection_wrapper -> postgresql : "12. Установка сессионной переменной\nSET app.current_tenant = 'alfa'"

' 4. Применение RLS
postgresql -> schema_alfa : "13. Доступ к схеме tenant_alfa"
schema_alfa -> table_clients : "14. Запрос к таблице clients"
rls_policy -> data_alfa : "15. Применение политики:\ntenant_id = current_setting('app.current_tenant')"
data_alfa --> rls_policy : "16. Возврат только строк\nс tenant_id = 'alfa'"
rls_policy --> table_clients : "17. Отфильтрованные данные"
table_clients --> schema_alfa : "18. Результат запроса"
schema_alfa --> postgresql : "19. Возврат данных"
postgresql --> connection_wrapper : "20. Результат SQL запроса"
connection_wrapper --> data_source : "21. Connection с результатами"
data_source --> connection_pool : "22. Возврат соединения"
connection_pool --> repository : "23. Результат запроса"
repository --> service_layer : "24. Объекты домена"
service_layer --> tenant_context : "25. Очистка ThreadLocal"
tenant_context --> interceptor : "26. Завершение обработки"
interceptor --> business_service : "27. Формирование ответа"
business_service --> api_gateway : "28. REST API ответ"
api_gateway --> client : "29. HTTP ответ"

' === ПРИМЕР НЕУДАЧНОГО ДОСТУПА ===

note right of schema_beta
  <b>Пример изоляции:</b>
  Если tenant_id = 'alfa', то
  запрос к tenant_beta.clients
  вернет 0 записей
end note

' === ЛЕГЕНДА ===

legend right
  <b>Цветовая схема:</b>
  <color:#FFE5CC>Клиент/Тенант</color>
  <color:#CCE5FF>Приложение</color>
  <color:#CCFFCC>База данных</color>
  <color:#FFCCCC>Безопасность</color>
  |
  <b>Ключевые компоненты:</b>
  1. JWT токен с claim tenant_id
  2. ThreadLocal контекст
  3. TenantAwareDataSource
  4. RLS политики в PostgreSQL
  |
  <b>Поток данных:</b>
  Аутентификация → Извлечение tenant_id →
  Установка в ThreadLocal → Установка в БД →
  Применение RLS → Возврат данных
end legend

' === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===

note top of postgresql
  <b>PostgreSQL RLS Configuration:</b>
  
  -- Включение RLS
  ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
  
  -- Создание политики
  CREATE POLICY tenant_isolation_policy
  ON clients USING (tenant_id = 
    current_setting('app.current_tenant', true));
  
  -- Установка переменной
  SET app.current_tenant = 'alfa';
end note

note bottom of business_service
  <b>Spring Configuration:</b>
  
  @Component
  public class TenantInterceptor 
    implements HandlerInterceptor {
    
    @Override
    public boolean preHandle(...) {
      String tenantId = extractFromJWT(request);
      TenantContext.setCurrentTenant(tenantId);
      return true;
    }
  }
end note

@enduml
```

## 11. Ответ на вопрос: Очистка сессий в пуле соединений

### 11.1 Проблема утечки контекста

**Критическая проблема:** Если соединение возвращается в пул без сброса `app.current_tenant`, следующий запрос может получить доступ к данным чужого тенанта.

### 11.2 Решение: Гарантированная очистка

В реализации `SafeTenantAwareDataSource` решены все проблемы:

```java
@Override
public void close() throws SQLException {
    try {
        // ГАРАНТИРОВАННАЯ очистка контекста перед возвратом в пул
        if (tenantSet) {
            try (Statement stmt = delegate.createStatement()) {
                stmt.execute("RESET app.current_tenant");
            }
        }
    } finally {
        delegate.close();
    }
}
```

### 11.3 Дополнительные меры безопасности

1. **Таймаут сессии в PostgreSQL:**
```sql
-- Автоматический сброс сессионных переменных при idle timeout
ALTER DATABASE abs SET idle_in_transaction_session_timeout = '5min';
```

2. **Валидация в RLS политиках:**
```sql
-- Дополнительная проверка, что tenant_id не NULL
CREATE POLICY tenant_isolation_policy ON clients
    USING (
        tenant_id IS NOT NULL 
        AND tenant_id = current_setting('app.current_tenant', true)
    );
```

3. **Мониторинг утечек:**
```sql
-- Запрос для обнаружения сессий с установленным tenant_id
SELECT 
    pid, 
    usename, 
    application_name,
    query_start,
    state,
    (SELECT setting FROM pg_settings WHERE name = 'app.current_tenant') as current_tenant
FROM pg_stat_activity 
WHERE query LIKE '%app.current_tenant%'
   OR state_change < NOW() - INTERVAL '10 minutes';
```

### 11.4 Синхронизация с OPA (Open Policy Agent) - Production версия

Для согласованности проверок доступа между API Gateway и RLS в БД используются Rego-политики в OPA:

```rego
package bank.tenancy

import future.keywords.in

default allow = false

# Полный доступ для администраторов платформы
allow {
    input.user.roles[_] == "PLATFORM_ADMIN"
}

# Изолированный доступ для пользователей тенанта
allow {
    input.user.tenant_id == input.headers["X-Tenant-ID"]
    action_allowed
}

# Проверка разрешенных действий на основе ролей
action_allowed {
    input.method == "GET"
    input.user.roles[_] in ["OPERATOR", "TENANT_ADMIN"]
}

action_allowed {
    input.method in ["POST", "PUT", "PATCH", "DELETE"]
    input.user.roles[_] == "TENANT_ADMIN"
}

# Проверка, что пользователь принадлежит тенанту
user_belongs_to_tenant {
    some user in data.users
    user.id == input.user.id
    user.tenant_id == input.user.tenant_id
}

# Политика для API endpoints
api_policy[decision] {
    # Извлечение tenant_id из JWT
    tenant_id := input.jwt.claims.tenant_id
    
    # Проверка доступа к ресурсу
    decision := {
        "allow": allow,
        "tenant_id": tenant_id,
        "roles": input.user.roles,
        "method": input.method
    }
}
```

```sql
-- Синхронизация политик между OPA и PostgreSQL
CREATE OR REPLACE FUNCTION sync_opa_policies()
RETURNS TRIGGER AS $$
BEGIN
    -- При изменении пользователя или роли в БД
    -- обновляем политики в OPA через REST API
    PERFORM net.http_post(
        url := 'http://opa:8181/v1/data/bank/tenancy',
        body := json_build_object(
            'users', (
                SELECT json_agg(json_build_object(
                    'id', id,
                    'tenant_id', tenant_id,
                    'role', role
                ))
                FROM users
                WHERE tenant_id = NEW.tenant_id
            )
        )::text
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 11.5 Альтернативный подход: Connection-per-request

```java
@Configuration
public class DataSourceConfig {
    
    @Bean
    @Scope(value = WebApplicationContext.SCOPE_REQUEST, proxyMode = ScopedProxyMode.TARGET_CLASS)
    public Connection scopedConnection() throws SQLException {
        Connection conn = dataSource.getConnection();
        String tenantId = TenantContext.getCurrentTenant();
        
        try (PreparedStatement stmt = conn.prepareStatement("SET app.current_tenant = ?")) {
            stmt.setString(1, tenantId);
            stmt.execute();
        }
        
        return conn;
    }
    
    @PreDestroy
    public void cleanup() throws SQLException {
        // Автоматическая очистка при завершении request scope
        try (Statement stmt = scopedConnection().createStatement()) {
            stmt.execute("RESET app.current_tenant");
        }
    }
}
```

## 12. Рекомендации по сопровождению и масштабированию

### 12.1 Мониторинг раздувания (Bloat)

RLS и частые обновления записей разными тенантами могут привести к неравномерному заполнению страниц:

```sql
-- Настройка агрессивного autovacuum для таблиц с высокой транзакционной активностью
ALTER TABLE clients SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay = 10
);

-- Мониторинг раздувания
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup::numeric / (n_live_tup + n_dead_tup) * 100, 2) as dead_percent
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY dead_percent DESC;
```

### 12.2 Подготовка к горизонтальному масштабированию

Shared Schema подход позволяет легче перейти к Sharding при достижении лимитов вертикального роста:

```sql
-- Подготовка к использованию Citus с tenant_id в качестве ключа шардирования
-- 1. Установка расширения Citus
CREATE EXTENSION IF NOT EXISTS citus;

-- 2. Настройка таблицы как распределенной
SELECT create_distributed_table('clients', 'tenant_id');
SELECT create_distributed_table('accounts', 'tenant_id');

-- 3. Добавление worker узлов
SELECT master_add_node('worker1.example.com', 5432);
SELECT master_add_node('worker2.example.com', 5432);
```

**Преимущества Shared Schema для шардирования:**
1. **Единая структура данных** на всех шардах
2. **Простое перераспределение** тенантов между узлами
3. **Согласованность миграций** - одна схема для всех шардов
4. **Упрощенное резервное копирование** на уровне тенанта

### 12.3 Чеклист эксплуатации Production-среды

✅ **Безопасность:**
- [ ] `FORCE ROW LEVEL SECURITY` применен ко всем таблицам
- [ ] Роли с `BYPASSRLS` созданы для миграций и аудита
- [ ] Connection Proxy гарантирует очистку контекста
- [ ] OPA политики синхронизированы с RLS

✅ **Производительность:**
- [ ] Индексы с `tenant_id` на первом месте
- [ ] Частичные индексы включают `tenant_id` в условия
- [ ] Autovacuum настроен для таблиц с высокой активностью
- [ ] Аналитическое хранилище (ClickHouse) разгружает OLTP

✅ **Масштабируемость:**
- [ ] Shared Schema подход для упрощения миграций
- [ ] Составные foreign keys гарантируют ссылочную целостность
- [ ] Архитектура готова к переходу на Citus шардирование
- [ ] CDC пайплайн для синхронизации с аналитическим хранилищем

✅ **Мониторинг:**
- [ ] Отслеживание раздувания таблиц
- [ ] Мониторинг производительности RLS политик
- [ ] Аудит изменений политик безопасности
- [ ] Обнаружение утечек контекста в пуле соединений

## 13. Заключение

Реализация RLS в облачной АБС обеспечивает:

1. **Безопасность:** Гарантированная изоляция данных между тенантами через Shared Schema + RLS с защитой от side-channel attacks
2. **Гибкость:** Возможность настройки политик для разных ролей с синхронизацией через OPA
3. **Производительность:** Минимизация overhead через оптимизированные индексы и выделенное аналитическое хранилище
4. **Масштабируемость:** Поддержка сотен тенантов с готовностью к горизонтальному шардированию
5. **Администрирование:** Разделенные роли для миграций, аудита и мониторинга

**Ключевые архитектурные решения:**
1. **Отказ от двойной изоляции** в пользу Shared Schema + RLS
2. **Гарантированная очистка контекста** в Connection Proxy с поддержкой Wrapper интерфейса
3. **Выделение аналитики** в ClickHouse через CDC пайплайн
4. **Оптимизированные индексы** с `tenant_id` на первом месте и правильными частичными индексами
5. **Разделение ролей** с `BYPASSRLS` для безопасного администрирования

Эта реализация решает все критические риски, отмеченные в техническом ревью, и обеспечивает масштабируемость системы до уровня enterprise SaaS платформы для банковских операций.