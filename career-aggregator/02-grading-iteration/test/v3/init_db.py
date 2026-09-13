# init_db.py
import sqlite3
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = 'vacancies.db'

def table_exists(cursor, table_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Проверка структуры базы данных...")
    
    # ========== 1. Справочники ==========
    if not table_exists(cursor, 'competency_categories'):
        print("  Создание таблицы: competency_categories")
        cursor.execute('''
            CREATE TABLE competency_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                parent_id INTEGER,
                description TEXT
            )
        ''')
    
    if not table_exists(cursor, 'competencies'):
        print("  Создание таблицы: competencies")
        cursor.execute('''
            CREATE TABLE competencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                display_name TEXT,
                description TEXT,
                is_key_senior BOOLEAN DEFAULT 0
            )
        ''')
    
    if not table_exists(cursor, 'competency_variants'):
        print("  Создание таблицы: competency_variants")
        cursor.execute('''
            CREATE TABLE competency_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competency_id INTEGER,
                variant_name TEXT,
                FOREIGN KEY(competency_id) REFERENCES competencies(id)
            )
        ''')
    
    if not table_exists(cursor, 'competency_category_link'):
        print("  Создание таблицы: competency_category_link")
        cursor.execute('''
            CREATE TABLE competency_category_link (
                competency_id INTEGER,
                category_id INTEGER,
                PRIMARY KEY (competency_id, category_id),
                FOREIGN KEY(competency_id) REFERENCES competencies(id),
                FOREIGN KEY(category_id) REFERENCES competency_categories(id)
            )
        ''')
    
    # ========== 2. Сырые данные ==========
    if not table_exists(cursor, 'vacancies'):
        print("  Создание таблицы: vacancies")
        cursor.execute('''
            CREATE TABLE vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hh_id TEXT UNIQUE,
                hash TEXT UNIQUE,
                name TEXT,
                requirement TEXT,
                responsibility TEXT,
                employer_name TEXT,
                city TEXT,
                salary_from INTEGER,
                salary_to INTEGER,
                salary_currency TEXT,
                salary_normalized INTEGER,
                is_remote BOOLEAN DEFAULT 0,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    if not table_exists(cursor, 'raw_competencies'):
        print("  Создание таблицы: raw_competencies")
        cursor.execute('''
            CREATE TABLE raw_competencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                source_vacancy_id INTEGER,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    # ========== 3. Продуктовые таблицы ==========
    if not table_exists(cursor, 'parsed_vacancies'):
        print("  Создание таблицы: parsed_vacancies")
        cursor.execute('''
            CREATE TABLE parsed_vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hh_id TEXT UNIQUE,
                job_title TEXT,
                overall_level TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                currency TEXT,
                is_remote BOOLEAN DEFAULT 0,
                requirement_raw TEXT,
                responsibility_raw TEXT,
                url TEXT,
                status TEXT DEFAULT 'pending',
                processed_at TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    if not table_exists(cursor, 'parsed_requirements'):
        print("  Создание таблицы: parsed_requirements")
        cursor.execute('''
            CREATE TABLE parsed_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parsed_vacancy_id INTEGER,
                competency_id INTEGER,
                required_level TEXT,
                is_mandatory BOOLEAN DEFAULT 0,
                confidence REAL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
                evidence TEXT,
                FOREIGN KEY(parsed_vacancy_id) REFERENCES parsed_vacancies(id),
                FOREIGN KEY(competency_id) REFERENCES competencies(id)
            )
        ''')
    
    # 12. Неизвестные компетенции (для аналитики)
    if not table_exists(cursor, 'unknown_competencies'):
        print("  Создание таблицы: unknown_competencies")
        cursor.execute('''
            CREATE TABLE unknown_competencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                vacancy_hh_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    # ========== 4. Индексы ==========
    print("  Создание индексов...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_vacancies_hh_id ON parsed_vacancies(hh_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_vacancies_status ON parsed_vacancies(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_vacancies_level ON parsed_vacancies(overall_level)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_requirements_vacancy ON parsed_requirements(parsed_vacancy_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_requirements_competency ON parsed_requirements(competency_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_hh_id ON vacancies(hh_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_competencies_name ON raw_competencies(name)')
    
    conn.commit()
    conn.close()
    
    print("\n✅ База данных инициализирована. Все таблицы проверены/созданы.")
    print("   Справочники: competency_categories, competencies, competency_variants, competency_category_link")
    print("   Сырые данные: vacancies, raw_competencies")
    print("   Продуктовые: parsed_vacancies, parsed_requirements")

if __name__ == "__main__":
    init_database()