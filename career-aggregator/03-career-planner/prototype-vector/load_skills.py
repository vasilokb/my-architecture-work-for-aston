"""Одноразовая загрузка справочника скиллов с векторами в Postgres+pgvector."""
import psycopg2
from sentence_transformers import SentenceTransformer

DB = dict(host="localhost", port=5433, dbname="prototype", user="career", password="career")
MODEL = "all-MiniLM-L6-v2"


def to_pgvector(emb) -> str:
    return "[" + ", ".join(f"{x:.8f}" for x in emb) + "]"


def main():
    with open("skills.txt", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]

    print(f"loading model {MODEL} (первый запуск скачает ~90 МБ)...")
    model = SentenceTransformer(MODEL)
    embeddings = model.encode(names, normalize_embeddings=True)

    conn = psycopg2.connect(**DB)
    try:
        with conn:
            with conn.cursor() as cur:
                for name, emb in zip(names, embeddings):
                    cur.execute(
                        "INSERT INTO skills (name, embedding) VALUES (%s, %s) "
                        "ON CONFLICT (name) DO UPDATE SET embedding = EXCLUDED.embedding",
                        (name, to_pgvector(emb)),
                    )
        print(f"loaded {len(names)} skills")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
