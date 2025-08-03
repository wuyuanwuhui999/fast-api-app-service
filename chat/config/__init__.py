from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    UPLOAD_DIR: str = "./uploads"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "documents"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    QWEN_MODEL_NAME: str = "qwen:7b"
    DEEPSEEK_MODEL_NAME: str = "deepseek:7b"
    TEMPERATURE: float = 0.7
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_TIMEOUT: int = 60

    class Config:
        env_file = ".env"

settings = Settings()