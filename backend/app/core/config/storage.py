import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from .base import _get_env_or_generate

class StorageSettings(BaseSettings):
    # MinIO Settings - credentials loaded from environment
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_SECURE: bool = True  # Default to secure in production
    MINIO_BUCKET_NAME: str = "reims"

    @field_validator('MINIO_ACCESS_KEY', mode='before')
    @classmethod
    def get_minio_access_key(cls, v):
        return _get_env_or_generate('MINIO_ACCESS_KEY', 'minioadmin')

    @field_validator('MINIO_SECRET_KEY', mode='before')
    @classmethod
    def get_minio_secret_key(cls, v):
        return _get_env_or_generate('MINIO_SECRET_KEY', 'minioadmin')

    @field_validator('MINIO_SECURE', mode='before')
    @classmethod
    def get_minio_secure(cls, v):
        # Default to False only in development
        environment = os.environ.get('ENVIRONMENT', 'development').lower()
        if environment == 'development':
            return os.environ.get('MINIO_SECURE', 'false').lower() == 'true'
        # In production, default to True (HTTPS)
        return os.environ.get('MINIO_SECURE', 'true').lower() == 'true'
