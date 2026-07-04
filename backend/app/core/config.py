from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "dev"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Resend API
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str

    # CORS Origins (comma-separated string in env)
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [i.strip() for i in self.CORS_ORIGINS.split(",") if i.strip()]

settings = Settings()
