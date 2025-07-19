from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import get_settings
from app.schemas.token import TokenData
from app.repositories.user import UserRepository
from app.utils.security import verify_password
from app.utils.jwt import create_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.settings = get_settings()

    async def authenticate_user(self, username: str, password: str):
        user = await self.user_repository.get_user_by_username_or_email(username)
        if not user:
            return False
        if not verify_password(password, user.password):
            return False
        return user

    async def login(self, username: str, password: str):
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=self.settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.user_account}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
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