"""
Email Configuration
Settings for SMTP email notifications
"""
from pydantic_settings import BaseSettings
from typing import Optional


class EmailSettings(BaseSettings):
    """Email configuration settings"""
    
    # SMTP Configuration
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025  # MailHog default for development
    SMTP_USE_TLS: bool = False
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@reims.com"
    SMTP_FROM_NAME: str = "REIMS 2.0"
    
    # Email Features
    EMAIL_ENABLED: bool = True
    EMAIL_DEBUG: bool = False  # If True, logs emails instead of sending
    
    # Notification Preferences
    SEND_ALERT_EMAILS: bool = True
    SEND_DIGEST_EMAILS: bool = True
    SEND_ESCALATION_EMAILS: bool = True
    
    # Digest Settings
    DIGEST_SCHEDULE: str = "daily"  # daily, weekly, or never
    DIGEST_TIME: str = "09:00"  # Time to send digest (24-hour format)
    
    class Config:
        env_file = ".env"
        env_prefix = "EMAIL_"
        extra = "ignore"


# Global email settings instance
email_settings = EmailSettings()


def get_smtp_config() -> dict:
    """Get SMTP configuration dictionary"""
    return {
        "host": email_settings.SMTP_HOST,
        "port": email_settings.SMTP_PORT,
        "use_tls": email_settings.SMTP_USE_TLS,
        "username": email_settings.SMTP_USERNAME,
        "password": email_settings.SMTP_PASSWORD,
        "from_email": email_settings.SMTP_FROM_EMAIL,
        "from_name": email_settings.SMTP_FROM_NAME
    }
