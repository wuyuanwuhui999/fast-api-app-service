from pathlib import Path
from functools import lru_cache  # 添加这行
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Fast Api Service"
    secret_key: str = "WCdTBej2ZRhIBXafQbALbAwpJ5A+v1PR4A4IN6+OhnM="
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
    avater_path: str = "/static/user/avater/"
    UPLOAD_DIR: str = "G:/static/ai/"
    class Config:
        env_file = Path(__file__).parent.parent.parent / ".env"


@lru_cache()
def get_settings():
    return Settings()