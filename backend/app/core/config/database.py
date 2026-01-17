from pydantic_settings import BaseSettings
from pydantic import field_validator
from .base import _get_env_or_generate

class DatabaseSettings(BaseSettings):
    # Database Settings - credentials loaded from environment
    # In development: defaults to 'reims', in production: MUST be set via env vars
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5433"
    POSTGRES_DB: str = "reims"

    @field_validator('POSTGRES_USER', mode='before')
    @classmethod
    def get_postgres_user(cls, v):
        return _get_env_or_generate('POSTGRES_USER', 'reims')

    @field_validator('POSTGRES_PASSWORD', mode='before')
    @classmethod
    def get_postgres_password(cls, v):
        return _get_env_or_generate('POSTGRES_PASSWORD', 'reims')

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
