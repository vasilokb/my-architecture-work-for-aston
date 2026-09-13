import requests
import json
import time
import sqlite3
import hashlib
import re
from math import ceil

import os
API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

PROFILE_ID = 4

# НАВЫКИ КАНДИДАТА (задаются консультантом)
CANDIDATE_SKILLS = ["BPMN", "UML", "SQL", "Jira"]

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text)

# 1. База данных
conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancies (
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
        url TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancy_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER,
        vacancy_id INTEGER,
        match_score INTEGER,
        missing_skills TEXT,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(profile_id, vacancy_id)
    )
''')
conn.commit()

print("База данных создана")

def compute_vacancy_hash(vacancy):
    content = vacancy['name'] + " " + (vacancy['snippet'].get('requirement') or "") + " " + (vacancy['snippet'].get('responsibility') or "")
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# 2. Получаем вакансии из HH.ru
print("1. Получаем вакансии из HH.ru...")
resp = requests.get("https://api.hh.ru/vacancies?text=NAME:системный+аналитик&per_page=100")
data = resp.json()
vacancies = data['items']
total_found = data['found']

print(f"2. Всего найдено на HH.ru: {total_found} вакансий")
print(f"3. Загружено за раз: {len(vacancies)} вакансий")

# 3. Сохраняем в базу
print("4. Сохраняем вакансии в базу...")
saved_count = 0
skipped_count = 0

for vac in vacancies:
    hh_id = vac['id']
    name = clean_text(vac['name'])
    req = clean_text(vac['snippet'].get('requirement') or "")
    resp_text = clean_text(vac['snippet'].get('responsibility') or "")
    hash_val = compute_vacancy_hash(vac)
    
    employer_name = vac['employer']['name'] if vac.get('employer') else "Не указано"
    
    city = "Не указан"
    if vac.get('area') and vac['area'].get('name'):
        city = vac['area']['name']
    
    salary_from = None
    salary_to = None
    salary_currency = None
    if vac.get('salary'):
        salary_from = vac['salary'].get('from')
        salary_to = vac['salary'].get('to')
        salary_currency = vac['salary'].get('currency')
    
    url = vac.get('alternate_url', '')
    
    try:
        cursor.execute('''
            INSERT INTO vacancies (
                hh_id, hash, name, requirement, responsibility, 
                employer_name, city, salary_from, salary_to, salary_currency, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (hh_id, hash_val, name, req, resp_text, employer_name, city, salary_from, salary_to, salary_currency, url))
        saved_count += 1
    except sqlite3.IntegrityError:
        skipped_count += 1

conn.commit()
print(f"5. Сохранено новых вакансий: {saved_count}")
print(f"6. Пропущено (уже были в БД): {skipped_count}")

# 4. Получаем новые вакансии для профиля
cursor.execute('''
    SELECT v.id, v.requirement, v.responsibility 
    FROM vacancies v
    LEFT JOIN vacancy_history vh ON v.id = vh.vacancy_id AND vh.profile_id = ?
    WHERE vh.id IS NULL
''', (PROFILE_ID,))
db_vacancies = cursor.fetchall()
print(f"7. Новых вакансий к обработке для профиля {PROFILE_ID}: {len(db_vacancies)}")

if len(db_vacancies) == 0:
    print("Нет новых вакансий. Выход.")
    conn.close()
    exit()

# 5. Обрабатываем пачками
batch_size = 15
batches = ceil(len(db_vacancies) / batch_size)

url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

all_results = []
total_time = 0
candidate_skills_str = ", ".join(CANDIDATE_SKILLS)

