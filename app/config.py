from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache  # 添加这行

class Settings(BaseSettings):
    app_name: str = "User Service"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # 30 days
    database_url: str
    redis_url: str = "redis://localhost:6379"
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int = 465
    mail_server: str = "smtp.qq.com"
    mail_starttls: bool = False
    mail_ssl_tls: bool = True
    avatar_path: str = "/static/user/avatar/"

    class Config:
        env_file = Path(__file__).parent.parent / ".env"


@lru_cache()
def get_settings():
    return Settings()