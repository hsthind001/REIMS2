import os
from pydantic_settings import BaseSettings

def _get_env_or_generate(key: str, default_dev_value: str) -> str:
    """Get value from environment or return development default.
    In production (ENVIRONMENT=production), raises error if not set."""
    env_value = os.environ.get(key)
    if env_value:
        return env_value

    # Check if we're in production
    environment = os.environ.get('ENVIRONMENT', 'development').lower()
    if environment == 'production':
        raise ValueError(
            f"SECURITY ERROR: {key} must be set via environment variable in production. "
            f"Set ENVIRONMENT=development for local development with defaults."
        )

    return default_dev_value
