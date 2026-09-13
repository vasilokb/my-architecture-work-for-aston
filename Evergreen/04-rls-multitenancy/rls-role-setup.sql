-- SQL-скрипт для настройки ролевой модели в облачной АБС с RLS
-- Версия: 1.0 Production-ready
-- Назначение: Создание ролей для безопасной эксплуатации многотенантной системы

-- ============================================================================
-- 1. ОСНОВНЫЕ РОЛИ ДЛЯ ЭКСПЛУАТАЦИИ
-- ============================================================================

-- 1.1 Роль для миграций (Flyway/Liquibase) - полный доступ с BYPASSRLS
CREATE ROLE migration_admin WITH 
    LOGIN 
    PASSWORD 'secure_migration_password_123!'  -- ЗАМЕНИТЬ в production!
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 10
    VALID UNTIL 'infinity';

-- Включение BYPASSRLS для обхода политик RLS при миграциях
ALTER ROLE migration_admin BYPASSRLS;

-- 1.2 Роль для сервисного пользователя (приложение)
CREATE ROLE service_user WITH 
    LOGIN 
    PASSWORD 'secure_service_password_456!'  -- ЗАМЕНИТЬ в production!
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 100
    VALID UNTIL 'infinity';

-- 1.3 Роль для аудита - только чтение с BYPASSRLS
CREATE ROLE read_only_auditor WITH 
    LOGIN 
    PASSWORD 'secure_audit_password_789!'  -- ЗАМЕНИТЬ в production!
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 5
    VALID UNTIL 'infinity';

ALTER ROLE read_only_auditor BYPASSRLS;

-- 1.4 Роль для мониторинга платформы
CREATE ROLE platform_monitor WITH 
    LOGIN 
    PASSWORD 'secure_monitor_password_012!'  -- ЗАМЕНИТЬ в production!
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT 3
    VALID UNTIL 'infinity';

ALTER ROLE platform_monitor BYPASSRLS;

-- ============================================================================
-- 2. ПРАВА ДОСТУПА К СХЕМАМ И ТАБЛИЦАМ
-- ============================================================================

-- 2.1 Права для migration_admin (полный доступ)
GRANT ALL ON ALL TABLES IN SCHEMA public TO migration_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO migration_admin;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO migration_admin;
GRANT ALL ON ALL PROCEDURES IN SCHEMA public TO migration_admin;

-- Права на будущие объекты
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO migration_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO migration_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO migration_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON PROCEDURES TO migration_admin;

-- 2.2 Права для service_user (ограниченный доступ)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO service_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_user;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO service_user;

-- Права на будущие объекты для service_user
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT USAGE ON SEQUENCES TO service_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT EXECUTE ON FUNCTIONS TO service_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT EXECUTE ON PROCEDURES TO service_user;

-- 2.3 Права для read_only_auditor (только чтение)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only_auditor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO read_only_auditor;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO read_only_auditor;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT ON TABLES TO read_only_auditor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT USAGE ON SEQUENCES TO read_only_auditor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT EXECUTE ON FUNCTIONS TO read_only_auditor;

-- 2.4 Права для platform_monitor (мониторинг)
-- Доступ к системным представлениям для мониторинга
GRANT pg_monitor TO platform_monitor;
GRANT SELECT ON 
    pg_stat_activity,
    pg_stat_user_tables,
    pg_stat_user_indexes,
    pg_stat_database,
    pg_locks,
    pg_stat_bgwriter
TO platform_monitor;

-- ============================================================================
-- 3. НАСТРОЙКА БЕЗОПАСНОСТИ И АТРИБУТОВ
-- ============================================================================

-- 3.1 Ограничение доступа к чувствительным таблицам
REVOKE ALL ON TABLE security.audit_rls_changes FROM service_user, read_only_auditor, platform_monitor;
GRANT SELECT ON TABLE security.audit_rls_changes TO migration_admin, read_only_auditor;

-- 3.2 Настройка параметров подключения для service_user
-- Ограничение времени выполнения запросов
ALTER ROLE service_user SET statement_timeout = '30s';
-- Ограничение времени простоя в транзакции
ALTER ROLE service_user SET idle_in_transaction_session_timeout = '5min';
-- Принудительное применение RLS (дополнительная защита)
ALTER ROLE service_user SET row_security = force;

-- 3.3 Настройка параметров для migration_admin
-- Отключение ограничений для миграций
ALTER ROLE migration_admin SET statement_timeout = '10min';
ALTER ROLE migration_admin SET lock_timeout = '1min';

-- 3.4 Настройка параметров для аудитора
ALTER ROLE read_only_auditor SET statement_timeout = '5min';
ALTER ROLE read_only_auditor SET work_mem = '64MB';

-- ============================================================================
-- 4. СОЗДАНИЕ СЛУЖЕБНЫХ СХЕМ ДЛЯ АУДИТА И МОНИТОРИНГА
-- ============================================================================

