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
