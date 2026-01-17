import os
import secrets
from typing import Union, List
from pydantic_settings import BaseSettings
from pydantic import field_validator

class SecuritySettings(BaseSettings):
    # CORS Settings
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    # Security - SECRET_KEY MUST be set via environment variable
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Session security settings
    SESSION_HTTPS_ONLY: bool = True  # True in production
    SESSION_SAME_SITE: str = "lax"  # "strict", "lax", or "none"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 1 day default

    @field_validator('SECRET_KEY', mode='before')
    @classmethod
    def validate_secret_key(cls, v):
        # Prioritize the value passed by Pydantic (from .env or env var)
        if isinstance(v, str) and v:
            if len(v) < 32:
                 if len(v) < 32:
                    raise ValueError(
                        "SECRET_KEY must be at least 32 characters long for security"
                    )
            return v
            
        # Fallback to os.environ if v is empty
        env_key = os.environ.get('SECRET_KEY')
        if env_key:
            # Validate key strength
            if len(env_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters long for security"
                )
            return env_key

        # Check if we're in production
        environment = os.environ.get('ENVIRONMENT', 'development').lower()
        if environment == 'production':
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY must be set via environment variable in production. "
                "Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        # Development only: generate a random key (not for production!)
        import warnings
        warnings.warn(
            "WARNING: Using auto-generated SECRET_KEY for development. "
            "Set SECRET_KEY environment variable for production!",
            UserWarning
        )
        return secrets.token_urlsafe(64)

    @field_validator('SESSION_HTTPS_ONLY', mode='before')
    @classmethod
    def get_session_https_only(cls, v):
        # Prioritize the value passed by Pydantic (from .env or env var)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() == 'true'
            
        # Fallback to environment variable if v is None/Empty for some reason
        # Default to False only in development
        environment = os.environ.get('ENVIRONMENT', 'development').lower()
        if environment == 'development':
            return os.environ.get('SESSION_HTTPS_ONLY', 'false').lower() == 'true'
        # In production, default to True
        return os.environ.get('SESSION_HTTPS_ONLY', 'true').lower() == 'true'
