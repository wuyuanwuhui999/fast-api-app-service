from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from common.config.common_config import get_settings
from user.schemas.token_schema import TokenData
from user.models.user_model import User  # 添加这行导入
import json

from common.utils.jwt_util import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

settings = get_settings()


async def get_current_user(
        token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authorization": "Bearer"},
    )
    try:
        payload = verify_token(token)
        user_data: str = payload.get("sub")
        if user_data is None:
            raise credentials_exception
        # 这里需要将JSON字符串解析为字典
        token_data = TokenData(**json.loads(user_data))
    except (JWTError, json.JSONDecodeError) as e:
        raise credentials_exception
    return token_data


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:  # 添加返回类型注解
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user