# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "HLAD Library Microservice"
    DATABASE_URL: str
    JWT_SECRET: str
    
    # This tells Pydantic to read from a .env file at the root level
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# We instantiate it once. When imported, it immediately validates the environment.
settings = Settings()