for batch_num in range(batches):
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, len(db_vacancies))
    batch = db_vacancies[start_idx:end_idx]
    
    print(f"\n8.{batch_num + 1} Обработка пачки {batch_num + 1}/{batches} ({len(batch)} вакансий)...")
    
    batch_text = ""
    vac_ids = []
    for idx, vac in enumerate(batch, 1):
        vac_id, req, resp_text = vac
        vac_ids.append(vac_id)
        batch_text += f"\n=== Вакансия {idx} ===\n"
        batch_text += f"Требования: {req}\n"
        batch_text += f"Обязанности: {resp_text}\n"
    
    prompt = f"""
Ты оцениваешь вакансии для системного аналитика.

Для каждой вакансии извлеки ВСЕ профессиональные навыки, которые требуются в вакансии (из требований и обязанностей).

Верни JSON массив. Пример:
[
  {{"vacancy_skills": ["BPMN", "REST", "SQL", "Docker", "Kafka", "UML", "Confluence"]}},
  {{"vacancy_skills": ["Python", "Django", "PostgreSQL"]}}
]

Вакансии:
{batch_text}
"""
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Ты оцениваешь вакансии. Отвечай ТОЛЬКО JSON массивом. Без пояснений."},
            {"role": "user", "content": prompt}
        ]
    }
    
    start = time.time()
    response = requests.post(url, headers=headers, json=payload)
    end = time.time()
    elapsed = end - start
    total_time += elapsed
    
    result = response.json()
    llm_response = result['choices'][0]['message']['content']
    print(f"    Ответ LLM: {llm_response[:150]}...")
    print(f"    Время: {elapsed:.2f}с")
    
    try:
        json_match = re.search(r'\[[\s\S]*\]', llm_response)
        if json_match:
            llm_response = json_match.group(0)
        scores_data = json.loads(llm_response)
        
        candidate_set = set(CANDIDATE_SKILLS)
        
        for idx, vac_id in enumerate(vac_ids):
            if idx < len(scores_data):
                vacancy_skills = scores_data[idx].get('vacancy_skills', [])
                vacancy_set = set(vacancy_skills)
                
                # Считаем match_score сами
                matched = candidate_set & vacancy_set
                total_skills = len(vacancy_set) if vacancy_set else 1
                score = int((len(matched) / total_skills) * 100)
                
                # Находим, чего не хватает
                missing = list(vacancy_set - candidate_set)
                missing_json = json.dumps(missing, ensure_ascii=False)
            else:
                score = 0
                missing_json = "[]"
            
            try:
                cursor.execute('''
                    INSERT INTO vacancy_history (profile_id, vacancy_id, match_score, missing_skills)
                    VALUES (?, ?, ?, ?)
                ''', (PROFILE_ID, vac_id, score, missing_json))
                conn.commit()
                all_results.append({'id': vac_id, 'score': score, 'missing': missing})
            except sqlite3.IntegrityError:
                print(f"    Вакансия {vac_id} уже в истории")
                
    except json.JSONDecodeError as e:
        print(f"    Ошибка парсинга JSON: {e}")
        for vac_id in vac_ids:
            try:
                cursor.execute('''
                    INSERT INTO vacancy_history (profile_id, vacancy_id, match_score, missing_skills)
                    VALUES (?, ?, ?, ?)
                ''', (PROFILE_ID, vac_id, 0, "[]"))
                conn.commit()
                all_results.append({'id': vac_id, 'score': 0, 'missing': []})
            except sqlite3.IntegrityError:
                pass

# 6. Вывод результатов
print("\n" + "="*80)
print(f"РЕЗУЛЬТАТЫ ПОИСКА ДЛЯ ПРОФИЛЯ {PROFILE_ID}")
print(f"Навыки кандидата: {', '.join(CANDIDATE_SKILLS)}")
print("="*80)

cursor.execute('''
    SELECT v.name, v.employer_name, v.city, v.salary_from, v.salary_to, 
           v.salary_currency, v.url, vh.match_score, vh.missing_skills, v.requirement
    FROM vacancies v
    JOIN vacancy_history vh ON v.id = vh.vacancy_id
    WHERE vh.profile_id = ?
    ORDER BY vh.match_score DESC
''', (PROFILE_ID,))
results = cursor.fetchall()

for i, row in enumerate(results, 1):
    name, employer, city, salary_from, salary_to, currency, url, score, missing_json, req = row
    
    req = clean_text(req)
    
    try:
        missing = json.loads(missing_json) if missing_json else []
    except:
        missing = []
    
    salary_str = "Не указана"
    if salary_from or salary_to:
        if salary_from and salary_to:
            salary_str = f"{salary_from:,} - {salary_to:,} {currency}".replace(',', ' ')
        elif salary_from:
            salary_str = f"от {salary_from:,} {currency}".replace(',', ' ')
        elif salary_to:
            salary_str = f"до {salary_to:,} {currency}".replace(',', ' ')
    
    print(f"\n{i}. {score}% - {name}")
    print(f"   Компания: {employer}")
    print(f"   Город: {city}")
    print(f"   Зарплата: {salary_str}")
    print(f"   Ссылка: {url}")
    if missing:
        print(f"   ❌ Кандидату не хватает: {', '.join(missing)}")
    else:
        print(f"   ✅ У кандидата есть все требуемые навыки")
    print(f"   Требования: {req[:150]}..." if len(req) > 150 else f"   Требования: {req}")
    print("-" * 80)

print(f"\nСтатистика:")
print(f"  Обработано вакансий для профиля {PROFILE_ID}: {len(results)}")
print(f"  Общее время: {total_time:.2f} секунд")

conn.close()