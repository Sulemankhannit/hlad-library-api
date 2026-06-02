
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):  # why not dotenv? cz,settings, prevent runtime crash, and validates the type of envs too.
    PROJECT_NAME: str = "HLAD Library Microservice"
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM:str
    ACCESS_TOKEN_EXPIRE_MINUTES:int
    LENDED_DAYS:int
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    # This tells Pydantic to read from a .env file at the root level
    model_config = SettingsConfigDict(env_file=".env", enable_decoding="utf-8",extra="ignore")

#instantiate
settings = Settings()