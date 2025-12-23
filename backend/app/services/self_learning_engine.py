"""
Self-Learning Engine

Analyzes captured issues, identifies patterns, and generates prevention strategies.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.issue_capture import IssueCapture
from app.models.prevention_rule import PreventionRule

logger = logging.getLogger(__name__)


class SelfLearningEngine:
    """Engine for learning from issues and generating prevention strategies"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_issue_patterns(
        self,
        days_back: int = 7,
        min_occurrences: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze captured issues to identify recurring patterns.
        
        Args:
            days_back: Number of days to look back
            min_occurrences: Minimum occurrences to consider a pattern
        
        Returns:
            List of identified patterns with statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Get unresolved captures from the last N days
            captures = self.db.query(IssueCapture).filter(
                and_(
                    IssueCapture.resolved == False,
                    IssueCapture.captured_at >= cutoff_date
                )
            ).all()
            
            # Group by error message pattern
            error_patterns = Counter()
            context_patterns = {}
            
            for capture in captures:
                # Extract error pattern
                error_msg = capture.error_message
                # Normalize error message (remove specific values)
                normalized = self._normalize_error_message(error_msg)
                error_patterns[normalized] += 1
                
                # Track context patterns
                if normalized not in context_patterns:
                    context_patterns[normalized] = {
                        "document_types": Counter(),
                        "properties": Counter(),
                        "extraction_engines": Counter(),
                        "file_sizes": [],
                        "contexts": []
                    }
                
                if capture.document_type:
                    context_patterns[normalized]["document_types"][capture.document_type] += 1
                if capture.property_id:
                    context_patterns[normalized]["properties"][capture.property_id] += 1
                if capture.context:
                    ctx = capture.context
                    if ctx.get("extraction_engine"):
                        context_patterns[normalized]["extraction_engines"][ctx["extraction_engine"]] += 1
                    if ctx.get("file_size"):
                        context_patterns[normalized]["file_sizes"].append(ctx["file_size"])
                    context_patterns[normalized]["contexts"].append(ctx)
            
            # Identify significant patterns
            patterns = []
            for error_pattern, count in error_patterns.items():
                if count >= min_occurrences:
                    pattern_info = {
                        "error_pattern": error_pattern,
                        "occurrence_count": count,
                        "context": context_patterns.get(error_pattern, {}),
                        "confidence": min(count / 10.0, 1.0)  # Confidence based on occurrences
                    }
                    patterns.append(pattern_info)
            
            return sorted(patterns, key=lambda x: x["occurrence_count"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error analyzing issue patterns: {e}")
            return []
    
    def generate_prevention_strategy(
        self,
        issue_kb_id: int,
        pattern_analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[PreventionRule]:
        """
        Generate a prevention strategy for a known issue.
        
        Args:
            issue_kb_id: Issue knowledge base ID
            pattern_analysis: Optional pattern analysis results
        
        Returns:
            PreventionRule: Generated prevention rule
        """
        try:
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.id == issue_kb_id
            ).first()
            
            if not issue:
                return None
            
            # Analyze issue to determine prevention strategy
            captures = self.db.query(IssueCapture).filter(
                IssueCapture.issue_kb_id == issue_kb_id
            ).limit(100).all()
            
            if not captures:
                return None
            
            # Determine rule type and action based on issue type
            rule_type = "auto_fix"
            rule_condition = {}
            rule_action = {}
            
            # Extract common context from captures
            document_types = [c.document_type for c in captures if c.document_type]
            if document_types:
                most_common_type = Counter(document_types).most_common(1)[0][0]
                rule_condition["document_type"] = most_common_type
            
            # Generate action based on issue type
            if "document_type_mismatch" in issue.issue_type:
                rule_action = {
                    "action_type": "skip_validation",
                    "validation_rule": "document_type_mismatch"
                }
            
            elif "year_mismatch" in issue.issue_type or "period_mismatch" in issue.issue_type:
                # Check if it's rent_roll with lease dates
                if document_types and "rent_roll" in document_types:
                    rule_action = {
                        "action_type": "skip_validation",
                        "validation_rule": "year_mismatch"
                    }
                else:
                    rule_action = {
                        "action_type": "auto_fix",
                        "fix_method": "use_statement_date",
                        "parameters": {"priority": "statement_date"}
                    }
            
            elif "extraction_timeout" in issue.issue_type or "extraction_error" in issue.issue_type:
                # Check file sizes
                file_sizes = [c.context.get("file_size") for c in captures if c.context and c.context.get("file_size")]
                if file_sizes:
                    avg_size = sum(file_sizes) / len(file_sizes)
                    if avg_size > 10 * 1024 * 1024:  # > 10MB
                        rule_condition["file_size_min"] = 10 * 1024 * 1024
                        rule_action = {
                            "action_type": "use_extraction_strategy",
                            "strategy": "fast",
                            "engine": "pymupdf"
                        }
            
            # Create prevention rule
            if rule_action:
                rule = PreventionRule(
                    issue_kb_id=issue_kb_id,
                    rule_type=rule_type,
                    rule_condition=rule_condition,
                    rule_action=rule_action,
                    is_active=True,
                    priority=10  # Default priority
                )
                
                self.db.add(rule)
                self.db.commit()
                self.db.refresh(rule)
                
                logger.info(f"Generated prevention rule for issue {issue_kb_id}")
                return rule
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating prevention strategy: {e}")
            self.db.rollback()
            return None
    
    def learn_from_resolution(
        self,
        issue_kb_id: int,
        fix_description: str,
        fix_code_location: Optional[str] = None,
        fix_implementation: Optional[str] = None,
        resolved_by: Optional[int] = None
    ) -> bool:
        """
        Update knowledge base when an issue is resolved.
        
        Args:
            issue_kb_id: Issue knowledge base ID
            fix_description: Description of the fix
            fix_code_location: Code location where fix was applied
            fix_implementation: Implementation details
            resolved_by: User ID who resolved it
        
        Returns:
            bool: True if successful
        """
        try:
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.id == issue_kb_id
            ).first()
            
            if not issue:
                return False
            
            # Update issue with fix information
            issue.status = "resolved"
            issue.resolved_at = datetime.now()
            issue.resolved_by = resolved_by
            issue.fix_applied = fix_description
            issue.fix_code_location = fix_code_location
            issue.fix_implementation = fix_implementation
            
            # Generate prevention rule if not exists
            existing_rule = self.db.query(PreventionRule).filter(
                PreventionRule.issue_kb_id == issue_kb_id,
                PreventionRule.is_active == True
            ).first()
            
            if not existing_rule:
                self.generate_prevention_strategy(issue_kb_id)
            
            self.db.commit()
            
            logger.info(f"Learned from resolution of issue {issue_kb_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error learning from resolution: {e}")
            self.db.rollback()
            return False
    
    def suggest_fixes(
        self,
        issue_capture_id: int
    ) -> List[Dict[str, Any]]:
        """
        Suggest fixes for a new issue based on similar resolved issues.
        
        Args:
            issue_capture_id: Issue capture ID
        
        Returns:
            List of suggested fixes
        """
        try:
            capture = self.db.query(IssueCapture).filter(
                IssueCapture.id == issue_capture_id
            ).first()
            
            if not capture:
                return []
            
            # Find similar resolved issues
            similar_issues = self.db.query(IssueKnowledgeBase).filter(
                and_(
                    IssueKnowledgeBase.issue_category == capture.issue_category,
                    IssueKnowledgeBase.status == "resolved",
                    IssueKnowledgeBase.fix_applied.isnot(None)
                )
            ).all()
            
            suggestions = []
            for issue in similar_issues:
                # Check similarity
                if self._issues_similar(capture, issue):
                    suggestions.append({
                        "issue_id": issue.id,
                        "issue_type": issue.issue_type,
                        "fix_description": issue.fix_applied,
                        "fix_code_location": issue.fix_code_location,
                        "confidence": issue.confidence_score
                    })
            
            return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error suggesting fixes: {e}")
            return []
    
    def _normalize_error_message(self, error_msg: str) -> str:
        """Normalize error message by removing specific values"""
        import re
        # Replace numbers with placeholders
        normalized = re.sub(r'\d+', 'N', error_msg)
        # Replace specific property codes with placeholder
        normalized = re.sub(r'[A-Z]{3,5}\d{3}', 'PROP', normalized)
        # Replace years with placeholder
        normalized = re.sub(r'20\d{2}', 'YEAR', normalized)
        return normalized
    
    def _issues_similar(
        self,
        capture: IssueCapture,
        issue: IssueKnowledgeBase
    ) -> bool:
        """Check if capture is similar to a known issue"""
        # Check category
        if capture.issue_category != issue.issue_category:
            return False
        
        # Check document type
        if capture.document_type and issue.context:
            issue_doc_type = issue.context.get("document_type")
            if issue_doc_type and capture.document_type != issue_doc_type:
                return False
        
        # Check error message pattern
        if issue.error_message_pattern:
            import re
            try:
                if re.search(issue.error_message_pattern, capture.error_message, re.IGNORECASE):
                    return True
            except re.error:
                pass
        
        return False
    
    def create_issue_knowledge_entry(
        self,
        issue_type: str,
        issue_category: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        error_pattern: Optional[str] = None
    ) -> IssueKnowledgeBase:
        """
        Create a new issue knowledge base entry from a capture.
        
        Args:
            issue_type: Type of issue
            issue_category: Category
            error_message: Error message
            context: Context dictionary
            error_pattern: Error pattern (regex)
        
        Returns:
            IssueKnowledgeBase: Created entry
        """
        try:
            issue = IssueKnowledgeBase(
                issue_type=issue_type,
                issue_category=issue_category,
                error_message_pattern=error_pattern or self._normalize_error_message(error_message),
                context=context or {},
                status="active",
                occurrence_count=1,
                first_occurred_at=datetime.now(),
                last_occurred_at=datetime.now(),
                confidence_score=0.5
            )
            
            self.db.add(issue)
            self.db.commit()
            self.db.refresh(issue)
            
            logger.info(f"Created issue knowledge entry: {issue_type}")
            return issue
            
        except Exception as e:
            logger.error(f"Error creating issue knowledge entry: {e}")
            self.db.rollback()
            return None

