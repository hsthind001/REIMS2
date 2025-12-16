"""
Structured Logging Configuration

Configures structlog for JSON logging with correlation IDs, context, and sampling.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Collection
import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import (
    JSONRenderer,
    TimeStamper,
    add_log_level,
    StackInfoRenderer,
    format_exc_info,
    UnicodeDecoder,
    CallsiteParameterAdder,
    CallsiteParameter
)

# Log directory
LOG_DIR = Path(os.getenv('LOG_DIR', '/var/log/reims2'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file paths
LOG_FILE = LOG_DIR / 'reims2.log'
ERROR_LOG_FILE = LOG_DIR / 'reims2_error.log'

# Log rotation settings
MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 1024 * 1024 * 1024))  # 1GB
BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 30))  # 30 days

# Log sampling rate (0.0 to 1.0)
LOG_SAMPLING_RATE = float(os.getenv('LOG_SAMPLING_RATE', '0.1'))  # 10% for high-volume

# Log level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Enable/disable sensitive data filtering
FILTER_SENSITIVE_DATA = os.getenv('FILTER_SENSITIVE_DATA', 'true').lower() == 'true'


class SensitiveDataFilter:
    """Filter sensitive data from logs"""
    
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'authorization', 'auth',
        'credit_card', 'cc_number', 'ssn', 'social_security',
        'email', 'phone', 'phone_number', 'address', 'zip_code'
    }
    
    SENSITIVE_PATTERNS = [
        r'Bearer\s+[\w-]+',
        r'api[_-]?key[\s:=]+[\w-]+',
        r'password[\s:=]+[^\s]+',
        r'token[\s:=]+[\w-]+'
    ]
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from dictionary"""
        if not FILTER_SENSITIVE_DATA:
            return data
        
        filtered = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key is sensitive
            if any(sensitive in key_lower for sensitive in cls.SENSITIVE_KEYS):
                filtered[key] = '[REDACTED]'
            elif isinstance(value, dict):
                filtered[key] = cls.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    cls.filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Check for sensitive patterns in string values
                filtered_value = value
                for pattern in cls.SENSITIVE_PATTERNS:
                    import re
                    filtered_value = re.sub(pattern, '[REDACTED]', filtered_value, flags=re.IGNORECASE)
                filtered[key] = filtered_value
            else:
                filtered[key] = value
        
        return filtered


class SamplingProcessor:
    """Processor to sample high-volume logs"""
    
    def __init__(self, rate: float = 0.1):
        """
        Initialize sampling processor
        
        Args:
            rate: Sampling rate (0.0 to 1.0). 0.1 = 10% of logs
        """
        self.rate = rate
        self._counter = 0
    
    def __call__(self, logger, method_name, event_dict):
        """Sample logs based on rate"""
        # Always log errors and critical messages
        level = event_dict.get('level', '').lower()
        if level in ('error', 'critical', 'exception'):
            return event_dict
        
        # Sample other logs
        self._counter += 1
        sample_interval = max(1, int(1 / self.rate)) if self.rate > 0 else 1
        if (self._counter % sample_interval) != 0:
            # Skip this log
            raise structlog.DropEvent
        
        return event_dict


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID from contextvars if available"""
    try:
        from app.middleware.correlation_id import get_correlation_id
        correlation_id = get_correlation_id()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
    except (ImportError, AttributeError, KeyError):
        pass
    return event_dict


def add_request_context(logger, method_name, event_dict):
    """Add request context (user_id, query_id, etc.) from contextvars"""
    try:
        from app.middleware.correlation_id import (
            get_user_id, get_query_id, get_conversation_id, get_property_id
        )
        
        # Add user_id if available
        user_id = get_user_id()
        if user_id:
            event_dict['user_id'] = user_id
        
        # Add query_id if available
        query_id = get_query_id()
        if query_id:
            event_dict['query_id'] = query_id
        
        # Add conversation_id if available
        conversation_id = get_conversation_id()
        if conversation_id:
            event_dict['conversation_id'] = conversation_id
        
        # Add property_id if available
        property_id = get_property_id()
        if property_id:
            event_dict['property_id'] = property_id
        
    except (ImportError, AttributeError, KeyError, LookupError):
        pass
    return event_dict


def configure_logging(
    log_level: str = LOG_LEVEL,
    log_to_file: bool = True,
    log_to_console: bool = True,
    sampling_rate: float = LOG_SAMPLING_RATE
):
    """
    Configure structured logging with structlog
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging
        sampling_rate: Sampling rate for high-volume logs (0.0 to 1.0)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO)
    )
    
    # Configure file handlers with rotation
    handlers = []
    
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level, logging.INFO))
        handlers.append(console_handler)
    
    if log_to_file:
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(LOG_FILE),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level, logging.INFO))
        handlers.append(file_handler)
        
        # Error log file (errors and above only)
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(ERROR_LOG_FILE),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        handlers.append(error_handler)
    
    # Configure structlog
    processors = [
        # Add log level
        add_log_level,
        # Logger name is added automatically by structlog
        # Add stack info for exceptions
        StackInfoRenderer(),
        # Format exceptions
        format_exc_info,
        # Decode unicode
        UnicodeDecoder(),
        # Add callsite info (file, line, function)
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME
            ]
        ),
        # Add timestamp
        TimeStamper(fmt="iso"),
        # Add correlation ID
        add_correlation_id,
        # Add request context
        add_request_context,
        # Filter sensitive data
        lambda logger, method_name, event_dict: SensitiveDataFilter.filter_dict(event_dict),
        # Sample high-volume logs (if rate < 1.0)
        SamplingProcessor(rate=sampling_rate) if sampling_rate < 1.0 else lambda logger, method_name, event_dict: event_dict,
        # Render as JSON
        JSONRenderer()
    ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True
    )
    
    # Set handlers for root logger
    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    return structlog.get_logger()


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Initialize logging on import
logger = configure_logging()

