"""
app/core/config.py
------------------
Centralized application settings using Pydantic Settings.
Values are loaded from environment variables or a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration model.
    All fields are populated from environment variables (case-insensitive).
    """

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/attendance_db"

    # --- Application Metadata ---
    APP_NAME: str = "Attendance Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # --- JWT Auth ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Pydantic Settings v2: read from a .env file if present
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton instance — import this everywhere you need config
settings = Settings()
