import sys; sys.stdout.reconfigure(encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

url = 'https://hh.ru/vacancy/132053577'
r = requests.get(url, headers=headers, timeout=30)
print(f"Status: {r.status_code}")
print(f"Length: {len(r.text)}")

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    desc = soup.find('div', {'data-qa': 'vacancy-description'})
    if desc:
        text = desc.get_text(separator='\n', strip=True)
        print(f"\nDescription length: {len(text)} chars")
        print(f"\n--- FULL DESCRIPTION ---\n{text[:2000]}")
    else:
        print("\nNo vacancy-description found, trying other selectors...")
        for tag in ['div.vacancy-description', 'div.g-user-content', 'div.b-vacancy-desc-wrapper']:
            el = soup.select_one(tag)
            if el:
                print(f"Found: {tag}")
                print(el.get_text(separator='\n', strip=True)[:500])
                break
        else:
            print("Nothing found. Page snippet:")
            print(r.text[:1000])
