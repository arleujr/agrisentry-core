from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Core application settings mapped from environment variables.
    Pydantic automatically validates data types on startup.
    """
    PROJECT_NAME: str = "AgriPlanum Core - AI & Data Quality"
    VERSION: str = "1.0.0"
    
    # Notice the prefix: 'postgresql+asyncpg' is mandatory for async SQLAlchemy
    DATABASE_URL: str 
    # Tuning for the Background Worker
    WORKER_SLEEP_SECONDS: int = 5
    WORKER_BATCH_SIZE: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Singleton instance to be imported across the application
settings = Settings()