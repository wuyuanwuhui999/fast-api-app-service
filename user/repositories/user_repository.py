from sqlalchemy.orm import Session
from common.models.common_model import User
from user.schemas.user_schema import UserCreate, UserUpdate
from typing import Optional

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, userId: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == userId).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def verify_user(self, user_account: str) -> int:
        """
            根据user_account精确查询用户数量
            :param user_account: 用户账号
            :return: 匹配该账号的用户数量
            """
        return (
            self.db.query(User)
                .filter(User.user_account == user_account)
                .count()
        )

    def get_user_by_user_account(self, user_account: str, password: str) -> Optional[User]:
        return (
            self.db.query(User)
                .filter(
                ((User.user_account == user_account) |
                 (User.email == user_account) |
                 (User.telephone == user_account)) &
                (User.password == password)
            )
                .first()
        )

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user: UserCreate) -> User:
        db_user = User(
            user_account=user.user_account,
            email=user.email,
            username=user.username,
            password=user.password,
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
        db_user = self.get_user_by_id(user_id)
        if db_user:
            update_data = user.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def update_password(self, user_id: str, new_password: str) -> bool:
        db_user = self.get_user_by_id(user_id)
        if db_user:
            db_user.password = new_password
            self.db.commit()
            return True
        return False

    def verify_password(self, user_account: str, password: str) -> bool:
        return self.get_user_by_user_account(user_account, password)

