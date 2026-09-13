-- Топ-10 похожих скиллов на заданный. Поменять 'SQL' на свой скилл.
-- Процент = (1 - косинусное расстояние) * 100
-- ВАЖНО: каст ::numeric обязателен, ROUND(double, int) в Postgres нет
WITH target AS (
    SELECT embedding AS v FROM skills WHERE name = 'SQL'
)
SELECT
    s.name,
    ROUND(((1 - (s.embedding <=> t.v)) * 100)::numeric, 1) AS similarity_percent
FROM skills s
CROSS JOIN target t
WHERE s.name <> 'SQL'
ORDER BY s.embedding <=> t.v
LIMIT 10;
