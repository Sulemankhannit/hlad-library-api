
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "HLAD Library Microservice"
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM:str
    ACCESS_TOKEN_EXPIRE_MINUTES:int
    LENDED_DAYS:int
    # This tells Pydantic to read from a .env file at the root level
    model_config = SettingsConfigDict(env_file=".env", enable_decoding="utf-8",extra="ignore")

#instantiate
settings = Settings()