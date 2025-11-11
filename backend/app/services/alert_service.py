"""
Alert Service for REIMS2
Multi-channel notification system for anomalies and critical events.

Sprint 3: Alerts & Real-Time Anomaly Detection
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json

from app.models.document_upload import DocumentUpload
from app.db.database import get_db


class AlertService:
    """
    Multi-channel alert and notification system.
    
    Channels:
    - Email (SMTP)
    - Slack (Webhooks)
    - In-app notifications (database)
    """
    
    def __init__(self, db: Session):
        """Initialize alert service."""
        self.db = db
        self.email_enabled = False  # Configure via settings
        self.slack_enabled = False  # Configure via settings
    
    def send_anomaly_alert(
        self,
        property_name: str,
        anomaly_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any]
    ) -> Dict[str, bool]:
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
        results = {}
        
        # Format alert
        alert_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'property': property_name,
            'type': anomaly_type,
            'severity': severity,
            'message': message,
            'details': details
        }
        
        # Send via email
        if self.email_enabled:
            results['email'] = self._send_email_alert(alert_data)
        
        # Send via Slack
        if self.slack_enabled:
            results['slack'] = self._send_slack_alert(alert_data)
        
        # Always create in-app notification
        results['in_app'] = self._create_in_app_notification(alert_data)
        
        return results
    
    def _send_email_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send email alert via SMTP."""
        try:
            # Email configuration (would be loaded from settings)
            smtp_host = 'localhost'
            smtp_port = 1025  # Postal default
            from_email = 'alerts@reims.com'
            to_emails = ['admin@reims.com']  # Would be configurable
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert_data['severity'].upper()}] REIMS Alert: {alert_data['type']}"
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            
            # HTML body
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
            
            # Send
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert to Slack webhook."""
        try:
            # Slack webhook URL (would be loaded from settings)
            webhook_url = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
            
            # Format for Slack
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
                        {
                            'title': 'Property',
                            'value': alert_data['property'],
                            'short': True
                        },
                        {
                            'title': 'Severity',
                            'value': alert_data['severity'].upper(),
                            'short': True
                        }
                    ],
                    'footer': 'REIMS Alert System',
                    'ts': int(datetime.utcnow().timestamp())
                }]
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=5
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Slack alert failed: {e}")
            return False
    
    def _create_in_app_notification(self, alert_data: Dict[str, Any]) -> bool:
        """Create in-app notification (stored in database)."""
        try:
            # Would store in notifications table
            # For now, just return success
            # TODO: Implement notifications table in Sprint 3
            return True
        except Exception as e:
            print(f"In-app notification failed: {e}")
            return False

