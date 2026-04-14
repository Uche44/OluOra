from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "OluNdi"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:maryjesu99@localhost:5432/olundi"
    
    # TikTok Settings
    TIKTOK_CLIENT_KEY: str
    TIKTOK_CLIENT_SECRET: str
    TIKTOK_REDIRECT_URI: str
    
    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
