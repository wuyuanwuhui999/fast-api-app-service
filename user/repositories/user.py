from sqlalchemy.orm import Session
from user.models.user import User
from user.schemas.user import UserCreate, UserUpdate
from user.utils.security import get_password_hash
from typing import Optional

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.user_account == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username_or_email(self, username: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter((User.user_account == username) | (User.email == username))
            .first()
        )

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user: UserCreate) -> User:
        hashed_password = get_password_hash(user.password)
        db_user = User(
            user_account=user.user_account,
            email=user.email,
            username=user.username,
            password=hashed_password,
            telephone=user.telephone,
            birthday=user.birthday,
            sex=user.sex,
            sign=user.sign,
            region=user.region,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: str, user: UserUpdate) -> Optional[User]:
        db_user = self.get_user(user_id)
        if db_user:
            update_data = user.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def update_password(self, user_id: str, new_password: str) -> bool:
        db_user = self.get_user(user_id)
        if db_user:
            db_user.password = get_password_hash(new_password)
            self.db.commit()
            return True
        return False

    def verify_password(self, user_id: str, password: str) -> bool:
        db_user = self.get_user(user_id)
        if db_user:
            return verify_password(password, db_user.password)
        return False