import os
import sys
import sqlite3
import re
from sentence_transformers import SentenceTransformer, util

# Переключаемся в папку со скриптом
os.chdir(os.path.dirname(os.path.abspath(__file__)))

conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

def clear_tables():
    print("0. Очищаем таблицы от старых данных...")
    cursor.execute('DELETE FROM competency_category_link')
    cursor.execute('DELETE FROM competency_variants')
    cursor.execute('DELETE FROM competencies')
    cursor.execute('DELETE FROM competency_categories')
    conn.commit()
    print("   Таблицы очищены")

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_best_canonical_name(names):
    if not names:
        return None
    placeholders = ','.join(['?'] * len(names))
    cursor.execute(f'''
        SELECT name, COUNT(*) as cnt 
        FROM raw_competencies 
        WHERE name IN ({placeholders})
        GROUP BY name
    ''', names)
    freq = {row[0]: row[1] for row in cursor.fetchall()}
    def sort_key(name):
        return (-freq.get(name, 0), -len(name), name)
    return max(names, key=sort_key)

def categorize_competency_multi(name):
    name_lower = name.lower()
    found_categories = []
    
    categories = {
        'AI & Machine Learning': [
            'ai', 'artificial intelligence', 'ml', 'machine learning', 'llm', 
            'large language model', 'nlp', 'natural language processing', 
            'computer vision', 'cv', 'generative ai', 'генеративный ии',
            'rag', 'retrieval augmented generation', 'prompt engineering',
            'langchain', 'llamaindex', 'vector database', 'векторная база данных',
            'embedding', 'нейросеть', 'neural network', 'gpt', 'bert', 'transformer',
            'pytorch', 'tensorflow', 'keras', 'sklearn', 'scikit-learn',
            'data science', 'анализ данных', 'model training', 'обучение модели'
        ],
        'Design (Нотации)': [
            'bpmn', 'uml', 'epc', 'idef', 'c4', 'archimate',
            'моделирование', 'диаграммы', 'нотация'
        ],
        'UI & Prototyping': [
            'figma', 'axure', 'balsamiq', 'прототип', 'mockup',
            'прототипирование', 'ui', 'ux', 'интерфейс'
        ],
        'Methodologies': [
            'agile', 'scrum', 'kanban', 'waterfall', 'гибкие'
        ],
        'DevOps & CI/CD': [
            'ci/cd', 'jenkins', 'gitlab ci', 'github actions', 'teamcity',
            'pipeline', 'devops', 'continuous integration', 'continuous delivery',
            'docker', 'kubernetes', 'k8s', 'контейнеризация', 'container'
        ],
        'Development (Languages)': [
            'python', 'java', 'javascript', 'typescript', 'go', 'golang',
            'c#', 'csharp', 'php', 'ruby', 'bash', 'shell', 'kotlin',
            'swift', 'rust', 'scala'
        ],
        'Tools (Task & Doc)': [
            'jira', 'confluence', 'trello', 'youtrack', 'notion', 'slack',
            'asana', 'monday', 'basecamp'
        ],
        'Tools (Code & Repo)': [
            'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial'
        ],
        'Data (OLTP)': [
            'postgresql', 'postgres', 'mysql', 'oracle', 'mssql', 'sql server',
            'plsql', 't-sql', 'база данных', 'реляционная', 'oltp'
        ],
        'Data (OLAP & BI)': [
            'clickhouse', 'dwh', 'data warehouse', 'etl', 'data modeling',
            'хранилище данных', 'витрина данных', 'tableau', 'power bi',
            'superset', 'looker', 'bi', 'аналитика', 'olap'
        ],
        'Data (NoSQL)': [
            'mongodb', 'cassandra', 'redis', 'elasticsearch', 'neo4j',
            'dynamodb', 'couchbase', 'nosql', 'нереляционная'
        ],
        'Data Formats': [
            'json', 'xml', 'yaml', 'avro', 'parquet', 'protobuf',
            'структура данных', 'формат данных', 'csv'
        ],
        'Integration (API)': [
            'api', 'rest', 'soap', 'graphql', 'grpc', 'веб-сервис'
        ],
        'Integration (Events)': [
            'kafka', 'rabbitmq', 'activemq', 'webhooks', 'message broker',
            'брокер сообщений', 'event', 'события'
        ],
        'API Tools': [
            'swagger', 'openapi', 'postman', 'soapui', 'insomnia'
        ],
        'Requirements': [
            'use case', 'user story', 'bdd', 'specification', 'требования',
            'анализ требований', 'brd', 'frd', 'backlog', 'user story mapping',
            'сбор требований', 'documentation requirements'
        ],
        'Architecture': [
            'microservices', 'soa', 'event-driven', 'serverless', 'monolith',
            'микросервисы', 'архитектура'
        ],
        'Security': [
            'oauth2', 'jwt', 'saml', 'rbac', 'abac', 'tls', 'шифрование',
            'authentication', 'authorization', 'security', 'безопасность',
            'ssl', 'https', 'cors'
        ]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', name_lower):
                found_categories.append(category)
                break
    
    return found_categories

def normalize_competencies():
    clear_tables()
    
    print("1. Загружаем сырые компетенции...")
    cursor.execute('SELECT DISTINCT name FROM raw_competencies')
    raw_skills = [row[0] for row in cursor.fetchall()]
    print(f"   Уникальных сырых навыков: {len(raw_skills)}")
    
    if not raw_skills:
        print("   Нет навыков для нормализации")
        return
    
    print("2. Нормализуем текст...")
    normalized_skills = [normalize_text(s) for s in raw_skills]
    
    print("3. Генерируем эмбеддинги и кластеризуем...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(normalized_skills, convert_to_tensor=True)
    similarity_matrix = util.cos_sim(embeddings, embeddings)
    
    used = set()
    clusters = []
    threshold = 0.65
    
    for i in range(len(raw_skills)):
        if i in used:
            continue
        cluster = [i]
        used.add(i)
        for j in range(i + 1, len(raw_skills)):
            if j in used:
                continue
            if similarity_matrix[i][j] > threshold:
                cluster.append(j)
                used.add(j)
        clusters.append([raw_skills[idx] for idx in cluster])
    
    print(f"   Сформировано кластеров: {len(clusters)}")
    
    # Создаём категории
    categories = {}
    category_names = [
        'AI & Machine Learning',
        'Design (Нотации)',
        'UI & Prototyping',
        'Methodologies',
        'DevOps & CI/CD',
        'Development (Languages)',
        'Tools (Task & Doc)',
        'Tools (Code & Repo)',
        'Data (OLTP)',
        'Data (OLAP & BI)',
        'Data (NoSQL)',
        'Data Formats',
        'Integration (API)',
        'Integration (Events)',
        'API Tools',
        'Requirements',
        'Architecture',
        'Security'
    ]
    for cat_name in category_names:
        cursor.execute('INSERT OR IGNORE INTO competency_categories (name, description) VALUES (?, ?)', (cat_name, ''))
        cursor.execute('SELECT id FROM competency_categories WHERE name = ?', (cat_name,))
        categories[cat_name] = cursor.fetchone()[0]
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competency_category_link (
            competency_id INTEGER,
            category_id INTEGER,
            PRIMARY KEY (competency_id, category_id)
        )
    ''')
    
    print("4. Сохраняем нормализованные компетенции...")
    cursor.execute('DELETE FROM competency_category_link')
    cursor.execute('DELETE FROM competency_variants')
    cursor.execute('DELETE FROM competencies')
    
    saved_count = 0
    for cluster in clusters:
        if not cluster:
            continue
        
        canonical = get_best_canonical_name(cluster)
        if not canonical:
            canonical = cluster[0]
        
        all_categories = set()
        for name in cluster:
            for cat in categorize_competency_multi(name):
                all_categories.add(cat)
        
        if not all_categories:
            continue
        
        cursor.execute('''
            INSERT INTO competencies (name, display_name, description)
            VALUES (?, ?, ?)
        ''', (canonical, canonical, f'Варианты: {", ".join(cluster[:5])}'))
        comp_id = cursor.lastrowid
        saved_count += 1
        
        for cat_name in all_categories:
            category_id = categories.get(cat_name)
            if category_id:
                cursor.execute('''
                    INSERT INTO competency_category_link (competency_id, category_id)
                    VALUES (?, ?)
                ''', (comp_id, category_id))
        
        for variant in cluster:
            if variant != canonical:
                cursor.execute('''
                    INSERT INTO competency_variants (competency_id, variant_name)
                    VALUES (?, ?)
                ''', (comp_id, variant))
    
    conn.commit()
    print(f"   Сохранено компетенций: {saved_count}")
    
    print("\n5. Анализ пропущенных навыков...")
    uncategorized_examples = []
    for cluster in clusters:
        all_categories = set()
        for name in cluster:
            for cat in categorize_competency_multi(name):
                all_categories.add(cat)
        if not all_categories:
            uncategorized_examples.extend(cluster[:2])
    
    if uncategorized_examples:
        print(f"   Примеры навыков без категории (первые 30):")
        for skill in uncategorized_examples[:30]:
            print(f"      - {skill}")
    else:
        print("   Все навыки получили категории")
    
    print("\n6. Компетенции по категориям:")
    cursor.execute('''
        SELECT c.name, COUNT(l.competency_id)
        FROM competency_categories c
        LEFT JOIN competency_category_link l ON c.id = l.category_id
        GROUP BY c.id
        ORDER BY c.name
    ''')
    for cat_name, count in cursor.fetchall():
        if count > 0:
            print(f"      {cat_name}: {count}")

if __name__ == "__main__":
    normalize_competencies()