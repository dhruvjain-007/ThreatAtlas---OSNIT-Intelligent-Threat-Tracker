from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "OSINT Threat Intelligence Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "threat_atlas"

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # SQLite GeoNames Cache
    GEONAMES_DB_PATH: str = "data/geonames.sqlite"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
