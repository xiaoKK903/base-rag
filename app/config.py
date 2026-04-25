from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "AI工具平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: list[str] = ["*"]

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    VECTOR_STORE_PATH: str = "data/vectors"
    DOCUMENTS_PATH: str = "data/documents"

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    TOP_K: int = 5
    MIN_SCORE: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
