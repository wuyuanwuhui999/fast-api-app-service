# common/config/common_config.py
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
import warnings
# 抑制 urllib3 的 HTTPS 警告
from urllib3.exceptions import InsecureRequestWarning
import logging

warnings.filterwarnings("ignore", category=InsecureRequestWarning)
logging.getLogger("elasticsearch").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*verify_certs=False.*")


class Settings(BaseSettings):
    app_name: str = "Fast Api Service"
    secret_key: str = "WCdTBej2ZRhIBXafQbALbAwpJ5A+v1PR4A4IN6+OhnM="
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200
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

    # Nacos配置
    nacos_host: str = "127.0.0.1"
    nacos_port: int = 8848
    nacos_namespace: str = ""
    nacos_username: str = "nacos"
    nacos_password: str = "nacos"

    # Chroma配置（替换Elasticsearch）
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection_name: str = "chat_documents"
    embedding_model: str = "nomic-embed-text:latest"

    # 服务配置
    enable_nacos: bool = True

    class Config:
        env_file = Path(__file__).parent.parent.parent / ".env"


@lru_cache()
def get_settings():
    return Settings()