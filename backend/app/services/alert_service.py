"""
Alert Service for REIMS2
Multi-channel notification system for anomalies and critical events.

Sprint 3: Alerts & Real-Time Anomaly Detection
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json

from app.core.config import settings
from app.core.email_config import email_settings, get_smtp_config
from app.models.notification import Notification


class AlertService:
    """
    Multi-channel alert and notification system.
    
    Channels:
    - Email (SMTP)
    - Slack (Webhooks)
    - In-app notifications (database)
    """
    
    def __init__(self, db: Session):
        """Initialize alert service with configurable channels."""
        self.db = db
        self.email_enabled = settings.ALERT_EMAIL_ENABLED and email_settings.EMAIL_ENABLED
        self.email_recipients = settings.ALERT_EMAIL_RECIPIENTS or []
        self.slack_webhook = settings.ALERT_SLACK_WEBHOOK_URL
        self.slack_enabled = settings.ALERT_SLACK_ENABLED and bool(self.slack_webhook)
        self.in_app_enabled = settings.ALERT_IN_APP_ENABLED
        self.smtp_config = get_smtp_config()
    
    def send_anomaly_alert(
        self,
        property_name: str,
        anomaly_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send alert across all configured channels.
        
        Args:
            property_name: Property name
            anomaly_type: Type of anomaly detected
            severity: Severity level (critical, high, medium, low)
            message: Alert message
            details: Additional details dict
            
        Returns:
            Dict of channel delivery status
        """
        results: Dict[str, Any] = {}
        
        alert_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'property': property_name,
            'type': anomaly_type,
            'severity': severity,
            'message': message,
            'details': details
        }
        
        if self.email_enabled and self.email_recipients:
            results['email'] = self._send_email_alert(alert_data)
        else:
            results['email'] = {
                "success": False,
                "skipped": True,
                "reason": "Email disabled or no recipients configured"
            }
        
        if self.slack_enabled:
            results['slack'] = self._send_slack_alert(alert_data)
        else:
            results['slack'] = {
                "success": False,
                "skipped": True,
                "reason": "Slack disabled or webhook missing"
            }
        
        results['in_app'] = self._create_in_app_notification(alert_data)
        
        return results
    
    def _send_email_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email alert via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{alert_data['severity'].upper()}] REIMS Alert: {alert_data['type']}"
        msg['From'] = self.smtp_config.get('from_email', 'noreply@reims.com')
        msg['To'] = ', '.join(self.email_recipients)
        
        html = f"""
        <html>
          <body>
            <h2>REIMS Anomaly Alert</h2>
            <p><strong>Property:</strong> {alert_data['property']}</p>
            <p><strong>Type:</strong> {alert_data['type']}</p>
            <p><strong>Severity:</strong> <span style="color: red;">{alert_data['severity']}</span></p>
            <p><strong>Message:</strong> {alert_data['message']}</p>
            <h3>Details:</h3>
            <pre>{json.dumps(alert_data['details'], indent=2)}</pre>
            <p><small>Timestamp: {alert_data['timestamp']}</small></p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        if email_settings.EMAIL_DEBUG:
            return {
                "success": True,
                "debug": True,
                "payload": html
            }
        
        try:
            server = smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'], timeout=10)
            if self.smtp_config.get('use_tls'):
                server.starttls()
            username = self.smtp_config.get('username')
            password = self.smtp_config.get('password')
            if username and password:
                server.login(username, password)
            server.send_message(msg)
            server.quit()
            return {"success": True, "recipients": len(self.email_recipients)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert to Slack webhook."""
        try:
            color = {
                'critical': 'danger',
                'high': 'warning',
                'medium': '#FFA500',
                'low': 'good'
            }.get(alert_data['severity'], 'warning')
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': f"REIMS Anomaly: {alert_data['type']}",
                    'text': alert_data['message'],
                    'fields': [
                        {'title': 'Property', 'value': alert_data['property'], 'short': True},
                        {'title': 'Severity', 'value': alert_data['severity'].upper(), 'short': True}
                    ],
                    'footer': 'REIMS Alert System',
                    'ts': int(datetime.utcnow().timestamp())
                }]
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=5
            )
            
            return {"success": response.status_code == 200, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_in_app_notification(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist notification for the UI."""
        if not self.in_app_enabled:
            return {"success": False, "skipped": True, "reason": "In-app notifications disabled"}
        
        try:
            notification = Notification(
                user_id=None,
                type="anomaly_alert",
                severity=alert_data['severity'],
                title=f"{alert_data['severity'].upper()} • {alert_data['type']}",
                message=alert_data['message'],
                metadata_json={
                    "property": alert_data['property'],
                    "details": alert_data['details'],
                    "timestamp": alert_data['timestamp']
                }
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            return {"success": True, "notification_id": notification.id}
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
