import requests
import json
import time

# Твой API ключ Perplexity
import os
API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# 1. Получаем вакансии из HH.ru
print("1. Получаем вакансии из HH.ru...")
resp = requests.get("https://api.hh.ru/vacancies?text=NAME:системный+аналитик&per_page=100")
data = resp.json()
vacancies = data['items']
total_found = data['found']

print(f"2. Всего найдено на HH.ru: {total_found} вакансий")
print(f"3. Загружено за раз: {len(vacancies)} вакансий")

# 2. Обрабатываем каждую вакансию
url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

results = []
total_time = 0

for i, vac in enumerate(vacancies[:15], 1):
    # Получаем requirement и responsibility, заменяем None на пустую строку
    req = vac['snippet'].get('requirement') or ""
    resp_text = vac['snippet'].get('responsibility') or ""
    text = req + " " + resp_text
    
    # Если текст пустой — пропускаем вакансию
    if not text.strip():
        print(f"4.{i} Пропускаем вакансию {i} (нет описания)")
        continue
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "Ты оцениваешь вакансии. Отвечай только числом от 0 до 100."
            },
            {
                "role": "user",
                "content": f"Оцени вакансию по навыкам: BPMN, UML, SQL, API, Jira, Confluence. Ответь только числом. Текст: {text}"
            }
        ]
    }
    
    print(f"4.{i} Обработка вакансии {i}...")
    start = time.time()
    response = requests.post(url, headers=headers, json=payload)
    end = time.time()
    
    result = response.json()
    score = result['choices'][0]['message']['content']
    elapsed = end - start
    total_time += elapsed
    
    results.append({
        'id': vac['id'],
        'name': vac['name'],
        'score': score,
        'time': elapsed
    })
    
    print(f"    Score: {score}, Время: {elapsed:.2f}с")

# 3. Итоги
print(f"\n5. Обработано вакансий: {len(results)}")
if len(results) > 0:
    print(f"6. Общее время: {total_time:.2f} секунд")
    print(f"7. Среднее время на вакансию: {total_time/len(results):.2f} секунд")
    print(f"8. Прогноз на 2000 вакансий: {(total_time/len(results)) * 2000 / 60:.0f} минут")

    # 4. Выводим топ-5
    sorted_results = sorted(results, key=lambda x: int(x['score']), reverse=True)
    print("\n9. Топ-5 вакансий по match_score:")
    for r in sorted_results[:5]:
        print(f"    {r['score']}% - {r['name']}")
else:
    print("Нет вакансий с описанием для обработки")