"""
Anomaly Export Service

Exports anomalies to CSV, XLSX, and JSON formats with comprehensive data including
XAI explanations, cross-property context, and feedback history.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from io import BytesIO
import csv
import json
import logging

logger = logging.getLogger(__name__)

# Try to import pandas and openpyxl for Excel export
try:
    import pandas as pd
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("pandas/openpyxl not available - Excel export disabled")

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_explanation import AnomalyExplanation
from app.models.anomaly_feedback import AnomalyFeedback
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


class AnomalyExportService:
    """
    Service for exporting anomalies in various formats.
    
    Features:
    - CSV, XLSX, JSON export formats
    - Comprehensive data including XAI explanations
    - Filtering by property, date range, severity, type, account
    - Efficient handling of large exports
    """
    
    def __init__(self, db: Session):
        """Initialize anomaly export service."""
        self.db = db
    
    def export_anomalies(
        self,
        format: str = 'csv',  # 'csv', 'xlsx', 'json'
        property_ids: Optional[List[int]] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        severity: Optional[str] = None,  # 'critical', 'high', 'medium', 'low'
        anomaly_type: Optional[str] = None,
        account_codes: Optional[List[str]] = None,
        include_explanations: bool = True,
        include_feedback: bool = True,
        include_cross_property: bool = True
    ) -> bytes:
        """
        Export anomalies to specified format.
        
        Args:
            format: Export format ('csv', 'xlsx', 'json')
            property_ids: Filter by property IDs
            date_start: Start date filter (inclusive)
            date_end: End date filter (inclusive)
            severity: Filter by severity level
            anomaly_type: Filter by anomaly type
            account_codes: Filter by account codes
            include_explanations: Include XAI explanations
            include_feedback: Include feedback history
            include_cross_property: Include cross-property context
        
        Returns:
            File bytes ready for download
        """
        # Build query
        query = self.db.query(AnomalyDetection)
        
        # Apply filters
        if property_ids:
            query = query.filter(AnomalyDetection.property_id.in_(property_ids))
        
        if date_start:
            query = query.filter(AnomalyDetection.detected_at >= datetime.combine(date_start, datetime.min.time()))
        
        if date_end:
            query = query.filter(AnomalyDetection.detected_at <= datetime.combine(date_end, datetime.max.time()))
        
        if severity:
            query = query.filter(AnomalyDetection.severity == severity)
        
        if anomaly_type:
            query = query.filter(AnomalyDetection.anomaly_type == anomaly_type)
        
        if account_codes:
            query = query.filter(AnomalyDetection.account_code.in_(account_codes))
        
        # Get anomalies
        anomalies = query.order_by(AnomalyDetection.detected_at.desc()).all()
        
        logger.info(f"Exporting {len(anomalies)} anomalies to {format.upper()}")
        
        # Export based on format
        if format.lower() == 'csv':
            return self._export_to_csv(anomalies, include_explanations, include_feedback, include_cross_property)
        elif format.lower() == 'xlsx':
            if not EXCEL_AVAILABLE:
                raise ValueError("Excel export requires pandas and openpyxl. Install with: pip install pandas openpyxl")
            return self._export_to_excel(anomalies, include_explanations, include_feedback, include_cross_property)
        elif format.lower() == 'json':
            return self._export_to_json(anomalies, include_explanations, include_feedback, include_cross_property)
        else:
            raise ValueError(f"Unsupported format: {format}. Supported: csv, xlsx, json")
    
    def _export_to_csv(
        self,
        anomalies: List[AnomalyDetection],
        include_explanations: bool,
        include_feedback: bool,
        include_cross_property: bool
    ) -> bytes:
        """Export anomalies to CSV format."""
        output = BytesIO()
        output.write(b'\xef\xbb\xbf')  # UTF-8 BOM for Excel compatibility
        
        writer = csv.writer(output)
        
        # Headers
        headers = [
            'ID', 'Property ID', 'Property Code', 'Account Code', 'Field Name',
            'Anomaly Type', 'Severity', 'Actual Value', 'Expected Value',
            'Confidence', 'Z-Score', 'Percentage Change', 'Detected At',
            'Detection Method', 'Context Suppressed', 'Suppression Reason'
        ]
        
        if include_explanations:
            headers.extend([
                'Root Cause Type', 'Root Cause Description', 'Natural Language Explanation',
                'Recommended Actions'
            ])
        
        if include_feedback:
            headers.extend([
                'Feedback Count', 'True Positive Count', 'False Positive Count',
                'True Positive Rate', 'False Positive Rate'
            ])
        
        if include_cross_property:
            headers.extend([
                'Portfolio Rank', 'Portfolio Percentile', 'Portfolio Mean', 'Portfolio Median'
            ])
        
        writer.writerow(headers)
        
        # Data rows
        for anomaly in anomalies:
            row = [
                anomaly.id,
                anomaly.property_id,
                self._get_property_code(anomaly.property_id),
                anomaly.account_code,
                anomaly.field_name,
                anomaly.anomaly_type,
                anomaly.severity,
                float(anomaly.actual_value) if anomaly.actual_value else None,
                float(anomaly.expected_value) if anomaly.expected_value else None,
                float(anomaly.confidence) if anomaly.confidence else None,
                float(anomaly.z_score) if anomaly.z_score else None,
                float(anomaly.percentage_change) if anomaly.percentage_change else None,
                anomaly.detected_at.isoformat() if anomaly.detected_at else None,
                anomaly.detection_method,
                anomaly.context_suppressed or False,
                anomaly.suppression_reason
            ]
            
            # Add explanation data
            if include_explanations:
                explanation = self._get_explanation(anomaly.id)
                if explanation:
                    row.extend([
                        explanation.root_cause_type,
                        explanation.root_cause_description,
                        explanation.natural_language_explanation,
                        json.dumps(explanation.recommended_actions) if explanation.recommended_actions else None
                    ])
                else:
                    row.extend([None, None, None, None])
            
            # Add feedback data
            if include_feedback:
                feedback_stats = self._get_feedback_stats(anomaly.id)
                row.extend([
                    feedback_stats.get('total_count', 0),
                    feedback_stats.get('true_positives', 0),
                    feedback_stats.get('false_positives', 0),
                    feedback_stats.get('true_positive_rate'),
                    feedback_stats.get('false_positive_rate')
                ])
            
            # Add cross-property data
            if include_cross_property:
                cross_prop = self._get_cross_property_context(anomaly.property_id, anomaly.account_code)
                row.extend([
                    cross_prop.get('rank'),
                    cross_prop.get('percentile'),
                    cross_prop.get('portfolio_mean'),
                    cross_prop.get('portfolio_median')
                ])
            
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()
    
    def _export_to_excel(
        self,
        anomalies: List[AnomalyDetection],
        include_explanations: bool,
        include_feedback: bool,
        include_cross_property: bool
    ) -> bytes:
        """Export anomalies to Excel format with multiple sheets."""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Anomalies
            anomalies_data = []
            for anomaly in anomalies:
                row = {
                    'ID': anomaly.id,
                    'Property ID': anomaly.property_id,
                    'Property Code': self._get_property_code(anomaly.property_id),
                    'Account Code': anomaly.account_code,
                    'Field Name': anomaly.field_name,
                    'Anomaly Type': anomaly.anomaly_type,
                    'Severity': anomaly.severity,
                    'Actual Value': float(anomaly.actual_value) if anomaly.actual_value else None,
                    'Expected Value': float(anomaly.expected_value) if anomaly.expected_value else None,
                    'Confidence': float(anomaly.confidence) if anomaly.confidence else None,
                    'Z-Score': float(anomaly.z_score) if anomaly.z_score else None,
                    'Percentage Change': float(anomaly.percentage_change) if anomaly.percentage_change else None,
                    'Detected At': anomaly.detected_at.isoformat() if anomaly.detected_at else None,
                    'Detection Method': anomaly.detection_method,
                    'Context Suppressed': anomaly.context_suppressed or False,
                    'Suppression Reason': anomaly.suppression_reason
                }
                anomalies_data.append(row)
            
            df_anomalies = pd.DataFrame(anomalies_data)
            df_anomalies.to_excel(writer, sheet_name='Anomalies', index=False)
            
            # Sheet 2: Explanations (if enabled)
            if include_explanations:
                explanations_data = []
                for anomaly in anomalies:
                    explanation = self._get_explanation(anomaly.id)
                    if explanation:
                        explanations_data.append({
                            'Anomaly ID': anomaly.id,
                            'Root Cause Type': explanation.root_cause_type,
                            'Root Cause Description': explanation.root_cause_description,
                            'Natural Language Explanation': explanation.natural_language_explanation,
                            'Recommended Actions': json.dumps(explanation.recommended_actions) if explanation.recommended_actions else None,
                            'SHAP Values': json.dumps(explanation.shap_values) if explanation.shap_values else None,
                            'LIME Explanation': explanation.lime_explanation,
                            'Generated At': explanation.generated_at.isoformat() if explanation.generated_at else None
                        })
                
                if explanations_data:
                    df_explanations = pd.DataFrame(explanations_data)
                    df_explanations.to_excel(writer, sheet_name='Explanations', index=False)
            
            # Sheet 3: Statistics
            stats_data = [{
                'Total Anomalies': len(anomalies),
                'By Severity - Critical': len([a for a in anomalies if a.severity == 'critical']),
                'By Severity - High': len([a for a in anomalies if a.severity == 'high']),
                'By Severity - Medium': len([a for a in anomalies if a.severity == 'medium']),
                'By Severity - Low': len([a for a in anomalies if a.severity == 'low']),
                'With Explanations': len([a for a in anomalies if self._get_explanation(a.id) is not None]),
                'With Feedback': len([a for a in anomalies if self._get_feedback_stats(a.id).get('total_count', 0) > 0]),
                'Context Suppressed': len([a for a in anomalies if a.context_suppressed]),
                'Export Date': datetime.now().isoformat()
            }]
            df_stats = pd.DataFrame(stats_data)
            df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            # Sheet 4: Feedback (if enabled)
            if include_feedback:
                feedback_data = []
                for anomaly in anomalies:
                    feedback_stats = self._get_feedback_stats(anomaly.id)
                    if feedback_stats.get('total_count', 0) > 0:
                        feedback_data.append({
                            'Anomaly ID': anomaly.id,
                            'Total Feedback': feedback_stats.get('total_count', 0),
                            'True Positives': feedback_stats.get('true_positives', 0),
                            'False Positives': feedback_stats.get('false_positives', 0),
                            'True Positive Rate %': feedback_stats.get('true_positive_rate'),
                            'False Positive Rate %': feedback_stats.get('false_positive_rate')
                        })
                
                if feedback_data:
                    df_feedback = pd.DataFrame(feedback_data)
                    df_feedback.to_excel(writer, sheet_name='Feedback', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    def _export_to_json(
        self,
        anomalies: List[AnomalyDetection],
        include_explanations: bool,
        include_feedback: bool,
        include_cross_property: bool
    ) -> bytes:
        """Export anomalies to JSON format."""
        result = {
            'export_metadata': {
                'export_date': datetime.now().isoformat(),
                'total_anomalies': len(anomalies),
                'format_version': '1.0'
            },
            'anomalies': []
        }
        
        for anomaly in anomalies:
            anomaly_data = {
                'id': anomaly.id,
                'property_id': anomaly.property_id,
                'property_code': self._get_property_code(anomaly.property_id),
                'account_code': anomaly.account_code,
                'field_name': anomaly.field_name,
                'anomaly_type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'actual_value': float(anomaly.actual_value) if anomaly.actual_value else None,
                'expected_value': float(anomaly.expected_value) if anomaly.expected_value else None,
                'confidence': float(anomaly.confidence) if anomaly.confidence else None,
                'z_score': float(anomaly.z_score) if anomaly.z_score else None,
                'percentage_change': float(anomaly.percentage_change) if anomaly.percentage_change else None,
                'detected_at': anomaly.detected_at.isoformat() if anomaly.detected_at else None,
                'detection_method': anomaly.detection_method,
                'context_suppressed': anomaly.context_suppressed or False,
                'suppression_reason': anomaly.suppression_reason
            }
            
            # Add explanation
            if include_explanations:
                explanation = self._get_explanation(anomaly.id)
                if explanation:
                    anomaly_data['explanation'] = {
                        'root_cause_type': explanation.root_cause_type,
                        'root_cause_description': explanation.root_cause_description,
                        'natural_language_explanation': explanation.natural_language_explanation,
                        'recommended_actions': explanation.recommended_actions,
                        'shap_values': explanation.shap_values,
                        'lime_explanation': explanation.lime_explanation
                    }
            
            # Add feedback
            if include_feedback:
                feedback_stats = self._get_feedback_stats(anomaly.id)
                anomaly_data['feedback'] = feedback_stats
            
            # Add cross-property context
            if include_cross_property:
                cross_prop = self._get_cross_property_context(anomaly.property_id, anomaly.account_code)
                anomaly_data['cross_property_context'] = cross_prop
            
            result['anomalies'].append(anomaly_data)
        
        return json.dumps(result, indent=2, default=str).encode('utf-8')
    
    def _get_property_code(self, property_id: int) -> Optional[str]:
        """Get property code for a property ID."""
        try:
            property_obj = self.db.query(Property).filter(Property.id == property_id).first()
            return property_obj.property_code if property_obj else None
        except:
            return None
    
    def _get_explanation(self, anomaly_id: int) -> Optional[AnomalyExplanation]:
        """Get XAI explanation for an anomaly."""
        try:
            return self.db.query(AnomalyExplanation).filter(
                AnomalyExplanation.anomaly_detection_id == anomaly_id
            ).first()
        except:
            return None
    
    def _get_feedback_stats(self, anomaly_id: int) -> Dict[str, Any]:
        """Get feedback statistics for an anomaly."""
        try:
            feedbacks = self.db.query(AnomalyFeedback).filter(
                AnomalyFeedback.anomaly_detection_id == anomaly_id
            ).all()
            
            total = len(feedbacks)
            true_positives = len([f for f in feedbacks if f.feedback_type == 'true_positive'])
            false_positives = len([f for f in feedbacks if f.feedback_type == 'false_positive'])
            
            return {
                'total_count': total,
                'true_positives': true_positives,
                'false_positives': false_positives,
                'true_positive_rate': (true_positives / total * 100) if total > 0 else None,
                'false_positive_rate': (false_positives / total * 100) if total > 0 else None
            }
        except:
            return {'total_count': 0, 'true_positives': 0, 'false_positives': 0}
    
    def _get_cross_property_context(self, property_id: int, account_code: str) -> Dict[str, Any]:
        """Get cross-property context for an anomaly."""
        try:
            from app.services.cross_property_intelligence import CrossPropertyIntelligenceService
            service = CrossPropertyIntelligenceService(self.db)
            ranking = service.get_property_ranking(property_id, account_code)
            return ranking or {}
        except:
            return {}

