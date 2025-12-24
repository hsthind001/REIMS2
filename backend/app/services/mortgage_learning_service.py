"""
Mortgage Statement Extraction Learning Service
Learns from successful extractions and applies learned patterns
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import json
import logging

logger = logging.getLogger(__name__)


class MortgageLearningService:
    """Learn from successful mortgage statement extractions and apply learned patterns"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def learn_from_successful_extraction(
        self,
        extracted_fields: Dict,
        field_patterns_used: Dict[str, str],
        lender_name: Optional[str] = None,
        confidence_score: float = 0.0
    ) -> None:
        """
        Learn from a successful extraction by storing which patterns worked
        
        Args:
            extracted_fields: Successfully extracted fields
            field_patterns_used: Mapping of field_name -> pattern that successfully extracted it
            lender_name: Optional lender name for lender-specific learning
            confidence_score: Confidence score of the extraction
        """
        try:
            # Store learned patterns in the database
            # This would use a mortgage_extraction_patterns table
            # For now, we'll use the existing issue_knowledge_base table
            from app.models.issue_knowledge_base import IssueKnowledgeBase
            
            # Create a knowledge entry for successful patterns
            pattern_data = {
                "field_patterns": field_patterns_used,
                "extracted_fields": list(extracted_fields.keys()),
                "lender": lender_name,
                "confidence": confidence_score,
                "learned_at": datetime.utcnow().isoformat()
            }
            
            # Check if similar pattern already exists
            existing = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type == "mortgage_extraction_pattern",
                IssueKnowledgeBase.issue_category == (lender_name or "generic")
            ).first()
            
            if existing:
                # Update existing pattern with new success
                existing.fix_implementation = json.dumps(pattern_data)
                existing.last_occurred_at = datetime.utcnow()
                existing.occurrence_count = (existing.occurrence_count or 0) + 1
                existing.status = "active"
            else:
                # Create new pattern entry
                new_pattern = IssueKnowledgeBase(
                    issue_type="mortgage_extraction_pattern",
                    issue_category=lender_name or "generic",
                    error_message_pattern="Successful mortgage extraction pattern",
                    fix_implementation=json.dumps(pattern_data),
                    last_occurred_at=datetime.utcnow(),
                    occurrence_count=1,
                    status="active"
                )
                self.db.add(new_pattern)
            
            self.db.commit()
            logger.info(f"Learned pattern for lender {lender_name or 'generic'}: {len(field_patterns_used)} fields")
            
        except Exception as e:
            logger.error(f"Failed to learn from extraction: {e}")
            self.db.rollback()
    
    def get_learned_patterns(
        self,
        lender_name: Optional[str] = None,
        field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve learned patterns for a lender or field
        
        Args:
            lender_name: Optional lender name to filter patterns
            field_name: Optional field name to filter patterns
            
        Returns:
            Dictionary of learned patterns
        """
        try:
            from app.models.issue_knowledge_base import IssueKnowledgeBase
            
            query = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type == "mortgage_extraction_pattern",
                IssueKnowledgeBase.status == "active"
            )
            
            if lender_name:
                query = query.filter(IssueKnowledgeBase.issue_category == lender_name)
            
            patterns = query.order_by(
                IssueKnowledgeBase.occurrence_count.desc(),
                IssueKnowledgeBase.last_occurred_at.desc()
            ).all()
            
            result = {}
            for pattern in patterns:
                try:
                    pattern_data = json.loads(pattern.fix_implementation or "{}")
                    field_patterns = pattern_data.get("field_patterns", {})
                    
                    if field_name:
                        if field_name in field_patterns:
                            result[field_name] = field_patterns[field_name]
                    else:
                        result.update(field_patterns)
                        
                except json.JSONDecodeError:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve learned patterns: {e}")
            return {}
    
    def apply_learned_patterns(
        self,
        field_patterns: Dict,
        lender_name: Optional[str] = None
    ) -> Dict:
        """
        Apply learned patterns to field patterns, prioritizing learned patterns
        
        Args:
            field_patterns: Default field patterns
            lender_name: Optional lender name for lender-specific patterns
            
        Returns:
            Updated field patterns with learned patterns prioritized
        """
        learned_patterns = self.get_learned_patterns(lender_name=lender_name)
        
        if not learned_patterns:
            return field_patterns
        
        # Merge learned patterns, prioritizing them
        updated_patterns = field_patterns.copy()
        
        for field_name, learned_pattern in learned_patterns.items():
            if field_name in updated_patterns:
                # Prepend learned pattern to the patterns list
                current_patterns = updated_patterns[field_name].get("patterns", [])
                if isinstance(learned_pattern, str):
                    # Learned pattern is a single pattern string
                    updated_patterns[field_name]["patterns"] = [learned_pattern] + current_patterns
                elif isinstance(learned_pattern, list):
                    # Learned pattern is a list of patterns
                    updated_patterns[field_name]["patterns"] = learned_pattern + current_patterns
            else:
                # New field learned
                updated_patterns[field_name] = {
                    "patterns": learned_pattern if isinstance(learned_pattern, list) else [learned_pattern],
                    "field_type": "text",  # Default, should be inferred
                    "required": False
                }
        
        return updated_patterns
    
    def learn_period_detection_pattern(
        self,
        detected_month: int,
        detected_year: int,
        pattern_used: str,
        confidence: float
    ) -> None:
        """
        Learn period detection patterns for mortgage statements
        
        Args:
            detected_month: Month that was detected
            detected_year: Year that was detected
            pattern_used: Pattern that successfully detected the period
            confidence: Confidence score of the detection
        """
        try:
            from app.models.issue_knowledge_base import IssueKnowledgeBase
            
            pattern_data = {
                "pattern": pattern_used,
                "detected_month": detected_month,
                "detected_year": detected_year,
                "confidence": confidence,
                "learned_at": datetime.utcnow().isoformat()
            }
            
            # Store as a period detection pattern
            existing = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type == "mortgage_period_detection",
                IssueKnowledgeBase.issue_category == "as_of_date_pattern"
            ).first()
            
            if existing:
                existing.fix_implementation = json.dumps(pattern_data)
                existing.last_occurred_at = datetime.utcnow()
                existing.occurrence_count = (existing.occurrence_count or 0) + 1
                existing.status = "active"
            else:
                new_pattern = IssueKnowledgeBase(
                    issue_type="mortgage_period_detection",
                    issue_category="as_of_date_pattern",
                    error_message_pattern="LOAN INFORMATION As of Date is authoritative for mortgage statements",
                    fix_implementation=json.dumps(pattern_data),
                    last_occurred_at=datetime.utcnow(),
                    occurrence_count=1,
                    status="active"
                )
                self.db.add(new_pattern)
            
            self.db.commit()
            logger.info(f"Learned period detection pattern: {pattern_used}")
            
        except Exception as e:
            logger.error(f"Failed to learn period detection pattern: {e}")
            self.db.rollback()

