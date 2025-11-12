from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'tv.db'}"

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
