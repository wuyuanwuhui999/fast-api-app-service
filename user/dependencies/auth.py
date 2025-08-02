from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from user.config import get_settings
from user.schemas.token import TokenData
from user.repositories.user import UserRepository
from user.database import get_db
from sqlalchemy.orm import Session
from user.models.user import User  # 添加这行导入
from base64 import b64decode
import json
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

settings = get_settings()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authorization": "Bearer"},
    )
    try:
        secret_key = b64decode(settings.secret_key)
        payload = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
        user_data: str = payload.get("sub")
        if user_data is None:
            raise credentials_exception
        # 这里需要将JSON字符串解析为字典
        token_data = TokenData(**json.loads(user_data))
    except (JWTError, json.JSONDecodeError) as e:
        raise credentials_exception

    user_repository = UserRepository(db)
    # 根据你的数据结构，应该使用user_data.id而不是token_data.id
    user = user_repository.get_user_by_username(token_data.id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:  # 添加返回类型注解
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user