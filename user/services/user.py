from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from user.repositories.user import UserRepository
from user.schemas.user import UserCreate, UserInDB, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest
from user.database import get_db
from user.utils.jwt import create_access_token
from datetime import timedelta
from user.config import get_settings
import random
import redis

from user.utils.result_util import ResultEntity, ResultUtil

settings = get_settings()


class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repository = UserRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)

    async def register_user(self, user: UserCreate) -> UserInDB:
        if self.user_repository.get_user_by_user_account(user.user_account):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        if self.user_repository.get_user_by_email(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        db_user = self.user_repository.create_user(user)
        return UserInDB.model_validate(db_user)

    async def get_user_data(self, current_user: UserInDB) -> ResultEntity:
        user = await self.user_repository.get_user_by_id(current_user.id)
        user_data = UserInDB.model_validate(user).dict()
        # 生成新的访问令牌，默认30天有效期
        token = create_access_token(data={"sub": user_data})

        # 直接返回封装好的ResultEntity
        return ResultUtil.success(
            data=user_data,
            token=token
        )

    async def get_user(self, user_id: str) -> Optional[UserInDB]:
        db_user = self.user_repository.get_user(user_id)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserInDB.model_validate(db_user)

    async def update_user(self, user_id: str, user: UserUpdate) -> UserInDB:
        db_user = self.user_repository.update_user(user_id, user)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return ResultUtil.success(data=1)

    async def update_password(self, user_account: str, password_change: PasswordChange) -> ResultEntity:
        # 使用同步调用
        user =  self.user_repository.verify_password(user_account, password_change.oldPassword)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码不正确"
            )

        # 更新密码
        success = self.user_repository.update_password(user.id, password_change.newPassword)

        return ResultUtil.success(data=1 if success else 0)

    async def send_email_verify_code(self, mail_request: MailRequest) -> bool:
        # Validate email format and existence
        if not self.user_repository.get_user_by_email(mail_request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not registered"
            )

        # Generate and store verification code
        code = random.randint(1000, 9999)
        self.redis.setex(mail_request.email, timedelta(minutes=5), code)

        # In production, you would send the code via email
        print(f"Verification code for {mail_request.email}: {code}")
        return True

    async def reset_password(self, reset_request: ResetPasswordConfirm) -> dict:
        # Verify the code
        stored_code = self.redis.get(reset_request.email)
        if not stored_code or int(stored_code) != reset_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        # Update password
        user = self.user_repository.get_user_by_email(reset_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self.user_repository.update_password(user.id, reset_request.new_password)

        # Generate new token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.user_account},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserInDB.model_validate(user)
        }

    async def login_by_email(self, mail_request: MailRequest) -> dict:
        # Verify the code
        stored_code = self.redis.get(mail_request.email)
        if not stored_code or str(stored_code) != mail_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        user = self.user_repository.get_user_by_email(mail_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.user_account},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserInDB.model_validate(user)
        }

    async def verify_user(self, user: UserCreate) -> dict:
        username_exists = self.user_repository.get_user_by_username(user.user_account) is not None
        email_exists = self.user_repository.get_user_by_email(user.email) is not None

        return {
            "username_exists": username_exists,
            "email_exists": email_exists
        }