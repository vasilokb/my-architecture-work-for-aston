import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
conn = sqlite3.connect('vacancies.db')
c = conn.cursor()

print("=== OVERALL GRADES ===")
c.execute("SELECT overall_level, COUNT(*) FROM parsed_vacancies GROUP BY overall_level")
for r in c.fetchall():
    print(f"  {r[0]:<10}: {r[1]}")

print("\n=== COMPETENCY DISTRIBUTION ===")
c.execute("""
    SELECT c.name, COUNT(*) as cnt
    FROM parsed_requirements pr
    JOIN competencies c ON pr.competency_id = c.id
    GROUP BY c.name
    ORDER BY cnt DESC
""")
for r in c.fetchall():
    print(f"  {r[0]:<25}: {r[1]}")

print("\n=== LEVEL DISTRIBUTION ===")
c.execute("SELECT required_level, COUNT(*) FROM parsed_requirements GROUP BY required_level")
for r in c.fetchall():
    print(f"  {r[0]:<10}: {r[1]}")

print("\n=== MANDATORY vs OPTIONAL ===")
c.execute("SELECT CASE is_mandatory WHEN 1 THEN 'mandatory' ELSE 'optional' END, COUNT(*) FROM parsed_requirements GROUP BY is_mandatory")
for r in c.fetchall():
    print(f"  {r[0]:<10}: {r[1]}")

print("\n=== CONFIDENCE STATS ===")
c.execute("SELECT MIN(confidence), MAX(confidence), ROUND(AVG(confidence), 2) FROM parsed_requirements")
r = c.fetchone()
print(f"  Min: {r[0]}, Max: {r[1]}, Avg: {r[2]}")

print("\n=== SKILLS PER VACANCY ===")
c.execute("""
    SELECT pv.id, pv.hh_id, COUNT(pr.id)
    FROM parsed_vacancies pv
    LEFT JOIN parsed_requirements pr ON pv.id = pr.parsed_vacancy_id
    GROUP BY pv.id
    ORDER BY COUNT(pr.id) DESC
""")
for r in c.fetchall():
    print(f"  {r[1]}: {r[2]} skills")
