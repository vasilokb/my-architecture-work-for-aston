import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('vacancies.db')
c = conn.cursor()

# Check if 131771794 exists in parsed_vacancies
c.execute("SELECT id, hh_id, job_title, overall_level FROM parsed_vacancies WHERE hh_id = '131771794'")
rows = c.fetchall()
print("parsed_vacancies для 131771794:", rows)

# Check all vacancies that were NOT processed
c.execute("""
    SELECT v.hh_id, v.name 
    FROM vacancies v 
    LEFT JOIN parsed_vacancies pv ON v.hh_id = pv.hh_id 
    WHERE pv.id IS NULL
""")
not_processed = c.fetchall()
print(f"\nНеобработанных вакансий: {len(not_processed)}")
for r in not_processed:
    print(f"  {r[0]}: {r[1]}")
