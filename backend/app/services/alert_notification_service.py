"""
Enhanced Alert Notification Service
Multi-channel notification system for alerts with templates and delivery tracking
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import json

from app.models.committee_alert import CommitteeAlert, CommitteeType, AlertSeverity
from app.models.alert_history import AlertHistory
from app.models.property import Property
from app.core.email_config import get_smtp_config, email_settings

logger = logging.getLogger(__name__)


class AlertNotificationService:
    """
    Enhanced Alert Notification Service
    
    Supports multiple notification channels:
    - Email (HTML templates)
    - In-app notifications
    - Webhooks (for integrations)
    - SMS (future)
    """
    
    def __init__(self, db: Session, smtp_config: Optional[Dict] = None):
        self.db = db
        self.smtp_config = smtp_config or get_smtp_config()
        self.email_enabled = email_settings.EMAIL_ENABLED
        self.email_debug = email_settings.EMAIL_DEBUG
    
    def notify_alert_created(self, alert: CommitteeAlert) -> Dict[str, Any]:
        """
        Send notifications when a new alert is created
        
        Returns delivery status for each channel
        """
        results = {
            "alert_id": alert.id,
            "channels": {},
            "success": False
        }
        
        try:
            # Email notification (if enabled)
            if self.email_enabled and email_settings.SEND_ALERT_EMAILS:
                email_result = self._send_email_notification(alert)
                results["channels"]["email"] = email_result
            else:
                results["channels"]["email"] = {"success": False, "skipped": True, "reason": "Email disabled"}
            
            # In-app notification (always enabled)
            in_app_result = self._create_in_app_notification(alert)
            results["channels"]["in_app"] = in_app_result
            
            # Record in alert history
            self._record_notification_history(alert, results)
            
            results["success"] = any(
                channel.get("success", False)
                for channel in results["channels"].values()
            )
            
        except Exception as e:
            logger.error(f"Error sending notifications for alert {alert.id}: {str(e)}", exc_info=True)
            results["error"] = str(e)
        
        return results
    
    def notify_alert_escalated(self, alert: CommitteeAlert, escalation_level: int) -> Dict[str, Any]:
        """Send notification when alert is escalated"""
        results = {
            "alert_id": alert.id,
            "escalation_level": escalation_level,
            "channels": {}
        }
        
        try:
            # Email notification for escalation
            email_result = self._send_escalation_email(alert, escalation_level)
            results["channels"]["email"] = email_result
            
            # In-app notification
            in_app_result = self._create_in_app_notification(
                alert,
                message=f"Alert escalated to level {escalation_level}"
            )
            results["channels"]["in_app"] = in_app_result
            
            results["success"] = True
            
        except Exception as e:
            logger.error(f"Error sending escalation notification: {str(e)}", exc_info=True)
            results["error"] = str(e)
        
        return results
    
    def send_daily_digest(self, committee: Optional[CommitteeType] = None) -> Dict[str, Any]:
        """
        Send daily alert digest to committee members
        
        Summarizes all active alerts for the committee
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=1)
        
        query = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.status == "ACTIVE",
            CommitteeAlert.triggered_at >= cutoff_date
        )
        
        if committee:
            query = query.filter(CommitteeAlert.assigned_committee == committee)
        
        alerts = query.all()
        
        if not alerts:
            return {
                "success": True,
                "message": "No alerts to summarize",
                "alert_count": 0
            }
        
        # Generate digest HTML
        digest_html = self._generate_digest_html(alerts, committee)
        
        # Send email
        committee_emails = self._get_committee_emails(committee)
        
        result = self._send_email(
            to_emails=committee_emails,
            subject=f"Daily Alert Digest - {len(alerts)} Active Alerts",
            body_html=digest_html
        )
        
        return {
            "success": result.get("success", False),
            "alert_count": len(alerts),
            "recipients": len(committee_emails),
            **result
        }
    
    def _send_email_notification(self, alert: CommitteeAlert) -> Dict[str, Any]:
        """Send email notification for alert"""
        try:
            property_obj = self.db.query(Property).filter(
                Property.id == alert.property_id
            ).first()
            
            if not property_obj:
                return {"success": False, "error": "Property not found"}
            
            # Get committee emails
            committee_emails = self._get_committee_emails(alert.assigned_committee)
            
            if not committee_emails:
                logger.warning(f"No emails configured for committee: {alert.assigned_committee}")
                return {"success": False, "error": "No committee emails configured"}
            
            # Generate email HTML
            email_html = self._generate_alert_email_html(alert, property_obj)
            
            # Send email
            subject = f"[{alert.severity.value}] {alert.title} - {property_obj.property_name}"
            
            result = self._send_email(
                to_emails=committee_emails,
                subject=subject,
                body_html=email_html
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _send_escalation_email(self, alert: CommitteeAlert, escalation_level: int) -> Dict[str, Any]:
        """Send escalation email"""
        property_obj = self.db.query(Property).filter(
            Property.id == alert.property_id
        ).first()
        
        if not property_obj:
            return {"success": False, "error": "Property not found"}
        
        committee_emails = self._get_committee_emails(alert.assigned_committee)
        
        escalation_html = f"""
        <html>
        <body>
            <h2 style="color: #dc3545;">Alert Escalated</h2>
            <p>The following alert has been escalated to level {escalation_level}:</p>
            <h3>{alert.title}</h3>
            <p><strong>Property:</strong> {property_obj.property_name}</p>
            <p><strong>Severity:</strong> {alert.severity.value}</p>
            <p><strong>Status:</strong> {alert.status.value}</p>
            <p><a href="http://localhost:3000/#/risk-management?alert={alert.id}">View Alert</a></p>
        </body>
        </html>
        """
        
        return self._send_email(
            to_emails=committee_emails,
            subject=f"Alert Escalated: {alert.title}",
            body_html=escalation_html
        )
    
    def _create_in_app_notification(self, alert: CommitteeAlert, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create in-app notification
        
        In a full implementation, this would create a record in a notifications table
        For now, we'll just log it
        """
        try:
            notification_data = {
                "type": "alert",
                "alert_id": alert.id,
                "title": alert.title,
                "message": message or f"New {alert.severity.value} alert: {alert.title}",
                "severity": alert.severity.value,
                "timestamp": datetime.utcnow().isoformat(),
                "link": f"#/risk-management?alert={alert.id}"
            }
            
            # TODO: Store in notifications table
            logger.info(f"In-app notification created: {json.dumps(notification_data)}")
            
            return {
                "success": True,
                "notification": notification_data
            }
            
        except Exception as e:
            logger.error(f"Error creating in-app notification: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _generate_alert_email_html(self, alert: CommitteeAlert, property_obj: Property) -> str:
        """Generate HTML email template for alert"""
        severity_color = {
            AlertSeverity.URGENT: "#d32f2f",
            AlertSeverity.CRITICAL: "#d32f2f",
            AlertSeverity.WARNING: "#f57c00",
            AlertSeverity.INFO: "#1976d2"
        }.get(alert.severity, "#666")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {severity_color}; border-bottom: 2px solid {severity_color}; padding-bottom: 10px;">
                    {alert.severity.value} Alert: {alert.title}
                </h2>
                
                <h3>Property Information</h3>
                <ul>
                    <li><strong>Property:</strong> {property_obj.property_name} ({property_obj.property_code})</li>
                    <li><strong>Address:</strong> {property_obj.address or 'N/A'}</li>
                </ul>
                
                <h3>Alert Details</h3>
                <ul>
                    <li><strong>Alert Type:</strong> {alert.alert_type.value}</li>
                    <li><strong>Severity:</strong> {alert.severity.value}</li>
                    <li><strong>Status:</strong> {alert.status.value}</li>
                    <li><strong>Assigned Committee:</strong> {alert.assigned_committee.value.replace('_', ' ')}</li>
                </ul>
                
                {f'<p><strong>Threshold:</strong> {alert.threshold_value} {alert.threshold_unit or ""}</p>' if alert.threshold_value else ''}
                {f'<p><strong>Actual Value:</strong> {alert.actual_value} {alert.threshold_unit or ""}</p>' if alert.actual_value else ''}
                
                <h3>Description</h3>
                <p>{alert.description or 'No description provided'}</p>
                
                <div style="margin-top: 30px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
                    <a href="http://localhost:3000/#/risk-management?alert={alert.id}" 
                       style="background: {severity_color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Alert in REIMS
                    </a>
                </div>
                
                <p style="margin-top: 30px; font-size: 12px; color: #666;">
                    This is an automated notification from REIMS 2.0 Risk Management System.
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_digest_html(self, alerts: List[CommitteeAlert], committee: Optional[CommitteeType]) -> str:
        """Generate daily digest HTML"""
        committee_name = committee.value.replace('_', ' ') if committee else "All Committees"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h2>Daily Alert Digest - {committee_name}</h2>
                <p>Summary of {len(alerts)} active alerts as of {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead>
                        <tr style="background: #f5f5f5;">
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Alert</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Severity</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Property</th>
                            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Triggered</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for alert in alerts[:20]:  # Limit to 20 for email
            property_obj = self.db.query(Property).filter(
                Property.id == alert.property_id
            ).first()
            
            severity_color = {
                AlertSeverity.URGENT: "#d32f2f",
                AlertSeverity.CRITICAL: "#d32f2f",
                AlertSeverity.WARNING: "#f57c00",
                AlertSeverity.INFO: "#1976d2"
            }.get(alert.severity, "#666")
            
            html += f"""
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd;">
                                <a href="http://localhost:3000/#/risk-management?alert={alert.id}">{alert.title}</a>
                            </td>
                            <td style="padding: 10px; border: 1px solid #ddd; color: {severity_color};">
                                {alert.severity.value}
                            </td>
                            <td style="padding: 10px; border: 1px solid #ddd;">
                                {property_obj.property_name if property_obj else f'Property {alert.property_id}'}
                            </td>
                            <td style="padding: 10px; border: 1px solid #ddd;">
                                {alert.triggered_at.strftime('%Y-%m-%d %H:%M') if alert.triggered_at else 'N/A'}
                            </td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
                    <a href="http://localhost:3000/#/risk-management" 
                       style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View All Alerts in REIMS
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_committee_emails(self, committee: CommitteeType) -> List[str]:
        """Get email addresses for committee members"""
        # In production, this should query from database
        COMMITTEE_EMAILS = {
            CommitteeType.FINANCE_SUBCOMMITTEE: ["finance-committee@reims.com"],
            CommitteeType.OCCUPANCY_SUBCOMMITTEE: ["occupancy-committee@reims.com"],
            CommitteeType.RISK_COMMITTEE: ["risk-committee@reims.com"],
            CommitteeType.EXECUTIVE_COMMITTEE: ["executive-committee@reims.com"],
        }
        
        return COMMITTEE_EMAILS.get(committee, [])
    
    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str
    ) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            if not to_emails:
                return {"success": False, "error": "No recipients"}
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = "noreply@reims.com"
            msg['To'] = ", ".join(to_emails)
            
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)
            
            # In debug mode, just log the email
            if self.email_debug:
                logger.info(f"[EMAIL DEBUG] Would send email to {to_emails}")
                logger.info(f"[EMAIL DEBUG] Subject: {subject}")
                logger.info(f"[EMAIL DEBUG] Body length: {len(body_html)} chars")
                return {
                    "success": True,
                    "recipients": to_emails,
                    "sent_at": datetime.utcnow().isoformat(),
                    "debug": True
                }
            
            # Try to send via SMTP
            try:
                with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'], timeout=5) as server:
                    if self.smtp_config.get('use_tls'):
                        server.starttls()
                    if self.smtp_config.get('username'):
                        server.login(
                            self.smtp_config['username'],
                            self.smtp_config['password']
                        )
                    server.send_message(msg)
                
                logger.info(f"Email sent to {to_emails}")
                return {
                    "success": True,
                    "recipients": to_emails,
                    "sent_at": datetime.utcnow().isoformat()
                }
            except (smtplib.SMTPException, OSError, ConnectionRefusedError) as e:
                # In development, log instead of failing
                logger.warning(f"SMTP not available, email logged: {subject} - {str(e)}")
                return {
                    "success": False,
                    "error": "SMTP not configured",
                    "logged": True,
                    "error_details": str(e)
                }
        
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _record_notification_history(self, alert: CommitteeAlert, results: Dict[str, Any]) -> None:
        """Record notification delivery in alert history"""
        try:
            history = AlertHistory(
                alert_id=alert.id,
                action_type="notified",
                action_at=datetime.utcnow(),
                action_metadata={
                    "notification_results": results,
                    "channels": list(results.get("channels", {}).keys())
                }
            )
            self.db.add(history)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error recording notification history: {str(e)}", exc_info=True)
            self.db.rollback()

