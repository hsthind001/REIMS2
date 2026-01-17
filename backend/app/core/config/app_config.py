from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator

class AppSettings(BaseSettings):
    # Environment - MUST be set to 'production' in production deployments
    ENVIRONMENT: str = "development"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "REIMS API"

    # ---------- Alert Channel Configuration ----------
    ALERT_EMAIL_ENABLED: bool = True
    ALERT_SLACK_ENABLED: bool = False
    ALERT_SLACK_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL_RECIPIENTS: List[str] = ["admin@reims.com"]
    ALERT_IN_APP_ENABLED: bool = True

    @field_validator("ALERT_EMAIL_RECIPIENTS", mode="before")
    @classmethod
    def _parse_alert_email_recipients(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return [email.strip() for email in v if isinstance(email, str) and email.strip()]
        return v
