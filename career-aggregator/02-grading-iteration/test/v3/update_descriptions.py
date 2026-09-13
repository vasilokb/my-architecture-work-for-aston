import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import requests
import time
import re
from bs4 import BeautifulSoup

conn = sqlite3.connect('vacancies.db')
c = conn.cursor()

c.execute("SELECT hh_id FROM vacancies ORDER BY id")
all_ids = [r[0] for r in c.fetchall()]
print(f"Vacancies to update: {len(all_ids)}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

session = requests.Session()
session.headers.update(headers)

updated = 0
failed = 0
skipped = 0

for i, hh_id in enumerate(all_ids, 1):
    c.execute("SELECT length(requirement), length(responsibility) FROM vacancies WHERE hh_id = ?", (hh_id,))
    row = c.fetchone()

    if row[0] > 500 and row[1] > 500:
        skipped += 1
        continue

    url = f"https://hh.ru/vacancy/{hh_id}"
    try:
        r = session.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  [{i}/{len(all_ids)}] {hh_id} -> status {r.status_code}")
            failed += 1
            if r.status_code == 404:
                continue
            time.sleep(5)
            continue

        soup = BeautifulSoup(r.text, 'html.parser')
        desc = soup.find('div', {'data-qa': 'vacancy-description'})
        if not desc:
            desc = soup.select_one('div.vacancy-description')
        if not desc:
            print(f"  [{i}/{len(all_ids)}] {hh_id} -> no description block")
            failed += 1
            continue

        full_text = desc.get_text(separator='\n', strip=True)

        parts = re.split(r'Что мы предлагаем|Мы предлагаем|Условия', full_text, flags=re.IGNORECASE)
        req_resp_text = parts[0] if parts else full_text

        split_patterns = [
            r'Чем предстоит заниматься',
            r'Что предстоит заниматься',
            r'Обязанности',
            r'Ваши задачи',
            r'Направление работы',
            r'Будете делать',
        ]
        pattern = '|'.join(split_patterns)
        match = re.search(pattern, req_resp_text, re.IGNORECASE)

        if match:
            requirement = req_resp_text[:match.start()].strip()
            responsibility = req_resp_text[match.start():].strip()
        else:
            requirement = req_resp_text.strip()
            responsibility = ""

        c.execute("UPDATE vacancies SET requirement = ?, responsibility = ? WHERE hh_id = ?",
                  (requirement, responsibility, hh_id))

        updated += 1
        if updated % 50 == 0:
            conn.commit()
            print(f"  [{i}/{len(all_ids)}] Updated {updated}, committed")

        time.sleep(1.5)

    except Exception as e:
        print(f"  [{i}/{len(all_ids)}] {hh_id} -> error: {e}")
        failed += 1
        time.sleep(3)

conn.commit()
print(f"\nDone. Updated: {updated}, Skipped (already full): {skipped}, Failed: {failed}")
conn.close()
