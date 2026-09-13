import os

_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(_DB_DIR, 'vacancies.db')}")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "perplexity")
LLM_MODEL = os.getenv("LLM_MODEL", "sonar-pro")

RATE_LIMIT_PER_MINUTE = 10
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 10

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 30

HH_API_BASE = "https://api.hh.ru"

DICT_CACHE_TTL = 300
