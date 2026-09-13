import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('vacancies.db')
c = conn.cursor()
c.execute("DELETE FROM parsed_requirements")
c.execute("DELETE FROM parsed_vacancies")
conn.commit()
print(f"Cleaned: {c.rowcount} rows")
