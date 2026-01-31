import os
from .app_config import AppSettings
from .database import DatabaseSettings
from .storage import StorageSettings
from .security import SecuritySettings
from .ai import AISettings


def validate_production_config() -> None:
    """
    Fail fast in prod/staging if required env vars are missing.
    Called at startup; raises ValueError with clear message.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    if env not in ("production", "staging"):
        return

    required = [
        ("SECRET_KEY", "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""),
        ("POSTGRES_USER", "Database user"),
        ("POSTGRES_PASSWORD", "Database password"),
        ("POSTGRES_SERVER", "Database host"),
    ]
    missing = []
    for key, hint in required:
        if not os.environ.get(key):
            missing.append(f"  {key} ({hint})")
    if missing:
        raise ValueError(
            f"SECURITY ERROR: In {env}, these required env vars must be set:\n" + "\n".join(missing)
        )


class Settings(AppSettings, DatabaseSettings, StorageSettings, SecuritySettings, AISettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            # Ensure API keys are read from environment
            if field_name in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'FRED_API_KEY', 'CENSUS_API_KEY']:
                return raw_val
            return cls.json_loads(raw_val)
