from .app_config import AppSettings
from .database import DatabaseSettings
from .storage import StorageSettings
from .security import SecuritySettings
from .ai import AISettings

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
