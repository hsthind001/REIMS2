"""
XAI (Explainable AI) Service for Anomaly Detection

Provides explainable AI capabilities for anomaly detection:
- SHAP (SHapley Additive exPlanations) for feature importance
- LIME (Local Interpretable Model-agnostic Explanations) for local explanations
- Root cause analysis
- Natural language explanations
- Actionable recommendations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_explanation import AnomalyExplanation
from app.core.config import settings
from app.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)

# Optional XAI imports
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available - feature importance explanations disabled")

try:
    import lime
    import lime.lime_tabular
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME not available - local explanations disabled")


class XAIExplanationService:
    """
    Service for generating explainable AI explanations for anomalies.
    
    Provides:
    - SHAP values for global feature importance
    - LIME explanations for local interpretability
    - Root cause analysis
    - Natural language explanations
    - Actionable recommendations
    """
    
    def __init__(self, db: Session):
        """Initialize XAI explanation service."""
        self.db = db
        self.shap_enabled = FeatureFlags.is_shap_enabled() and SHAP_AVAILABLE
        self.lime_enabled = FeatureFlags.is_lime_enabled() and LIME_AVAILABLE
    
    def generate_explanation(
        self,
        anomaly_id: int,
        feature_data: Optional[pd.DataFrame] = None,
        model: Optional[Any] = None,
        method: str = 'auto'
    ) -> AnomalyExplanation:
        """
        Generate comprehensive explanation for an anomaly.
        
        Args:
            anomaly_id: ID of the anomaly detection
            feature_data: Optional feature data for the anomaly
            model: Optional trained model for SHAP/LIME
            method: Explanation method ('shap', 'lime', 'auto', 'root_cause')
        
        Returns:
            AnomalyExplanation object with all explanation data
        """
        # Get anomaly detection
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            raise ValueError(f"Anomaly detection {anomaly_id} not found")
        
        start_time = datetime.utcnow()
        
        # Generate root cause analysis
        root_cause = self._analyze_root_cause(anomaly)
        
        # Generate SHAP explanation if enabled
        shap_data = None
        if self.shap_enabled and method in ('shap', 'auto') and model is not None:
            try:
                shap_data = self._generate_shap_explanation(
                    anomaly, feature_data, model
                )
            except Exception as e:
                logger.warning(f"SHAP explanation failed: {e}")
        
        # Generate LIME explanation if enabled
        lime_data = None
        if self.lime_enabled and method in ('lime', 'auto') and model is not None:
            try:
                lime_data = self._generate_lime_explanation(
                    anomaly, feature_data, model
                )
            except Exception as e:
                logger.warning(f"LIME explanation failed: {e}")
        
        # Generate natural language explanation
        nl_explanation = self._generate_natural_language_explanation(
            anomaly, root_cause, shap_data, lime_data
        )
        
        # Generate actionable recommendations
        recommendations = self._generate_recommendations(anomaly, root_cause)
        
        computation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Create explanation record
        explanation = AnomalyExplanation(
            anomaly_detection_id=anomaly_id,
            root_cause_type=root_cause['type'],
            root_cause_description=root_cause['description'],
            contributing_factors=root_cause.get('factors'),
            shap_values=shap_data.get('values') if shap_data else None,
            shap_base_value=shap_data.get('base_value') if shap_data else None,
            shap_feature_importance=shap_data.get('feature_importance') if shap_data else None,
            lime_explanation=lime_data.get('explanation') if lime_data else None,
            lime_intercept=lime_data.get('intercept') if lime_data else None,
            lime_score=lime_data.get('score') if lime_data else None,
            suggested_actions=recommendations,
            action_category=recommendations[0]['category'] if recommendations else None,
            explanation_generated_at=datetime.utcnow(),
            explanation_method=method,
            computation_time_ms=computation_time
        )
        
        self.db.add(explanation)
        self.db.commit()
        self.db.refresh(explanation)
        
        return explanation
    
    def _analyze_root_cause(
        self,
        anomaly: AnomalyDetection
    ) -> Dict[str, Any]:
        """
        Analyze root cause of anomaly.
        
        Returns:
            Dictionary with root cause type, description, and contributing factors
        """
        root_cause_type = 'unknown'
        description = f"Anomaly detected in {anomaly.account_code or 'unknown account'}"
        factors = []
        
        # Analyze based on anomaly type
        if anomaly.anomaly_type:
            if 'percentage_change' in anomaly.anomaly_type.lower():
                root_cause_type = 'sudden_change'
                description = f"Sudden {anomaly.percentage_change:+.1f}% change detected"
                factors.append({
                    'factor': 'percentage_change',
                    'value': float(anomaly.percentage_change) if anomaly.percentage_change else None,
                    'impact': 'high' if abs(anomaly.percentage_change or 0) > 100 else 'medium'
                })
            
            elif 'z_score' in anomaly.anomaly_type.lower():
                root_cause_type = 'statistical_outlier'
                description = f"Statistical outlier detected (Z-score: {anomaly.z_score:.2f})"
                factors.append({
                    'factor': 'z_score',
                    'value': float(anomaly.z_score) if anomaly.z_score else None,
                    'impact': 'high' if abs(anomaly.z_score or 0) > 4 else 'medium'
                })
            
            elif 'missing' in anomaly.anomaly_type.lower():
                root_cause_type = 'missing_data'
                description = "Missing or incomplete data detected"
                factors.append({
                    'factor': 'data_completeness',
                    'value': 0,
                    'impact': 'high'
                })
        
        # Add context factors
        if anomaly.expected_value and anomaly.actual_value:
            deviation = abs(float(anomaly.actual_value) - float(anomaly.expected_value))
            factors.append({
                'factor': 'deviation_from_expected',
                'value': float(deviation),
                'impact': 'high' if deviation > (float(anomaly.expected_value) * 0.5) else 'medium'
            })
        
        return {
            'type': root_cause_type,
            'description': description,
            'factors': factors
        }
    
    def _generate_shap_explanation(
        self,
        anomaly: AnomalyDetection,
        feature_data: Optional[pd.DataFrame],
        model: Any
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for anomaly.
        
        Returns:
            Dictionary with SHAP values and feature importance
        """
        if feature_data is None or len(feature_data) == 0:
            return {}
        
        try:
            # Get the instance corresponding to the anomaly
            instance_idx = 0  # Assuming first row is the anomaly instance
            instance = feature_data.iloc[instance_idx:instance_idx+1]
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model) if hasattr(model, 'tree_') else shap.Explainer(model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(instance)
            
            # Get base value
            base_value = explainer.expected_value
            
            # Calculate feature importance
            if isinstance(shap_values, list):
                shap_values = shap_values[0]  # For binary classification, take first class
            
            feature_importance = {
                feature: float(shap_values[0][i])
                for i, feature in enumerate(feature_data.columns)
            }
            
            return {
                'values': shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values,
                'base_value': float(base_value) if isinstance(base_value, (int, float, np.number)) else base_value,
                'feature_importance': feature_importance
            }
        except Exception as e:
            logger.error(f"SHAP explanation error: {e}")
            return {}
    
    def _generate_lime_explanation(
        self,
        anomaly: AnomalyDetection,
        feature_data: Optional[pd.DataFrame],
        model: Any
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation for anomaly.
        
        Returns:
            Dictionary with LIME explanation data
        """
        if feature_data is None or len(feature_data) == 0:
            return {}
        
        try:
            # Get the instance corresponding to the anomaly
            instance = feature_data.iloc[0:1].values
            
            # Create LIME explainer
            explainer = lime.lime_tabular.LimeTabularExplainer(
                feature_data.values,
                feature_names=feature_data.columns.tolist(),
                mode='regression' if hasattr(model, 'predict') else 'classification',
                discretize_continuous=True
            )
            
            # Generate explanation
            explanation = explainer.explain_instance(
                instance[0],
                model.predict,
                num_features=min(10, len(feature_data.columns))
            )
            
            # Extract explanation data
            explanation_list = explanation.as_list()
            explanation_dict = {item[0]: float(item[1]) for item in explanation_list}
            
            return {
                'explanation': explanation_dict,
                'intercept': float(explanation.intercept[0]) if hasattr(explanation, 'intercept') else None,
                'score': float(explanation.score) if hasattr(explanation, 'score') else None
            }
        except Exception as e:
            logger.error(f"LIME explanation error: {e}")
            return {}
    
    def _generate_natural_language_explanation(
        self,
        anomaly: AnomalyDetection,
        root_cause: Dict[str, Any],
        shap_data: Optional[Dict[str, Any]],
        lime_data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate natural language explanation of the anomaly.
        
        Returns:
            Human-readable explanation string
        """
        explanation_parts = []
        
        # Start with root cause
        explanation_parts.append(root_cause['description'])
        
        # Add account context
        if anomaly.account_code:
            explanation_parts.append(f"Account: {anomaly.account_code}")
        
        # Add value context
        if anomaly.actual_value and anomaly.expected_value:
            explanation_parts.append(
                f"Actual value: {anomaly.actual_value:,.2f}, "
                f"Expected: {anomaly.expected_value:,.2f}"
            )
        
        # Add SHAP insights if available
        if shap_data and shap_data.get('feature_importance'):
            top_features = sorted(
                shap_data['feature_importance'].items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:3]
            
            if top_features:
                explanation_parts.append(
                    f"Key contributing factors: {', '.join([f[0] for f in top_features])}"
                )
        
        return ". ".join(explanation_parts) + "."
    
    def _generate_recommendations(
        self,
        anomaly: AnomalyDetection,
        root_cause: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations for addressing the anomaly.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Recommendation based on root cause type
        if root_cause['type'] == 'sudden_change':
            recommendations.append({
                'action': 'Review recent transactions',
                'category': 'investigation',
                'priority': 'high',
                'description': 'Investigate recent transactions or events that may have caused the sudden change'
            })
            recommendations.append({
                'action': 'Verify data accuracy',
                'category': 'validation',
                'priority': 'high',
                'description': 'Confirm that the extracted value is correct and matches source documents'
            })
        
        elif root_cause['type'] == 'statistical_outlier':
            recommendations.append({
                'action': 'Compare with historical patterns',
                'category': 'analysis',
                'priority': 'medium',
                'description': 'Review historical data to determine if this is a one-time event or a trend'
            })
            recommendations.append({
                'action': 'Check for data entry errors',
                'category': 'validation',
                'priority': 'medium',
                'description': 'Verify the data was entered correctly'
            })
        
        elif root_cause['type'] == 'missing_data':
            recommendations.append({
                'action': 'Complete missing data',
                'category': 'data_quality',
                'priority': 'high',
                'description': 'Obtain and enter the missing data to complete the analysis'
            })
        
        # Add general recommendations
        recommendations.append({
            'action': 'Document findings',
            'category': 'documentation',
            'priority': 'low',
            'description': 'Document the anomaly and any findings for future reference'
        })
        
        return recommendations
    
    def get_explanation(
        self,
        anomaly_id: int
    ) -> Optional[AnomalyExplanation]:
        """
        Get existing explanation for an anomaly.
        
        Args:
            anomaly_id: ID of the anomaly detection
        
        Returns:
            AnomalyExplanation if found, None otherwise
        """
        return self.db.query(AnomalyExplanation).filter(
            AnomalyExplanation.anomaly_detection_id == anomaly_id
        ).first()
    
    def get_explanations_for_property(
        self,
        property_id: int,
        limit: int = 100
    ) -> List[AnomalyExplanation]:
        """
        Get all explanations for anomalies in a property.
        
        Args:
            property_id: Property ID
            limit: Maximum number of explanations to return
        
        Returns:
            List of AnomalyExplanation objects
        """
        return self.db.query(AnomalyExplanation).join(
            AnomalyDetection
        ).filter(
            AnomalyDetection.property_id == property_id
        ).order_by(
            AnomalyExplanation.explanation_generated_at.desc()
        ).limit(limit).all()

