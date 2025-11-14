"""
Committee Notification Service

Handles email notifications to committee members for:
- Risk alerts
- Workflow lock approvals
- Covenant violations
- Critical financial events
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from app.models.committee_alert import CommitteeAlert, CommitteeType, AlertSeverity
from app.models.workflow_lock import WorkflowLock
from app.models.property import Property
from app.models.user import User

logger = logging.getLogger(__name__)


class CommitteeNotificationService:
    """
    Committee Notification Service

    Sends notifications to committee members for alerts and approvals
    """

    # Committee member emails (in production, this should come from database)
    COMMITTEE_EMAILS = {
        CommitteeType.FINANCE_SUBCOMMITTEE: [
            "finance-committee@reims.com",
            # Add actual emails in production
        ],
        CommitteeType.OCCUPANCY_SUBCOMMITTEE: [
            "occupancy-committee@reims.com",
        ],
        CommitteeType.RISK_COMMITTEE: [
            "risk-committee@reims.com",
        ],
        CommitteeType.EXECUTIVE_COMMITTEE: [
            "executive-committee@reims.com",
        ],
    }

    def __init__(self, db: Session, smtp_config: Optional[Dict] = None):
        self.db = db
        self.smtp_config = smtp_config or {
            "host": "localhost",
            "port": 1025,  # MailHog default for dev
            "use_tls": False,
            "username": None,
            "password": None,
        }

    def notify_alert_created(self, alert: CommitteeAlert) -> Dict:
        """
        Send notification when a new alert is created
        """
        try:
            # Get property details
            property = self.db.query(Property).filter(
                Property.id == alert.property_id
            ).first()

            if not property:
                return {"success": False, "error": "Property not found"}

            # Get committee emails
            committee_emails = self.COMMITTEE_EMAILS.get(alert.assigned_committee, [])
            if not committee_emails:
                logger.warning(f"No emails configured for committee: {alert.assigned_committee}")
                return {"success": False, "error": "No committee emails configured"}

            # Compose email
            subject = f"[{alert.severity.value}] {alert.title} - {property.property_name}"

            body = f"""
