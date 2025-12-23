"""
Alert Deduplication Service

Deduplicates alerts based on property, period, metric/account, and anomaly_family.
Updates existing alerts instead of creating new ones.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import hashlib
import json

from app.models.committee_alert import CommitteeAlert, AlertType, AlertStatus

logger = logging.getLogger(__name__)


class AlertDeduplicationService:
    """
    Deduplicates alerts to prevent alert storms.
    
    Groups alerts by:
    - property_id
    - period_id
    - metric/account (related_metric or field_name)
    - anomaly_family (from metadata)
    """
    
    def __init__(self, db: Session):
        """Initialize deduplication service."""
        self.db = db
    
    def deduplicate_alert(
        self,
        alert_data: Dict[str, Any]
    ) -> Optional[CommitteeAlert]:
        """
        Check for duplicate alert and update existing or create new.
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            CommitteeAlert (existing updated or newly created)
        """
        # Generate deduplication key
        dedup_key = self._generate_dedup_key(alert_data)
        
        # Find existing alert
        existing = self._find_existing_alert(dedup_key, alert_data)
        
        if existing:
            # Update existing alert
            return self._update_existing_alert(existing, alert_data)
        else:
            # Create new alert
            return self._create_new_alert(alert_data, dedup_key)
    
    def _generate_dedup_key(self, alert_data: Dict[str, Any]) -> str:
        """Generate deduplication key from alert data."""
        key_parts = [
            str(alert_data.get('property_id', '')),
            str(alert_data.get('period_id', '')),
            str(alert_data.get('related_metric', '') or alert_data.get('field_name', '')),
            str(alert_data.get('anomaly_family', '') or alert_data.get('anomaly_type', ''))
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _find_existing_alert(
        self,
        dedup_key: str,
        alert_data: Dict[str, Any]
    ) -> Optional[CommitteeAlert]:
        """Find existing alert matching deduplication criteria."""
        # Query by deduplication criteria
        query = self.db.query(CommitteeAlert).filter(
            and_(
                CommitteeAlert.property_id == alert_data.get('property_id'),
                CommitteeAlert.related_metric == (alert_data.get('related_metric') or alert_data.get('field_name')),
                CommitteeAlert.alert_type == AlertType.ANOMALY_DETECTED,
                CommitteeAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
            )
        )
        
        # If period_id available, filter by it
        if alert_data.get('period_id'):
            # Check metadata for period_id
            query = query.filter(
                func.jsonb_extract_path_text(CommitteeAlert.metadata, 'period_id') == str(alert_data['period_id'])
            )
        
        return query.order_by(CommitteeAlert.created_at.desc()).first()
    
    def _update_existing_alert(
        self,
        existing: CommitteeAlert,
        alert_data: Dict[str, Any]
    ) -> CommitteeAlert:
        """Update existing alert with new information."""
        # Update metadata with new occurrence
        if not existing.metadata:
            existing.metadata = {}
        
        if 'occurrences' not in existing.metadata:
            existing.metadata['occurrences'] = []
        
        existing.metadata['occurrences'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'severity': alert_data.get('severity'),
            'anomaly_id': alert_data.get('anomaly_id')
        })
        
        existing.metadata['last_updated'] = datetime.utcnow().isoformat()
        existing.metadata['occurrence_count'] = len(existing.metadata['occurrences'])
        
        # Update severity if new one is higher
        from app.models.committee_alert import AlertSeverity
        severity_map = {
            'info': AlertSeverity.INFO,
            'low': AlertSeverity.WARNING,
            'medium': AlertSeverity.WARNING,
            'high': AlertSeverity.URGENT,
            'critical': AlertSeverity.CRITICAL
        }
        
        new_severity = severity_map.get(alert_data.get('severity', 'medium').lower(), AlertSeverity.WARNING)
        if new_severity.value > existing.severity.value:
            existing.severity = new_severity
        
        # Update timestamp
        existing.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(existing)
        
        logger.info(f"Updated existing alert {existing.id} (occurrence count: {existing.metadata.get('occurrence_count', 1)})")
        
        return existing
    
    def _create_new_alert(
        self,
        alert_data: Dict[str, Any],
        dedup_key: str
    ) -> CommitteeAlert:
        """Create new alert with deduplication key."""
        from app.models.committee_alert import AlertSeverity, CommitteeType
        
        severity_map = {
            'info': AlertSeverity.INFO,
            'low': AlertSeverity.WARNING,
            'medium': AlertSeverity.WARNING,
            'high': AlertSeverity.URGENT,
            'critical': AlertSeverity.CRITICAL
        }
        
        severity = severity_map.get(alert_data.get('severity', 'medium').lower(), AlertSeverity.WARNING)
        
        metadata = alert_data.get('metadata', {})
        metadata['dedup_key'] = dedup_key
        metadata['occurrences'] = [{
            'timestamp': datetime.utcnow().isoformat(),
            'severity': alert_data.get('severity'),
            'anomaly_id': alert_data.get('anomaly_id')
        }]
        metadata['occurrence_count'] = 1
        
        alert = CommitteeAlert(
            property_id=alert_data.get('property_id'),
            alert_type=AlertType.ANOMALY_DETECTED,
            severity=severity,
            status=AlertStatus.ACTIVE,
            title=alert_data.get('title', 'Anomaly Detected'),
            description=alert_data.get('description', ''),
            assigned_committee=CommitteeType.RISK_COMMITTEE,
            related_metric=alert_data.get('related_metric') or alert_data.get('field_name'),
            metadata=metadata
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Created new alert {alert.id} with dedup_key {dedup_key}")
        
        return alert
