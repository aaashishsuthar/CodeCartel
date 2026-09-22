from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Agent Kautilya Backend"
    DATABASE_URL: str = "sqlite:///./kautilya.db"

settings = Settings()
