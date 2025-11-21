from pydantic_settings import BaseSettings
from typing import Optional, List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "REIMS API"
    
    # Database Settings
    POSTGRES_USER: str = "reims"
    POSTGRES_PASSWORD: str = "reims"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5433"
    POSTGRES_DB: str = "reims"
    
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
    
    # MinIO Settings
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "reims"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000"]
    
    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # Security
    # IMPORTANT: Set SECRET_KEY environment variable in production!
    SECRET_KEY: str = "CHANGE-THIS-IN-PRODUCTION-USE-ENV-VAR"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator('SECRET_KEY', mode='before')
    @classmethod
    def validate_secret_key(cls, v):
        if v in ["your-secret-key-change-this-in-production", "CHANGE-THIS-IN-PRODUCTION-USE-ENV-VAR"]:
            import os
            env_key = os.environ.get('SECRET_KEY')
            if env_key:
                return env_key
            import warnings
            warnings.warn("SECRET_KEY not set! Using default value. Set SECRET_KEY environment variable in production!")
        return v

    # LLM API Settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    LLM_MODEL: str = "gpt-4-turbo-preview"  # gpt-4-turbo-preview, gpt-4, claude-3-5-sonnet-20241022
    LLM_TEMPERATURE: float = 0.3  # Lower temperature for factual summarization
    LLM_MAX_TOKENS: int = 4000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            # Ensure API keys are read from environment
            if field_name in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']:
                return raw_val
            return cls.json_loads(raw_val)


settings = Settings()

