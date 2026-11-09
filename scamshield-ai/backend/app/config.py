from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./scamshield.db"
    jwt_secret: str = "development-only-change-me-please-32chars"
    jwt_expire_minutes: int = 1440
    frontend_origins: str = "http://localhost:3000"
    model_path: str = "app/ml/artifacts/message_model.joblib"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
