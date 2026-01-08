"""
Configuration for Best-in-Class NLQ System with Temporal Support

This module defines all configurations for the multi-agent RAG system including:
- LLM providers and models
- Vector store settings
- Knowledge graph configuration
- Temporal query processing
- Agent-specific settings
"""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from pydantic import Field


class NLQConfig(BaseSettings):
    """
    Natural Language Query System Configuration

    Supports multiple LLM providers with fallback chain:
    1. Groq (Llama 3.3 70B) - Primary (free, ultra-fast)
    2. OpenAI (GPT-4 Turbo) - Fallback
    3. Anthropic (Claude 3.5 Sonnet) - Fallback
    4. Local Ollama (Llama 3.1 8B) - Privacy mode
    """

    # ============================================================================
    # LLM PROVIDER CONFIGURATION
    # ============================================================================

    # Primary LLM Provider
    PRIMARY_LLM_PROVIDER: Literal["groq", "openai", "anthropic", "ollama"] = Field(
        default="groq",
        description="Primary LLM provider for NLQ queries"
    )

    # Groq Configuration (Free, Ultra-Fast)
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key for Llama 3.3 70B (800+ tokens/sec)"
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model name"
    )
    GROQ_MAX_TOKENS: int = Field(
        default=8192,
        description="Max output tokens for Groq"
    )
    GROQ_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for Groq (lower = more deterministic)"
    )

    # OpenAI Configuration (Fallback)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model for complex queries"
    )
    OPENAI_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for OpenAI"
    )

    # Anthropic Configuration (Fallback)
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model for reasoning"
    )

    # Ollama Configuration (Local/Privacy)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL for local models"
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.1:8b",
        description="Local Ollama model"
    )

    # ============================================================================
    # EMBEDDINGS CONFIGURATION
    # ============================================================================

    EMBEDDING_PROVIDER: Literal["jina", "openai", "huggingface", "local"] = Field(
        default="jina",
        description="Embedding provider (jina = free, SOTA)"
    )

    # Jina Embeddings V3 (Free, SOTA)
    JINA_API_KEY: Optional[str] = Field(
        default=None,
        description="Jina AI API key (free tier available)"
    )
    JINA_MODEL: str = Field(
        default="jina-embeddings-v3",
        description="Jina embedding model (8192 context)"
    )
    JINA_DIMENSIONS: int = Field(
        default=1024,
        description="Embedding dimensions"
    )

    # HuggingFace Embeddings (Open-source)
    HUGGINGFACE_MODEL: str = Field(
        default="BAAI/bge-large-en-v1.5",
        description="HuggingFace embedding model"
    )

    # OpenAI Embeddings (Paid)
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model"
    )

    # ============================================================================
    # VECTOR STORE CONFIGURATION (QDRANT)
    # ============================================================================

    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant server host"
    )
    QDRANT_PORT: int = Field(
        default=6333,
        description="Qdrant server port"
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key (for cloud deployment)"
    )
    QDRANT_COLLECTION_PREFIX: str = Field(
        default="reims_nlq",
        description="Prefix for Qdrant collections"
    )

    # Collections
    QDRANT_DOCUMENTS_COLLECTION: str = Field(
        default="reims_nlq_documents",
        description="Collection for reconciliation documents"
    )
    QDRANT_RULES_COLLECTION: str = Field(
        default="reims_nlq_rules",
        description="Collection for validation rules"
    )
    QDRANT_FORMULAS_COLLECTION: str = Field(
        default="reims_nlq_formulas",
        description="Collection for financial formulas"
    )
    QDRANT_QUERIES_COLLECTION: str = Field(
        default="reims_nlq_queries",
        description="Collection for cached queries"
    )

    # Vector search parameters
    VECTOR_SEARCH_TOP_K: int = Field(
        default=10,
        description="Number of top results to retrieve from vector search"
    )
    VECTOR_SEARCH_SCORE_THRESHOLD: float = Field(
        default=0.7,
        description="Minimum similarity score threshold (0-1)"
    )

    # ============================================================================
    # KNOWLEDGE GRAPH CONFIGURATION (NEO4J)
    # ============================================================================

    NEO4J_ENABLED: bool = Field(
        default=True,
        description="Enable Neo4j knowledge graph"
    )
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    NEO4J_USER: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    NEO4J_PASSWORD: str = Field(
        default="password",
        description="Neo4j password"
    )
    NEO4J_DATABASE: str = Field(
        default="reims",
        description="Neo4j database name"
    )

    # ============================================================================
    # TEMPORAL QUERY CONFIGURATION
    # ============================================================================

    # Date parsing and normalization
    ENABLE_TEMPORAL_UNDERSTANDING: bool = Field(
        default=True,
        description="Enable natural language date/time parsing"
    )
    TIMEZONE: str = Field(
        default="UTC",
        description="Default timezone for temporal queries"
    )
    FISCAL_YEAR_START_MONTH: int = Field(
        default=1,
        description="Fiscal year start month (1=January)"
    )

    # Temporal query patterns
    TEMPORAL_PATTERNS: list[str] = Field(
        default=[
            r"in (\w+) (\d{4})",  # "in November 2025"
            r"during (\d{4})",  # "during 2025"
            r"between (\w+) and (\w+)",  # "between August and December"
            r"last (\d+) (months?|years?|quarters?)",  # "last 3 months"
            r"(Q[1-4]) (\d{4})",  # "Q4 2025"
            r"year to date|ytd",  # "year to date"
            r"month to date|mtd",  # "month to date"
            r"(\d{4})-(\d{2})-(\d{2})",  # "2025-11-30"
        ],
        description="Regex patterns for temporal expression extraction"
    )

    # ============================================================================
    # HYBRID RETRIEVAL CONFIGURATION
    # ============================================================================

    ENABLE_HYBRID_SEARCH: bool = Field(
        default=True,
        description="Enable hybrid search (vector + BM25)"
    )

    # BM25 parameters
    BM25_K1: float = Field(
        default=1.5,
        description="BM25 k1 parameter (term frequency saturation)"
    )
    BM25_B: float = Field(
        default=0.75,
        description="BM25 b parameter (length normalization)"
    )

    # Hybrid fusion
    HYBRID_ALPHA: float = Field(
        default=0.5,
        description="Weight for vector search vs BM25 (0=BM25 only, 1=vector only)"
    )

    # Reranking
    ENABLE_RERANKING: bool = Field(
        default=True,
        description="Enable reranking of retrieved results"
    )
    RERANKER_MODEL: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="Reranker model"
    )
    RERANKER_TOP_K: int = Field(
        default=5,
        description="Final number of results after reranking"
    )

    # ============================================================================
    # AGENT CONFIGURATION
    # ============================================================================

    # Agent routing
    ENABLE_MULTI_AGENT: bool = Field(
        default=True,
        description="Enable multi-agent system (vs single agent)"
    )

    # Agent domains
    AGENT_DOMAINS: list[str] = Field(
        default=[
            "financial_data",
            "audit_trail",
            "formulas_calculations",
            "metrics_kpi",
            "validation_rules",
            "extraction_process",
            "anomaly_detection",
            "alerts_warnings",
            "reconciliation",
            "document_intelligence",
            "cross_statement_analysis"
        ],
        description="Specialized agent domains"
    )

    # Query decomposition
    ENABLE_QUERY_DECOMPOSITION: bool = Field(
        default=True,
        description="Decompose complex queries into sub-queries"
    )
    MAX_SUBQUERIES: int = Field(
        default=5,
        description="Maximum number of sub-queries to generate"
    )

    # ============================================================================
    # VALIDATION & QUALITY CONFIGURATION
    # ============================================================================

    ENABLE_SELF_VALIDATION: bool = Field(
        default=True,
        description="Enable answer validation before returning"
    )
    MIN_CONFIDENCE_SCORE: float = Field(
        default=0.7,
        description="Minimum confidence score to return answer (0-1)"
    )
    ENABLE_HALLUCINATION_DETECTION: bool = Field(
        default=True,
        description="Check for hallucinations in generated answers"
    )
    ENABLE_CALCULATION_VERIFICATION: bool = Field(
        default=True,
        description="Verify numerical calculations in answers"
    )

    # ============================================================================
    # TEXT-TO-SQL CONFIGURATION
    # ============================================================================

    ENABLE_SQL_GENERATION: bool = Field(
        default=True,
        description="Enable automatic SQL query generation"
    )
    SQL_PROVIDER: Literal["vanna", "langchain", "custom"] = Field(
        default="vanna",
        description="SQL generation provider"
    )
    SQL_MAX_ROWS: int = Field(
        default=1000,
        description="Maximum rows to return from SQL queries"
    )
    SQL_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="SQL query execution timeout"
    )
    ENABLE_SQL_EXPLAIN: bool = Field(
        default=True,
        description="Show SQL query explanation to users"
    )

    # ============================================================================
    # CACHING CONFIGURATION
    # ============================================================================

    ENABLE_SEMANTIC_CACHE: bool = Field(
        default=True,
        description="Enable semantic caching for similar queries"
    )
    CACHE_SIMILARITY_THRESHOLD: float = Field(
        default=0.95,
        description="Minimum similarity to use cached result (0-1)"
    )
    CACHE_TTL_HOURS: int = Field(
        default=24,
        description="Cache time-to-live in hours"
    )
    ENABLE_REDIS_CACHE: bool = Field(
        default=True,
        description="Use Redis for query result caching"
    )

    # ============================================================================
    # CONTEXT WINDOW & TOKEN LIMITS
    # ============================================================================

    MAX_CONTEXT_TOKENS: int = Field(
        default=32000,
        description="Maximum context tokens for LLM"
    )
    MAX_OUTPUT_TOKENS: int = Field(
        default=4096,
        description="Maximum output tokens"
    )
    CHUNK_SIZE: int = Field(
        default=1000,
        description="Document chunk size for embeddings"
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        description="Overlap between chunks"
    )

    # ============================================================================
    # CONVERSATION & HISTORY
    # ============================================================================

    ENABLE_CONVERSATION_MEMORY: bool = Field(
        default=True,
        description="Enable conversation context tracking"
    )
    MAX_CONVERSATION_HISTORY: int = Field(
        default=10,
        description="Maximum number of previous messages to include"
    )
    CONVERSATION_SUMMARY_THRESHOLD: int = Field(
        default=20,
        description="Summarize conversation after N messages"
    )

    # ============================================================================
    # MONITORING & OBSERVABILITY
    # ============================================================================

    ENABLE_TRACING: bool = Field(
        default=True,
        description="Enable LLM tracing with Phoenix AI"
    )
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # ============================================================================
    # PERFORMANCE & CONCURRENCY
    # ============================================================================

    MAX_CONCURRENT_AGENTS: int = Field(
        default=3,
        description="Maximum concurrent agents per query"
    )
    AGENT_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Maximum time per agent execution"
    )
    TOTAL_QUERY_TIMEOUT_SECONDS: int = Field(
        default=120,
        description="Maximum total query processing time"
    )

    # ============================================================================
    # CHART OF ACCOUNTS & DOMAIN KNOWLEDGE
    # ============================================================================

    COA_CATEGORIES: dict[str, list[str]] = Field(
        default={
            "cash_accounts": ["0122", "0123", "0124", "0125"],
            "restricted_cash": ["1310", "1320", "1330", "1340"],
            "receivables": ["0305", "0310", "0315"],
            "property_assets": ["1410", "1420", "1430"],
            "accumulated_depreciation": ["1411", "1421", "1431"],
            "current_liabilities": ["2010", "2020", "2030"],
            "long_term_debt": ["2510", "2520", "2530"],
            "equity_accounts": ["3010", "3020", "3030", "3040"]
        },
        description="Chart of accounts category mappings"
    )

    # Financial statement types
    STATEMENT_TYPES: list[str] = Field(
        default=[
            "balance_sheet",
            "income_statement",
            "cash_flow",
            "rent_roll",
            "mortgage_statement"
        ],
        description="Supported financial statement types"
    )

    class Config:
        env_file = ".env"
        env_prefix = "NLQ_"
        case_sensitive = False


