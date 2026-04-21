from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    secret_key: str = "frisco-admin-secret-2024-enterprise"
    algorithm: str = "HS256"
    token_expire_minutes: int = 480  # 8 hours

    admin_username: str = "admin"
    admin_password: str = "admin123"

    db_path: str = str(BASE_DIR / "webapp" / "annotations.db")

    class Config:
        env_file = ".env"

settings = Settings()