<html>
<body>
    <h2 style="color: {'#d32f2f' if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT] else '#f57c00'};">
        {alert.severity.value} Alert: {alert.title}
    </h2>

    <h3>Property Information</h3>
    <ul>
        <li><strong>Property:</strong> {property.property_name} ({property.property_code})</li>
        <li><strong>Address:</strong> {property.address or 'N/A'}</li>
        <li><strong>Type:</strong> {property.property_type or 'N/A'}</li>
    </ul>

    <h3>Alert Details</h3>
    <ul>
        <li><strong>Alert Type:</strong> {alert.alert_type.value}</li>
        <li><strong>Severity:</strong> {alert.severity.value}</li>
        <li><strong>Status:</strong> {alert.status.value}</li>
        <li><strong>Triggered:</strong> {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
    </ul>

    <p><strong>Description:</strong></p>
    <p style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #f57c00;">
        {alert.description.replace(chr(10), '<br>')}
    </p>

    {'<h3>Threshold Information</h3>' if alert.threshold_value else ''}
    {f'''<ul>
        <li><strong>Threshold:</strong> {float(alert.threshold_value):.2f} {alert.threshold_unit or ''}</li>
        <li><strong>Actual Value:</strong> {float(alert.actual_value):.2f} {alert.threshold_unit or ''}</li>
        <li><strong>Deviation:</strong> {((float(alert.actual_value) / float(alert.threshold_value) - 1) * 100):.1f}%</li>
    </ul>''' if alert.threshold_value else ''}

    {'<p style="color: #d32f2f; font-weight: bold;">⚠️ This alert requires committee approval.</p>' if alert.requires_approval else ''}

    <hr>
    <p style="font-size: 12px; color: #666;">
        This is an automated notification from REIMS2 (Real Estate Investment Monitoring System).<br>
        Alert ID: {alert.id} | BR-ID: {alert.br_id or 'N/A'}<br>
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </p>
</body>
</html>
            """

            # Send email
            result = self._send_email(
                to_emails=committee_emails,
                subject=subject,
                body_html=body,
                alert_id=alert.id
            )

            if result["success"]:
                logger.info(f"Alert notification sent for alert {alert.id}")

            return result

        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")
            return {"success": False, "error": str(e)}

    def notify_workflow_lock_created(self, lock: WorkflowLock) -> Dict:
        """
        Send notification when a workflow lock requires approval
        """
        try:
            # Get property details
            property = self.db.query(Property).filter(
                Property.id == lock.property_id
            ).first()

            if not property:
                return {"success": False, "error": "Property not found"}

            # Determine which committee to notify
            if lock.approval_committee == "Finance Sub-Committee":
                committee = CommitteeType.FINANCE_SUBCOMMITTEE
            elif lock.approval_committee == "Occupancy Sub-Committee":
                committee = CommitteeType.OCCUPANCY_SUBCOMMITTEE
            elif lock.approval_committee == "Executive Committee":
                committee = CommitteeType.EXECUTIVE_COMMITTEE
            else:
                committee = CommitteeType.RISK_COMMITTEE

            committee_emails = self.COMMITTEE_EMAILS.get(committee, [])
            if not committee_emails:
                logger.warning(f"No emails configured for committee: {committee}")
                return {"success": False, "error": "No committee emails configured"}

            # Compose email
            subject = f"[ACTION REQUIRED] Workflow Lock Approval - {property.property_name}"

            body = f"""
<html>
<body>
    <h2 style="color: #d32f2f;">🔒 Workflow Lock Requires Committee Approval</h2>

    <h3>Property Information</h3>
    <ul>
        <li><strong>Property:</strong> {property.property_name} ({property.property_code})</li>
        <li><strong>Address:</strong> {property.address or 'N/A'}</li>
    </ul>

    <h3>Lock Details</h3>
    <ul>
        <li><strong>Lock Reason:</strong> {lock.lock_reason.value}</li>
        <li><strong>Lock Scope:</strong> {lock.lock_scope.value}</li>
        <li><strong>Status:</strong> {lock.status.value}</li>
        <li><strong>Locked At:</strong> {lock.locked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
        <li><strong>Days Locked:</strong> {lock.days_locked()}</li>
    </ul>

    <p><strong>Title:</strong> {lock.title}</p>
    <p><strong>Description:</strong></p>
    <p style="background-color: #ffebee; padding: 15px; border-left: 4px solid #d32f2f;">
        {lock.description or 'No description provided'}
    </p>

    <h3 style="color: #d32f2f;">⚠️ Action Required</h3>
    <p>
        This workflow lock requires approval from the <strong>{lock.approval_committee}</strong>
        before operations can resume on this property.
    </p>

    <p>
        <strong>Blocked Operations:</strong>
        {self._format_blocked_operations(lock.lock_scope)}
    </p>

    <hr>
    <p style="font-size: 12px; color: #666;">
        This is an automated notification from REIMS2 (Real Estate Investment Monitoring System).<br>
        Lock ID: {lock.id} | BR-ID: {lock.br_id or 'N/A'}<br>
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </p>
</body>
</html>
            """

            # Send email
            result = self._send_email(
                to_emails=committee_emails,
                subject=subject,
                body_html=body,
                lock_id=lock.id
            )

            if result["success"]:
                logger.info(f"Workflow lock notification sent for lock {lock.id}")

            return result

        except Exception as e:
            logger.error(f"Failed to send workflow lock notification: {str(e)}")
            return {"success": False, "error": str(e)}

    def notify_alert_resolved(self, alert: CommitteeAlert, resolved_by: User) -> Dict:
        """
        Send notification when an alert is resolved
        """
        try:
            property = self.db.query(Property).filter(
                Property.id == alert.property_id
            ).first()

            committee_emails = self.COMMITTEE_EMAILS.get(alert.assigned_committee, [])

            subject = f"[RESOLVED] {alert.title} - {property.property_name}"

            body = f"""
<html>
<body>
    <h2 style="color: #388e3c;">✓ Alert Resolved: {alert.title}</h2>

    <h3>Property Information</h3>
    <ul>
        <li><strong>Property:</strong> {property.property_name} ({property.property_code})</li>
    </ul>

    <h3>Resolution Details</h3>
    <ul>
        <li><strong>Resolved By:</strong> {resolved_by.email if resolved_by else 'System'}</li>
        <li><strong>Resolved At:</strong> {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
        <li><strong>Days Open:</strong> {alert.days_open()}</li>
    </ul>

    <p><strong>Resolution Notes:</strong></p>
    <p style="background-color: #f5f5f5; padding: 15px;">
        {alert.resolution_notes or 'No notes provided'}
    </p>

    <hr>
    <p style="font-size: 12px; color: #666;">
        Alert ID: {alert.id}<br>
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </p>
</body>
</html>
            """

            return self._send_email(
                to_emails=committee_emails,
                subject=subject,
                body_html=body,
                alert_id=alert.id
            )

        except Exception as e:
            logger.error(f"Failed to send resolution notification: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_daily_digest(self, committee: CommitteeType) -> Dict:
        """
        Send daily digest of active alerts to committee
        """
        try:
            # Get active alerts for committee
            alerts = self.db.query(CommitteeAlert).filter(
                CommitteeAlert.assigned_committee == committee,
                CommitteeAlert.status.in_(['ACTIVE', 'ACKNOWLEDGED'])
            ).order_by(CommitteeAlert.severity.desc(), CommitteeAlert.triggered_at).all()

            if not alerts:
                return {"success": True, "message": "No active alerts to report"}

            committee_emails = self.COMMITTEE_EMAILS.get(committee, [])

            # Count by severity
            critical = len([a for a in alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]])
            warning = len([a for a in alerts if a.severity == AlertSeverity.WARNING])
            info = len([a for a in alerts if a.severity == AlertSeverity.INFO])

            subject = f"[REIMS2] Daily Alert Digest - {committee.value} ({len(alerts)} alerts)"

            alerts_html = ""
            for alert in alerts:
                property = self.db.query(Property).filter(Property.id == alert.property_id).first()
                alerts_html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 10px;">{alert.severity.value}</td>
                    <td style="padding: 10px;">{property.property_name if property else 'N/A'}</td>
                    <td style="padding: 10px;">{alert.alert_type.value}</td>
                    <td style="padding: 10px;">{alert.title}</td>
                    <td style="padding: 10px;">{alert.days_open()} days</td>
                </tr>
                """

            body = f"""
<html>
<body>
    <h2>Daily Alert Digest - {committee.value}</h2>
    <p>{datetime.utcnow().strftime('%A, %B %d, %Y')}</p>

    <h3>Summary</h3>
    <ul>
        <li>🔴 <strong>Critical:</strong> {critical}</li>
        <li>🟡 <strong>Warning:</strong> {warning}</li>
        <li>🔵 <strong>Info:</strong> {info}</li>
        <li><strong>Total:</strong> {len(alerts)}</li>
    </ul>

    <h3>Active Alerts</h3>
    <table style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr style="background-color: #f5f5f5;">
                <th style="padding: 10px; text-align: left;">Severity</th>
                <th style="padding: 10px; text-align: left;">Property</th>
                <th style="padding: 10px; text-align: left;">Type</th>
                <th style="padding: 10px; text-align: left;">Alert</th>
                <th style="padding: 10px; text-align: left;">Age</th>
            </tr>
        </thead>
        <tbody>
            {alerts_html}
        </tbody>
    </table>

    <hr>
    <p style="font-size: 12px; color: #666;">
        This is an automated daily digest from REIMS2.<br>
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
    </p>
</body>
</html>
            """

            return self._send_email(
                to_emails=committee_emails,
                subject=subject,
                body_html=body
            )

        except Exception as e:
            logger.error(f"Failed to send daily digest: {str(e)}")
            return {"success": False, "error": str(e)}

    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        alert_id: Optional[int] = None,
        lock_id: Optional[int] = None
    ) -> Dict:
        """
        Send email using SMTP
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = "noreply@reims.com"
            msg['To'] = ", ".join(to_emails)

            # Attach HTML body
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
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
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {"success": False, "error": str(e)}

    def _format_blocked_operations(self, lock_scope) -> str:
        """
        Format blocked operations based on lock scope
        """
        from app.models.workflow_lock import LockScope

        scope_descriptions = {
            LockScope.PROPERTY_ALL: "All property operations",
            LockScope.FINANCIAL_UPDATES: "Financial data updates",
            LockScope.REPORTING_ONLY: "Report generation",
            LockScope.TRANSACTION_APPROVAL: "Transaction approvals",
            LockScope.DATA_ENTRY: "Data entry",
        }

        return scope_descriptions.get(lock_scope, "Unknown")
