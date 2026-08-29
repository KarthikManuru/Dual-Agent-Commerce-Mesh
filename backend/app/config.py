import os
from pydantic_settings import BaseSettings
from functools import lru_cache

# Path to root .env file
ROOT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
LOCAL_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mesh:meshdev@localhost:5432/commerce_mesh"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://mesh:meshdev@localhost:5432/commerce_mesh"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Razorpay (Phase 2+)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # AI / LLM (Phase 3)
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_REQUIRED: bool = False
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {
        "env_file": (ROOT_ENV_PATH, LOCAL_ENV_PATH, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
