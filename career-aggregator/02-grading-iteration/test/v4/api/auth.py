from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from infrastructure.database import get_session
from repositories.user_repo import UserRepo
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_token
from schemas.auth import LoginRequest, RegisterRequest, Token, UserRead
from models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=Token)
async def register(req: RegisterRequest, session: Session = Depends(get_session)):
    repo = UserRepo(session)
    if repo.get_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email exists")
    expires = None
    if req.role == "employee":
        expires = User.employee_expires_default()
    user = repo.create(req.email, hash_password(req.password), req.role, expires)
    session.commit()
    return Token(access_token=create_token(user.id, user.role))

@router.post("/login", response_model=Token)
async def login(req: LoginRequest, session: Session = Depends(get_session)):
    repo = UserRepo(session)
    user = repo.get_by_email(req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.is_expired():
        raise HTTPException(status_code=403, detail="Account expired")
    return Token(access_token=create_token(user.id, user.role))
