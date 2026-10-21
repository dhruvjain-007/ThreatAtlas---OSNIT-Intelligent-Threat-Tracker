from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the repository or container app directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if (ROOT_DIR.parent / "backend").exists():
    ROOT_DIR = ROOT_DIR.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "OSINT Threat Intelligence Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # CORS Settings
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database Settings
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGODB_URL: Optional[str] = None
    MONGO_DB_NAME: str = "threat_atlas"
    DATABASE_NAME: Optional[str] = None

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # SQLite GeoNames Cache
    GEONAMES_DB_PATH: str = "data/geonames.sqlite"

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
                except Exception:
                    pass
            return [origin.strip().rstrip("/") for origin in v_str.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [str(origin).strip().rstrip("/") for origin in v if str(origin).strip()]
        return []

    @model_validator(mode="after")
    def sync_database_fields(self) -> "Settings":
        if self.MONGODB_URL:
            self.MONGO_URI = self.MONGODB_URL
        else:
            self.MONGODB_URL = self.MONGO_URI

        if self.DATABASE_NAME:
            self.MONGO_DB_NAME = self.DATABASE_NAME
        else:
            self.DATABASE_NAME = self.MONGO_DB_NAME
        return self

    model_config = SettingsConfigDict(
        env_file=(".env", str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
