from typing import Optional, List
from pydantic_settings import BaseSettings

class AISettings(BaseSettings):
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
