from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./collectiq.db"
    access_token_expire_minutes: int = 720
    frontend_origin: str = "http://localhost:5173"

settings = Settings()
