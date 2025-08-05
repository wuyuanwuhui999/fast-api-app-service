from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from common.config.common_config import get_settings
from user.schemas.token_schema import TokenData
from user.repositories.user_repository import UserRepository
from user.schemas.user_schema import UserInDB
from common.utils.result_util import ResultUtil
from common.utils.jwt_util import create_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.settings = get_settings()

    async def login(self, userAccount: str, password: str):
        user = self.user_repository.get_user_by_user_account(userAccount,password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号或者密码不正确",
                headers={"Authorization": "Bearer"},
            )

        access_token_expires = timedelta(minutes=self.settings.access_token_expire_minutes)
        user_data = ResultUtil.convert_snake_to_camel(UserInDB.model_validate(user).dict())
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,  # Exclude sensitive data
            token=access_token
        )

    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"Authorization": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=[self.settings.algorithm])
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
