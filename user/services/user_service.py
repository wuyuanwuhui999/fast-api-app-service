from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from common.schemas.user_schema import UserInDB
from user.repositories.user_repository import UserRepository
from user.schemas.user_schema import UserCreate, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest
from common.config.common_database import get_db
from common.utils.jwt_util import create_access_token
from datetime import timedelta
from common.config.common_config import get_settings
import random
import redis
from fastapi.logger import logger
from common.utils.result_util import ResultEntity, ResultUtil

settings = get_settings()


class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repository = UserRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)

    async def register_user(self, user: UserCreate) -> ResultEntity:
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

        user_data = self.user_repository.create_user(user)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user_data).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def get_user_data(self, current_user: UserInDB) -> ResultEntity:
        user = self.user_repository.get_user_by_id(current_user.id)
        user_data = UserInDB.model_validate(user).dict()
        # 生成新的访问令牌，默认30天有效期
        token = create_access_token(data={"sub": user_data})

        # 直接返回封装好的ResultEntity
        return ResultUtil.success(
            data=user_data,
            token=token
        )

    async def update_user(self, user_id: str, user: UserUpdate) -> ResultEntity:
        db_user = self.user_repository.update_user(user_id, user)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return ResultUtil.success(data=1)

    async def update_password(self, user_account: str, password_change: PasswordChange) -> ResultEntity:
        # 使用同步调用
        user = self.user_repository.verify_password(user_account, password_change.oldPassword)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码不正确"
            )

        # 更新密码
        success = self.user_repository.update_password(user.id, password_change.newPassword)
        return ResultUtil.success(data=1 if success else 0)

    async def send_email_verify_code(self, mail_request: MailRequest) -> ResultEntity:
        if not self.user_repository.get_user_by_email(mail_request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not registered"
            )

        code = random.randint(1000, 9999)
        await self.redis.setex(mail_request.email, timedelta(minutes=5), code)
        print(f"Verification code for {mail_request.email}: {code}")
        return ResultUtil.success(msg="验证码发送成功，请在五分钟内完成操作")

    async def reset_password(self, reset_request: ResetPasswordConfirm) -> ResultEntity:
        stored_code = self.redis.get(reset_request.email)
        if stored_code is None or stored_code.decode('utf-8') != reset_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        user = self.user_repository.get_user_by_email(reset_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self.user_repository.update_password(user.id, reset_request.new_password)

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def login_by_email(self, mail_request: MailRequest) -> ResultEntity:
        stored_code = self.redis.get(mail_request.email)
        if stored_code is None or stored_code.decode('utf-8') != mail_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        user = self.user_repository.get_user_by_email(mail_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def verify_user(self, user: UserCreate) -> ResultEntity:
        user_account_count = self.user_repository.verify_user(user.user_account)
        return ResultUtil.success(data=user_account_count)