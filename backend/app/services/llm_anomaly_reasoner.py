"""
LLM-Powered Anomaly Reasoning Service

Uses Claude 3.5 Sonnet or GPT-4o to analyze anomalies and generate
business-readable explanations with full document context.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
import json
import logging
import os

from app.models.anomaly_detection import AnomalyDetection
from app.models.document_upload import DocumentUpload

logger = logging.getLogger(__name__)

# LLM imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not available")


class LLMAnomalyReasoner:
    """
    Uses LLMs to generate business-readable explanations for anomalies.
    
    Supports:
    - Claude 3.5 Sonnet (preferred)
    - GPT-4o (fallback)
    """
    
    def __init__(self, db: Session):
        """Initialize LLM reasoner."""
        self.db = db
        
        # Get API keys from environment (from .cursor/mcp.json)
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize clients
        self.anthropic_client = None
        self.openai_client = None
        
        if ANTHROPIC_AVAILABLE and self.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
    
    def generate_explanation(
        self,
        anomaly_id: int,
        use_claude: bool = True
    ) -> Dict[str, Any]:
        """
        Generate business-readable explanation for an anomaly.
        
        Args:
            anomaly_id: AnomalyDetection ID
            use_claude: Use Claude (True) or GPT-4o (False)
            
        Returns:
            Dict with explanation and root cause candidates
        """
        anomaly = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.id == anomaly_id
        ).first()
        
        if not anomaly:
            raise ValueError(f"Anomaly {anomaly_id} not found")
        
        # Get document context
        document_context = self._get_document_context(anomaly.document_id)
        
        # Build prompt
        prompt = self._build_prompt(anomaly, document_context)
        
        # Generate explanation
        if use_claude and self.anthropic_client:
            explanation = self._generate_with_claude(prompt)
        elif self.openai_client:
            explanation = self._generate_with_openai(prompt)
        else:
            logger.warning("No LLM client available")
            return {
                'explanation': "LLM explanation unavailable",
                'root_cause_candidates': []
            }
        
        # Parse and store
        root_cause_candidates = self._parse_root_causes(explanation)
        
        # Update anomaly record
        if not anomaly.root_cause_candidates:
            anomaly.root_cause_candidates = {}
        
        anomaly.root_cause_candidates.update({
            'llm_explanation': explanation,
            'root_causes': root_cause_candidates,
            'generated_at': datetime.utcnow().isoformat(),
            'model_used': 'claude-3-5-sonnet' if use_claude else 'gpt-4o'
        })
        
        self.db.commit()
        
        return {
            'explanation': explanation,
            'root_cause_candidates': root_cause_candidates
        }
    
    def _get_document_context(self, document_id: int) -> Dict[str, Any]:
        """Get document context for the anomaly."""
        document = self.db.query(DocumentUpload).filter(
            DocumentUpload.id == document_id
        ).first()
        
        if not document:
            return {}
        
        return {
            'document_type': document.document_type,
            'file_name': document.file_name,
            'upload_date': document.upload_date.isoformat() if document.upload_date else None,
            'property_id': document.property_id,
            'period_id': document.period_id
        }
    
    def _build_prompt(
        self,
        anomaly: AnomalyDetection,
        document_context: Dict[str, Any]
    ) -> str:
        """Build LLM prompt for anomaly explanation."""
        prompt = f"""Analyze this financial anomaly and provide a business-readable explanation.

Anomaly Details:
- Account: {anomaly.field_name}
- Actual Value: {anomaly.field_value}
- Expected Value: {anomaly.expected_value}
- Z-Score: {anomaly.z_score}
- Percentage Change: {anomaly.percentage_change}%
- Severity: {anomaly.severity}
- Anomaly Type: {anomaly.anomaly_type}

Document Context:
- Type: {document_context.get('document_type', 'unknown')}
- Period: {document_context.get('period_id', 'unknown')}

Please provide:
1. A clear, business-readable explanation of why this anomaly occurred
2. Top 3 most likely root causes with confidence levels
3. Recommended actions to investigate or resolve

Format the response as JSON with keys: explanation, root_causes (array), recommendations (array).
"""
        return prompt
    
    def _generate_with_claude(self, prompt: str) -> str:
        """Generate explanation using Claude 3.5 Sonnet."""
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"Error generating explanation: {str(e)}"
    
    def _generate_with_openai(self, prompt: str) -> str:
        """Generate explanation using GPT-4o."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error generating explanation: {str(e)}"
    
    def _parse_root_causes(self, explanation: str) -> List[Dict[str, Any]]:
        """Parse root causes from LLM response."""
        try:
            # Try to parse as JSON
            if explanation.strip().startswith('{'):
                data = json.loads(explanation)
                return data.get('root_causes', [])
            
            # Fallback: extract from text
            root_causes = []
            lines = explanation.split('\n')
            for line in lines:
                if 'root cause' in line.lower() or 'likely cause' in line.lower():
                    root_causes.append({
                        'cause': line.strip(),
                        'confidence': 0.7
                    })
            
            return root_causes[:3]  # Top 3
            
        except Exception as e:
            logger.warning(f"Error parsing root causes: {e}")
            return []
