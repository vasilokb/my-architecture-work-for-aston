import os
import sys
import requests
import json
import sqlite3
import hashlib
import re
import time
from math import ceil

# Переключаемся в папку со скриптом
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import os
API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# ============================================================
# НАСТРОЙКИ (все параметры здесь)
# ============================================================
CONFIG = {
    'max_tokens_per_batch': 25000,           # макс токенов на пачку
    'max_vacancies_per_batch': 8,            # макс вакансий в пачке
    'rate_limit_requests_per_minute': 20,    # лимит запросов в минуту
    'retry_attempts': 5,                     # попыток при ошибке
    'retry_base_delay': 5,                   # базовая задержка между попытками (сек)
    'delay_between_batches': 3,              # задержка между пачками (сек)
    'clear_raw_before_start': True,          # очищать raw_competencies перед запуском
    'system_overhead_tokens': 1000,          # токены на промпт и примеры
    'request_timeout': 120                   # таймаут запроса к API
}

# ============================================================
# ПОДКЛЮЧЕНИЕ К БД
# ============================================================
conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

# ============================================================
# RATE LIMITER
# ============================================================
class RateLimiter:
    def __init__(self, requests_per_minute):
        self.interval = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.interval:
            wait_time = self.interval - time_since_last
            print(f"      Rate limit: ждём {wait_time:.1f} сек")
            time.sleep(wait_time)
        self.last_request_time = time.time()

rate_limiter = RateLimiter(CONFIG['rate_limit_requests_per_minute'])

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text)

def compute_vacancy_hash(vacancy):
    content = vacancy['name'] + " " + (vacancy['snippet'].get('requirement') or "") + " " + (vacancy['snippet'].get('responsibility') or "")
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def count_tokens(text):
    return len(text) // 4

def clear_raw_competencies():
    """Очищает только сырые компетенции"""
    print("0. Очистка таблицы raw_competencies...")
    cursor.execute('DELETE FROM raw_competencies')
    conn.commit()
    print("   Таблица raw_competencies очищена")

# ============================================================
# ЗАГРУЗКА ВАКАНСИЙ ИЗ HH.ru
# ============================================================
def fetch_all_vacancies():
    print("1. Загружаем все вакансии из HH.ru...")
    all_vacancies = []
    page = 0
    per_page = 100
    
    max_retries = 5
    while True:
        url = f"https://api.hh.ru/vacancies?text=NAME:системный+аналитик&per_page={per_page}&page={page}"
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                items = data.get('items', [])
                break
            except Exception as e:
                wait = 2 ** attempt
                print(f"   Ошибка загрузки страницы {page} (попытка {attempt+1}/{max_retries}): {e}. Ждём {wait} сек.")
                time.sleep(wait)
        else:
            print(f"   Не удалось загрузить страницу {page} после {max_retries} попыток. Останавливаем загрузку.")
            break

        if not items:
            break

        all_vacancies.extend(items)
        print(f"   Страница {page}: загружено {len(items)} вакансий (всего {len(all_vacancies)})")

        if len(items) < per_page:
            break
        page += 1
        time.sleep(0.5)
    
    print(f"   Всего загружено: {len(all_vacancies)} вакансий")
    
    saved = 0
    for vac in all_vacancies:
        hh_id = vac['id']
        name = clean_text(vac['name'])
        req = clean_text(vac['snippet'].get('requirement') or "")
        resp_text = clean_text(vac['snippet'].get('responsibility') or "")
        hash_val = compute_vacancy_hash(vac)
        employer = vac['employer']['name'] if vac.get('employer') else "Не указано"
        city = vac['area']['name'] if vac.get('area') else "Не указан"
        
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
                INSERT INTO vacancies (hh_id, hash, name, requirement, responsibility, employer_name, city, salary_from, salary_to, salary_currency, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (hh_id, hash_val, name, req, resp_text, employer, city, salary_from, salary_to, salary_currency, url))
            saved += 1
        except:
            pass
    
    conn.commit()
    print(f"   Сохранено новых вакансий: {saved}")

# ============================================================
# РАЗБИЕНИЕ НА ПАЧКИ
# ============================================================
def split_into_batches(vacancies):
    batches = []
    current_batch = []
    current_tokens = 0
    
    for vac_id, req, resp in vacancies:
        vac_text = f"=== Вакансия {len(current_batch) + 1} ===\nТребования: {req}\nОбязанности: {resp}\n"
        vac_tokens = count_tokens(vac_text)
        
        if vac_tokens > CONFIG['max_tokens_per_batch'] - CONFIG['system_overhead_tokens']:
            continue
        
        if (current_tokens + vac_tokens > CONFIG['max_tokens_per_batch'] - CONFIG['system_overhead_tokens']) or \
           (len(current_batch) >= CONFIG['max_vacancies_per_batch']):
            if current_batch:
                batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        
        current_batch.append((vac_id, req, resp))
        current_tokens += vac_tokens
    
    if current_batch:
        batches.append(current_batch)
    
    return batches