# Singleton instance
nlq_config = NLQConfig()


# Helper functions for temporal query processing
def get_fiscal_quarter(month: int, year: int) -> tuple[int, int]:
    """Get fiscal quarter and year for a given month"""
    fiscal_start = nlq_config.FISCAL_YEAR_START_MONTH
    if month >= fiscal_start:
        fiscal_year = year
        quarter = ((month - fiscal_start) // 3) + 1
    else:
        fiscal_year = year - 1
        quarter = ((12 - fiscal_start + month) // 3) + 1
    return quarter, fiscal_year


def get_period_range(period_type: str, reference_date=None) -> tuple[str, str]:
    """
    Get date range for common period types

    Args:
        period_type: 'ytd', 'mtd', 'qtd', 'last_month', 'last_quarter', etc.
        reference_date: Reference date (default: today)

    Returns:
        (start_date, end_date) as ISO strings
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    if reference_date is None:
        reference_date = datetime.now()

    if period_type == "ytd":
        start = datetime(reference_date.year, nlq_config.FISCAL_YEAR_START_MONTH, 1)
        end = reference_date
    elif period_type == "mtd":
        start = datetime(reference_date.year, reference_date.month, 1)
        end = reference_date
    elif period_type == "qtd":
        quarter, fiscal_year = get_fiscal_quarter(reference_date.month, reference_date.year)
        quarter_start_month = nlq_config.FISCAL_YEAR_START_MONTH + (quarter - 1) * 3
        if quarter_start_month > 12:
            quarter_start_month -= 12
            fiscal_year += 1
        start = datetime(fiscal_year, quarter_start_month, 1)
        end = reference_date
    elif period_type == "last_month":
        start = (reference_date - relativedelta(months=1)).replace(day=1)
        end = reference_date.replace(day=1) - timedelta(days=1)
    elif period_type == "last_quarter":
        quarter, fiscal_year = get_fiscal_quarter(reference_date.month, reference_date.year)
        prev_quarter = quarter - 1 if quarter > 1 else 4
        if prev_quarter == 4:
            fiscal_year -= 1
        quarter_start_month = nlq_config.FISCAL_YEAR_START_MONTH + (prev_quarter - 1) * 3
        start = datetime(fiscal_year, quarter_start_month, 1)
        end = start + relativedelta(months=3) - timedelta(days=1)
    else:
        raise ValueError(f"Unknown period type: {period_type}")

    return start.date().isoformat(), end.date().isoformat()
