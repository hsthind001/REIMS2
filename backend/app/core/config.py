from pydantic_settings import BaseSettings
from typing import Optional, List, Union
from pydantic import field_validator
import os
import secrets


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


class Settings(BaseSettings):
    # Environment - MUST be set to 'production' in production deployments
    ENVIRONMENT: str = "development"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "REIMS API"

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
    SESSION_SAME_SITE: str = "strict"  # "strict", "lax", or "none"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 1 day default

    @field_validator('SECRET_KEY', mode='before')
    @classmethod
    def validate_secret_key(cls, v):
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
        # Default to False only in development
        environment = os.environ.get('ENVIRONMENT', 'development').lower()
        if environment == 'development':
            return os.environ.get('SESSION_HTTPS_ONLY', 'false').lower() == 'true'
        # In production, default to True
        return os.environ.get('SESSION_HTTPS_ONLY', 'true').lower() == 'true'

    # LLM API Settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None  # Groq Cloud API (free tier, 800 tokens/sec)
    LLM_PROVIDER: str = "ollama"  # "ollama", "groq", "openai", or "anthropic"
    LLM_MODEL: str = "llama3.2:3b-instruct-q4_K_M"  # Ollama model name (using available model)
    LLM_TEMPERATURE: float = 0.3  # Lower temperature for factual summarization
    LLM_MAX_TOKENS: int = 4000

    # Ollama Configuration (Local LLM)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2:3b-instruct-q4_K_M"  # Currently available model
    OLLAMA_GPU_LAYERS: int = -1  # -1 = all layers on GPU, 0 = CPU only
    OLLAMA_NUM_THREADS: int = 8  # CPU threads for inference

    # LLM Performance Settings
    LLM_ENABLE_STREAMING: bool = True  # Stream responses for real-time UI
    LLM_ENABLE_CACHING: bool = True  # Cache LLM responses (semantic caching)
    LLM_CACHE_TTL_HOURS: int = 24  # Cache duration
    LLM_AUTO_SELECT: bool = True  # Automatically choose model based on task
    
    # External API Keys (Optional - for higher rate limits)
    CENSUS_API_KEY: Optional[str] = None  # Optional - Census API works without key for basic queries
    FRED_API_KEY: Optional[str] = None  # Required for FRED economic indicators
    BLS_API_KEY: Optional[str] = None  # Optional - Bureau of Labor Statistics
    GOOGLE_PLACES_API_KEY: Optional[str] = None  # Optional - Google Places API
    
    # ============================================================================
    # ANOMALY DETECTION ENHANCEMENT CONFIGURATION
    # ============================================================================
    
    # ---------- PyOD & ML Configuration ----------
    PYOD_ENABLED: bool = True
    PYOD_LLM_MODEL_SELECTION: bool = False  # Use LLM for intelligent model selection
    # OPENAI_API_KEY already defined above for LLM model selection
    
    # ---------- GPU Acceleration ----------
    ANOMALY_USE_GPU: bool = False  # Set to true if NVIDIA GPU available
    GPU_DEVICE_ID: int = 0  # GPU device index (0-based)
    PYTORCH_CUDA_AVAILABLE: bool = False  # Auto-detected by PyTorch
    
    # ---------- Model Caching ----------
    MODEL_CACHE_ENABLED: bool = True
    MODEL_CACHE_TTL_DAYS: int = 30  # Model cache expiration (days)
    INCREMENTAL_LEARNING_ENABLED: bool = True
    BATCH_SIZE: int = 32  # Batch size for deep learning models
    MAX_EPOCHS: int = 50  # Max training epochs for neural networks
    
    # ---------- XAI (Explainability) Configuration ----------
    SHAP_ENABLED: bool = False  # Enable SHAP explanations (computationally intensive)
    LIME_ENABLED: bool = False  # Enable LIME explanations (fast, on-demand)
    XAI_BACKGROUND_SAMPLES: int = 100  # Number of background samples for SHAP
    
    # ---------- Active Learning ----------
    ACTIVE_LEARNING_ENABLED: bool = False
    ADAPTIVE_THRESHOLDS_ENABLED: bool = False
    AUTO_SUPPRESSION_ENABLED: bool = False  # Auto-suppress learned false positives
    AUTO_SUPPRESSION_CONFIDENCE_THRESHOLD: float = 0.8  # Confidence threshold for auto-suppression (0-1)
    FEEDBACK_LOOKBACK_DAYS: int = 90  # Days to look back for feedback analysis
    
    # ---------- Cross-Property Intelligence ----------
    PORTFOLIO_BENCHMARKS_ENABLED: bool = False
    BENCHMARK_REFRESH_SCHEDULE: str = '0 2 1 * *'  # Cron: 2 AM on 1st of month
    BENCHMARK_MIN_PROPERTIES: int = 3  # Minimum properties required for benchmarking
    
    # ---------- LayoutLM Configuration ----------
    LAYOUTLM_ENABLED: bool = False
    LAYOUTLM_MODEL_PATH: str = "/models/layoutlmv3-reims-finetuned"  # Path to fine-tuned model
    LAYOUTLM_CONFIDENCE_THRESHOLD: float = 0.75  # Minimum confidence for coordinate predictions
    LAYOUTLM_USE_PRETRAINED: bool = True  # Use pre-trained model if fine-tuned not available
    
    # ---------- Batch Processing ----------
    BATCH_PROCESSING_CHUNK_SIZE: int = 10  # Number of documents to process in parallel
    BATCH_PROCESSING_MAX_CONCURRENT: int = 3  # Maximum concurrent batch jobs
    BATCH_PROCESSING_TIMEOUT_MINUTES: int = 60  # Timeout for batch jobs

    # ---------- Anomaly Threshold Overrides ----------
    ANOMALY_Z_SCORE_THRESHOLD: float = 2.0
    ANOMALY_PERCENTAGE_CHANGE_THRESHOLD: float = 0.15

    # ---------- Alert Channel Configuration ----------
    ALERT_EMAIL_ENABLED: bool = True
    ALERT_SLACK_ENABLED: bool = False
    ALERT_SLACK_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL_RECIPIENTS: List[str] = ["admin@reims.com"]
    ALERT_IN_APP_ENABLED: bool = True

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

    @field_validator("ALERT_EMAIL_RECIPIENTS", mode="before")
    @classmethod
    def _parse_alert_email_recipients(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return [email.strip() for email in v if isinstance(email, str) and email.strip()]
        return v


settings = Settings()
