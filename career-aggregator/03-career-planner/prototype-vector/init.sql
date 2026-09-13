CREATE EXTENSION IF NOT EXISTS vector;

-- Справочник скиллов (базовая таблица прототипа)
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    embedding VECTOR(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skills_embedding
ON skills USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 4);

-- Боевые таблицы (миниатюра целевой схемы из видения 12.08)
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    hh_id TEXT UNIQUE,
    name TEXT,
    employer TEXT,
    technology TEXT NOT NULL,
    published_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vacancy_skills (
    vacancy_id INT REFERENCES vacancies(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login TEXT UNIQUE,
    technology TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL
);
