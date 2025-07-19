from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import get_settings
from app.schemas.token import TokenData
from app.repositories.user import UserRepository
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User  # 添加这行导入

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

settings = get_settings()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:  # 添加返回类型注解
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user_repository = UserRepository(db)
    user = user_repository.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:  # 添加返回类型注解
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user