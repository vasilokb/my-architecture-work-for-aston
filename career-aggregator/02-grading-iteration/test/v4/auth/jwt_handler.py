from datetime import datetime, timezone, timedelta
from jose import jwt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from exceptions import AuthError

def create_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise AuthError("Invalid or expired token")