-- 4.1 Схема для аудита безопасности
CREATE SCHEMA IF NOT EXISTS security;
GRANT USAGE ON SCHEMA security TO migration_admin, read_only_auditor;
REVOKE ALL ON SCHEMA security FROM service_user, platform_monitor;

-- 4.2 Схема для мониторинга
CREATE SCHEMA IF NOT EXISTS monitoring;
GRANT USAGE ON SCHEMA monitoring TO migration_admin, platform_monitor;
REVOKE ALL ON SCHEMA monitoring FROM service_user, read_only_auditor;

-- ============================================================================
-- 5. ПРОВЕРКА НАСТРОЙКИ РОЛЕЙ
-- ============================================================================

-- 5.1 Проверка атрибутов BYPASSRLS
SELECT 
    rolname,
    rolbypassrls as bypass_rls,
    rolcanlogin as can_login,
    rolconnlimit as conn_limit
FROM pg_roles 
WHERE rolname IN ('migration_admin', 'service_user', 'read_only_auditor', 'platform_monitor')
ORDER BY rolname;

-- 5.2 Проверка прав доступа к таблицам
SELECT 
    grantee,
    table_schema,
    table_name,
    string_agg(privilege_type, ', ') as privileges
FROM information_schema.role_table_grants 
WHERE grantee IN ('migration_admin', 'service_user', 'read_only_auditor', 'platform_monitor')
    AND table_schema = 'public'
GROUP BY grantee, table_schema, table_name
ORDER BY grantee, table_name;

-- 5.3 Проверка параметров ролей
SELECT 
    rolname,
    setconfig as role_settings
FROM pg_roles r
LEFT JOIN pg_db_role_setting rs ON r.oid = rs.setrole
WHERE rolname IN ('migration_admin', 'service_user', 'read_only_auditor', 'platform_monitor')
ORDER BY rolname;

-- ============================================================================
-- 6. ИНСТРУКЦИИ ПО БЕЗОПАСНОСТИ ДЛЯ PRODUCTION
-- ============================================================================

/*
ИНСТРУКЦИЯ ПО РАЗВЕРТЫВАНИЮ:

1. ПЕРЕД ВЫПОЛНЕНИЕМ СКРИПТА:
   - ЗАМЕНИТЕ все пароли на безопасные случайные пароли
   - Сохраните пароли в secure vault (Hashicorp Vault, AWS Secrets Manager и т.д.)
   - Настройте доступ к vault для приложения и администраторов

2. ПОСЛЕ ВЫПОЛНЕНИЯ СКРИПТА:
   - Проверьте подключение каждой роли с соответствующим паролем
   - Убедитесь, что service_user не может обходить RLS политики
   - Проверьте, что migration_admin может выполнять миграции
   - Протестируйте доступ read_only_auditor только на чтение

3. РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ:
   - Регулярно ротируйте пароли (каждые 90 дней)
   - Используйте SSL/TLS для всех подключений к БД
   - Настройте firewall правила для ограничения доступа к порту PostgreSQL
   - Включите логирование всех попыток неудачного входа
   - Регулярно проводите аудит прав доступа

4. МОНИТОРИНГ:
   - Настройте алерты на множественные неудачные попытки входа
   - Мониторьте использование BYPASSRLS ролей
   - Отслеживайте длительные транзакции от service_user
   - Контролируйте создание новых объектов migration_admin
*/

-- ============================================================================
-- 7. КОМАНДЫ ДЛЯ БЫСТРОЙ ПРОВЕРКИ
-- ============================================================================

/*
-- Проверка подключения service_user (должен видеть только данные своего тенанта)
SET app.current_tenant = 'test_tenant';
SELECT * FROM clients LIMIT 5;

-- Проверка подключения migration_admin (должен видеть все данные)
SELECT COUNT(*) as total_clients FROM clients;
SELECT COUNT(DISTINCT tenant_id) as total_tenants FROM clients;

-- Проверка подключения read_only_auditor (только чтение)
SELECT * FROM clients WHERE tenant_id = 'test_tenant' LIMIT 5;

-- Попытка записи от read_only_auditor (должна завершиться ошибкой)
-- INSERT INTO clients (tenant_id, name) VALUES ('test', 'should_fail');
*/

-- ============================================================================
-- КОНЕЦ СКРИПТА
-- ============================================================================

COMMENT ON SCHEMA public IS 'Основная схема для многотенантной АБС с RLS';
COMMENT ON ROLE migration_admin IS 'Роль для выполнения миграций с полным доступом и BYPASSRLS';
COMMENT ON ROLE service_user IS 'Сервисная роль приложения с ограниченным доступом через RLS';
COMMENT ON ROLE read_only_auditor IS 'Роль для аудита с доступом только на чтение и BYPASSRLS';
COMMENT ON ROLE platform_monitor IS 'Роль для мониторинга производительности платформы';