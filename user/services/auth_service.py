# user/services/auth_service.py
import os
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from common.schemas.token_schema import TokenData
from user.repositories.user_repository import UserRepository
from common.schemas.user_schema import UserSchema
from common.utils.result_util import ResultUtil
from common.utils.jwt_util import create_access_token

# 直接从环境变量读取配置
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def login(self, userAccount: str, password: str):
        user = self.user_repository.get_user_by_user_account(userAccount, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号或者密码不正确",
                headers={"Authorization": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        user_data = ResultUtil.convert_snake_to_camel(UserSchema.model_validate(user).dict())
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"Authorization": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception

        user = await self.user_repository.get_user_by_username(token_data.username)
        if user is None:
            raise credentials_exception
        return user