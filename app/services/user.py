from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserInDB, UserUpdate, PasswordChange, ResetPasswordRequest, \
    ResetPasswordConfirm, MailRequest
from app.database import get_db
from app.utils.security import get_password_hash, verify_password
from app.utils.jwt import create_access_token
from datetime import timedelta
from app.config import get_settings
import random
import redis

settings = get_settings()


class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repository = UserRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)

    async def register_user(self, user: UserCreate) -> UserInDB:
        # Check if username or email already exists
        if self.user_repository.get_user_by_username(user.user_account):
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

    async def get_user(self, user_id: str) -> Optional[UserInDB]:
        db_user = self.user_repository.get_user(user_id)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserInDB.model_validate(db_user)

    async def update_user(self, user_id: str, user: UserUpdate) -> UserInDB:
        db_user = self.user_repository.update_user(user_id, user)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserInDB.model_validate(db_user)

    async def update_password(self, user_id: str, password_change: PasswordChange) -> bool:
        if not self.user_repository.verify_password(user_id, password_change.old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect old password"
            )
        return self.user_repository.update_password(user_id, password_change.new_password)

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