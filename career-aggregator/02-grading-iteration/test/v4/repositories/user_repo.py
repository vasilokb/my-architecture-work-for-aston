from sqlalchemy.orm import Session
from models.user import User
from exceptions import NotFoundError

class UserRepo:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> User:
        user = self.session.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    def get_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email).first()

    def create(self, email: str, password_hash: str, role: str, expires_at=None) -> User:
        user = User(email=email, password_hash=password_hash, role=role, expires_at=expires_at)
        self.session.add(user)
        self.session.flush()
        return user

    def delete(self, user_id: int):
        user = self.get_by_id(user_id)
        self.session.delete(user)
        self.session.flush()
