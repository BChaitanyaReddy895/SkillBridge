from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "SkillBridge Attendance API"
    environment: str = "local"

    database_url: str = "sqlite:///./skillbridge.db"

    jwt_secret: str = "change-me-please"
    jwt_algorithm: str = "HS256"
    jwt_expires_hours: int = 24

    monitoring_api_key: str = "monitoring-key-change-me"
    monitoring_jwt_secret: str = "change-me-monitoring"
    monitoring_jwt_expires_hours: int = 1


settings = Settings()

