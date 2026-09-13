import sqlite3
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

COMPETENCY_TREE = []
cursor.execute('''
    SELECT cc.name, c.id, c.name
    FROM competency_categories cc
    JOIN competency_category_link cl ON cc.id = cl.category_id
    JOIN competencies c ON cl.competency_id = c.id
    ORDER BY cc.name, c.name
''')
rows = cursor.fetchall()
current_group = None
for group_name, comp_id, comp_name in rows:
    if group_name != current_group:
        COMPETENCY_TREE.append(f"\n{group_name}:")
        current_group = group_name
    COMPETENCY_TREE.append(f"    {comp_id}. {comp_name}")
COMPETENCY_TREE_TEXT = "\n".join(COMPETENCY_TREE)

cursor.execute("SELECT requirement, responsibility FROM vacancies WHERE hh_id = '131771794'")
row = cursor.fetchone()
batch_text = f"\n=== Vacancy 1 ===\nName: Системный аналитик\nDesc:\n{row[0]} {row[1]}\n"

prompt = f"""
Из представленного ниже списка компетенций выбери те, что явно упомянуты в тексте вакансии.

СПИСОК КОМПЕТЕНЦИЙ (ТОЛЬКО ИЗ ЭТОГО СПИСКА):
{COMPETENCY_TREE_TEXT}

ПРАВИЛА:
1. Используй ТОЛЬКО id из списка выше
2. НЕ придумывай новые названия
3. НЕ добавляй то чего нет в списке
4. Для каждой компетенции укажи level: junior/middle/senior, mandatory: true/false, confidence: 0.0-1.0, evidence: цитата из текста

Верни ТОЛЬКО JSON-массив без пояснений:
[
  {{
    "requirements": [
      {{"id": 1, "level": "middle", "mandatory": true, "confidence": 0.9, "evidence": "цитата"}}
    ]
  }}
]

Вакансии:
{batch_text}
"""

content = "Ты извлекаешь навыки из вакансий. Используй ТОЛЬКО компетенции из предоставленного списка. Возвращай только JSON.\n\n" + prompt

payload = {
    "model": "sonar-pro",
    "messages": [
        {"role": "user", "content": content}
    ]
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
