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

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # JWT Authentication
    JWT_SECRET: str = "secret-key-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Origins (comma-separated string in env)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        # Strip trailing slashes and whitespace to avoid strict origin mismatch errors
        return [i.strip().rstrip("/") for i in self.CORS_ORIGINS.split(",") if i.strip()]

settings = Settings()
