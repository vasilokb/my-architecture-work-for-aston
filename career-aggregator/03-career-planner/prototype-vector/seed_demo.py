"""Наполнение боевых таблиц: пользователь demo + ~20 вакансий трёх технологий."""
import psycopg2
from sentence_transformers import SentenceTransformer

DB = dict(host="localhost", port=5433, dbname="prototype", user="career", password="career")
MODEL = "all-MiniLM-L6-v2"

USER = ("demo", "Системный аналитик", ["SQL", "BPMN", "UML", "REST API"])

VACANCIES = [
    # (hh_id, name, employer, technology, [skills])
    ("101", "Системный аналитик (ERP)", "Сбер", "Системный аналитик", ["SQL", "UML", "BPMN", "Jira", "Confluence", "Use Case", "Visio"]),
    ("102", "Ведущий системный аналитик", "Тинькофф", "Системный аналитик", ["SQL", "BPMN", "REST API", "UML", "Agile", "Swagger", "Postman", "OpenAPI"]),
    ("103", "Аналитик бизнес-процессов", "X5 Group", "Системный аналитик", ["BPMN", "UML", "Excel", "Confluence", "Agile", "Process Mining", "Celonis", "Visio"]),
    ("104", "Системный аналитик (интеграции)", "РЖД", "Системный аналитик", ["REST API", "SOAP", "SQL", "UML", "XML", "JSON", "Swagger"]),
    ("105", "Системный аналитик", "Совкомбанк", "Системный аналитик", ["SQL", "ER-диаграммы", "BPMN", "Jira", "DFD", "IDEF0"]),
    ("106", "Аналитик (методолог)", "Альфа-Банк", "Системный аналитик", ["BPMN", "UML", "Excel", "SQL", "User Story", "Use Case"]),
    ("107", "Системный аналитик (платежи)", "Озон", "Системный аналитик", ["SQL", "REST API", "BPMN", "Confluence", "Camunda", "ArchiMate"]),
    ("201", "Data Engineer", "Ozon", "Data Engineer", ["SQL", "Python", "Airflow", "Kafka", "PostgreSQL"]),
    ("202", "Senior Data Engineer", "Тинькофф", "Data Engineer", ["SQL", "Spark", "Kafka", "DWH", "Airflow"]),
    ("203", "Инженер данных", "Сбер", "Data Engineer", ["ETL", "SQL", "ClickHouse", "Airflow"]),
    ("204", "Data Engineer", "X5 Group", "Data Engineer", ["Python", "PostgreSQL", "ETL", "Docker"]),
    ("205", "Big Data Engineer", "МТС", "Data Engineer", ["Spark", "Hadoop", "Kafka", "SQL"]),
    ("206", "Data Warehouse Engineer", "Ростелеком", "Data Engineer", ["DWH", "ETL", "SQL", "Snowflake"]),
    ("207", "Data Engineer", "Авито", "Data Engineer", ["Airflow", "Kafka", "ClickHouse", "Python"]),
    ("301", "Java-разработчик", "Сбер", "Java-разработчик", ["Java", "Spring", "PostgreSQL", "Docker"]),
    ("302", "Senior Java Developer", "Тинькофф", "Java-разработчик", ["Java", "Spring", "Kafka", "Kubernetes", "Microservices"]),
    ("303", "Java-разработчик", "Ozon", "Java-разработчик", ["Java", "REST API", "PostgreSQL", "Docker"]),
    ("304", "Backend Developer (Java)", "Авито", "Java-разработчик", ["Java", "Microservices", "Kafka", "Git"]),
    ("305", "Java-разработчик", "ВТБ", "Java-разработчик", ["Java", "Spring", "SQL", "REST API"]),
    ("306", "Lead Java Developer", "Wildberries", "Java-разработчик", ["Java", "Kubernetes", "Terraform", "Microservices"]),
]


def to_pgvector(emb) -> str:
    return "[" + ", ".join(f"{x:.8f}" for x in emb) + "]"


def main():
    print(f"loading model {MODEL}...")
    model = SentenceTransformer(MODEL)

    def vec(text: str) -> str:
        return to_pgvector(model.encode([text], normalize_embeddings=True)[0])

    conn = psycopg2.connect(**DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE user_skills, users, vacancy_skills, vacancies RESTART IDENTITY")
                login, tech, user_skills = USER
                cur.execute(
                    "INSERT INTO users (login, technology) VALUES (%s, %s) RETURNING id",
                    (login, tech),
                )
                user_id = cur.fetchone()[0]
                for s in user_skills:
                    cur.execute(
                        "INSERT INTO user_skills (user_id, skill, embedding) VALUES (%s, %s, %s)",
                        (user_id, s, vec(s)),
                    )


                for hh_id, name, employer, technology, skills in VACANCIES:
                    cur.execute(
                        "INSERT INTO vacancies (hh_id, name, employer, technology) "
                        "VALUES (%s, %s, %s, %s) RETURNING id",
                        (hh_id, name, employer, technology),
                    )
                    vac_id = cur.fetchone()[0]
                    for s in skills:
                        cur.execute(
                            "INSERT INTO vacancy_skills (vacancy_id, skill, embedding) VALUES (%s, %s, %s)",
                            (vac_id, s, vec(s)),
                        )
        print(f"seeded: user {login} + {len(VACANCIES)} vacancies")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
