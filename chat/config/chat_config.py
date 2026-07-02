from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    UPLOAD_DIR: str = "/Users/wuwenqiang/Documents/static/chat"
    # Chroma配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "chat_vector_collection"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    QWEN_MODEL_NAME: str = "qwen:7b"
    DEEPSEEK_MODEL_NAME: str = "deepseek:7b"
    TEMPERATURE: float = 0.7
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_TIMEOUT: int = 60
    REDIS_URL: str = "redis://localhost:6379"
    class Config:
        env_file = ".env"

settings = Settings()