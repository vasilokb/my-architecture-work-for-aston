import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import requests
import time
import re
from bs4 import BeautifulSoup

conn = sqlite3.connect('vacancies.db')
c = conn.cursor()

c.execute("SELECT hh_id, length(requirement), length(responsibility) FROM vacancies ORDER BY id LIMIT 5")
rows = c.fetchall()
print(f"Testing on {len(rows)} vacancies:\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}
session = requests.Session()
session.headers.update(headers)

for hh_id, old_req_len, old_resp_len in rows:
    url = f"https://hh.ru/vacancy/{hh_id}"
    r = session.get(url, timeout=30)
    print(f"{hh_id}: status={r.status_code}, old_req={old_req_len}, old_resp={old_resp_len}")

    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        desc = soup.find('div', {'data-qa': 'vacancy-description'})
        if desc:
            text = desc.get_text(separator='\n', strip=True)
            print(f"  Full description: {len(text)} chars")
            print(f"  Preview: {text[:150]}...\n")
        else:
            print(f"  No description block found\n")
    else:
        print(f"  Failed\n")

    time.sleep(2)