# ============================================================
# ИЗВЛЕЧЕНИЕ КОМПЕТЕНЦИЙ ЧЕРЕЗ LLM
# ============================================================
def extract_skills_batch(vacancies_batch, retry=None):
    if retry is None:
        retry = CONFIG['retry_attempts']
    
    batch_text = ""
    vac_ids = []
    for idx, (vac_id, req, resp) in enumerate(vacancies_batch, 1):
        text = f"Требования: {req}\nОбязанности: {resp}"
        batch_text += f"\n=== Вакансия {idx} ===\n{clean_text(text)}\n"
        vac_ids.append(vac_id)
    
    prompt = f"""
Ты — extractor технических компетенций из вакансий системного аналитика.

Задача:
Для КАЖДОЙ вакансии извлечь только профессиональные компетенции:
- hard skills (технологии, инструменты, нотации, протоколы, языки, БД, API, методологии),
- устойчивые профессиональные практики (например: "Сбор требований", "Описание бизнес-процессов", "Моделирование данных").

Не включать:
- общие слова и шум: "данных", "опыт", "знание", "навыки", "коммуникабельность", "ответственность", "обучаемость",
- названия компаний,
- бизнес-продукты/доменные термины без технической сущности,
- абстрактные и непроверяемые формулировки,
- дубликаты в рамках одной вакансии.

Нормализация (обязательно):
1) Приводи к канонической форме (кратко и технично):
   - "pgsql" -> "PostgreSQL"
   - "postgres" -> "PostgreSQL"
   - "rest api" -> "REST API"
   - "ооп" -> "ООП"
   - "uml нотации" -> "UML"
2) Убирай лишние уточнения и воду.
3) Используй индустриальное написание (SQL, BPMN, UML, Kafka, Docker).

Критерий включения:
Добавляй только то, что является отдельной проверяемой компетенцией.

Верни СТРОГО JSON:
- массив по количеству вакансий в том же порядке,
- каждый элемент — массив строк компетенций.

Формат ответа:
[
  ["BPMN", "UML", "SQL", "PostgreSQL", "REST API", "Jira", "Confluence"],
  ["Сбор требований", "User Story", "Use Case", "Swagger", "Postman"]
]

Вакансии:
{batch_text}
"""
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Извлекай только технические компетенции из вакансий. Возвращай строго JSON-массив массивов строк без комментариев и без текста вне JSON. Исключай общие слова и шум."},
            {"role": "user", "content": prompt}
        ]
    }
    
    for attempt in range(retry):
        try:
            rate_limiter.wait()
            
            response = requests.post(url, headers=headers, json=payload, timeout=CONFIG['request_timeout'])
            result = response.json()
            llm_response = result['choices'][0]['message']['content']
            
            json_match = re.search(r'\[[\s\S]*\]', llm_response)
            if json_match:
                llm_response = json_match.group(0)
            
            all_skills = json.loads(llm_response)
            
            for idx, skills in enumerate(all_skills):
                if idx < len(vac_ids):
                    for skill in skills:
                        skill = skill.strip()
                        if skill and len(skill) > 1:
                            cursor.execute('INSERT INTO raw_competencies (name, source_vacancy_id) VALUES (?, ?)', (skill, vac_ids[idx]))
            conn.commit()
            return True
            
        except Exception as e:
            wait_time = CONFIG['retry_base_delay'] * (2 ** attempt)
            print(f"      Попытка {attempt + 1} не удалась: {e}")
            if attempt < retry - 1:
                print(f"      Ждём {wait_time} сек")
                time.sleep(wait_time)
            else:
                print(f"      Пачка не обработана")
    
    return False

# ============================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================
def extract_all_competencies():
    print("\n2. Извлекаем компетенции из вакансий...")
    
    cursor.execute('''
        SELECT v.id, v.requirement, v.responsibility 
        FROM vacancies v
        LEFT JOIN raw_competencies rc ON v.id = rc.source_vacancy_id
        WHERE rc.id IS NULL
    ''')
    all_vacancies = cursor.fetchall()
    print(f"   Новых вакансий для обработки: {len(all_vacancies)}")
    
    if not all_vacancies:
        print("   Нет новых вакансий. Выход.")
        return
    
    batches = split_into_batches(all_vacancies)
    print(f"   Сформировано пачек: {len(batches)}")
    
    for i, batch in enumerate(batches, 1):
        print(f"\n   Пачка {i}/{len(batches)} ({len(batch)} вакансий)...")
        success = extract_skills_batch(batch)
        if not success:
            print(f"      Ошибка, разбиваем на меньшие...")
            for vac in batch:
                extract_skills_batch([vac], retry=3)
                time.sleep(3)
        time.sleep(CONFIG['delay_between_batches'])
    
    print("   Готово.")

# ============================================================
# ТОЧКА ВХОДА
# ============================================================
def main():
    if CONFIG.get('clear_raw_before_start', False):
        clear_raw_competencies()
    
    fetch_all_vacancies()
    extract_all_competencies()
    
    cursor.execute('SELECT COUNT(*) FROM raw_competencies')
    count = cursor.fetchone()[0]
    print(f"\nСырых компетенций извлечено: {count}")
    
    conn.close()
    print("\nГОТОВО.")

if __name__ == "__main__":
    main()