"""
Auto-Fix Service

Applies learned fixes automatically to prevent known issues.
"""

import logging
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.prevention_rule import PreventionRule
from app.services.preflight_check_service import PreflightCheckService

logger = logging.getLogger(__name__)


class AutoFixService:
    """Service for applying learned fixes automatically"""
    
    def __init__(self, db: Session):
        self.db = db
        self.preflight_service = PreflightCheckService(db)
    
    def apply_known_fixes(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply known fixes based on learned patterns.
        
        Args:
            operation: Operation type ('upload', 'extraction', 'validation')
            context: Operation context
        
        Returns:
            Dict with applied fixes and modified context
        """
        return self.preflight_service.apply_preventive_fixes(operation, context)
    
    def fix_document_type_mismatch(
        self,
        detected_type: str,
        expected_type: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-fix document type mismatch.
        
        Args:
            detected_type: Detected document type
            expected_type: Expected document type
            context: Context with document content
        
        Returns:
            Dict with fix result, or None if no fix available
        """
        try:
            # Check if we have a learned pattern for this mismatch
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type == "document_type_mismatch",
                IssueKnowledgeBase.status == "active"
            ).first()
            
            if issue and issue.prevention_strategy:
                strategy = issue.prevention_strategy
                
                # Check if context matches
                if self._context_matches(issue.context, context):
                    # Apply auto-fix: use detected type if confidence is high
                    if strategy.get("auto_fix") == "use_detected_type":
                        return {
                            "success": True,
                            "fixed_type": detected_type,
                            "reason": "Auto-fixed based on learned pattern"
                        }
                    
                    # Or skip validation
                    if strategy.get("auto_fix") == "skip_validation":
                        return {
                            "success": True,
                            "skip_validation": True,
                            "reason": "Skipping validation based on learned pattern"
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fixing document type mismatch: {e}")
            return None
    
    def fix_period_detection(
        self,
        detected_month: Optional[int],
        detected_year: Optional[int],
        expected_month: Optional[int],
        expected_year: Optional[int],
        document_type: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-fix period/year detection issues.
        
        Args:
            detected_month: Detected month
            detected_year: Detected year
            expected_month: Expected month
            expected_year: Expected year
            document_type: Document type
            context: Context with PDF content
        
        Returns:
            Dict with fix result, or None if no fix available
        """
        try:
            # Check for learned patterns
            issue_type = "year_mismatch" if detected_year != expected_year else "period_mismatch"
            
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type == issue_type,
                IssueKnowledgeBase.status == "active"
            ).first()
            
            if issue and issue.prevention_strategy:
                strategy = issue.prevention_strategy
                issue_context = issue.context or {}
                
                # Check if document type matches
                if issue_context.get("document_type") == document_type:
                    # Apply fix: use statement date
                    if strategy.get("auto_fix") == "use_statement_date":
                        # Extract statement date from context if available
                        if context.get("statement_date"):
                            stmt_date = context["statement_date"]
                            return {
                                "success": True,
                                "fixed_month": stmt_date.get("month"),
                                "fixed_year": stmt_date.get("year"),
                                "reason": "Using statement date based on learned pattern"
                            }
                    
                    # Skip validation for rent_roll
                    if document_type == "rent_roll" and strategy.get("auto_fix") == "skip_validation":
                        return {
                            "success": True,
                            "skip_validation": True,
                            "reason": "Skipping year mismatch validation for rent_roll (learned pattern)"
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fixing period detection: {e}")
            return None
    
    def fix_extraction_errors(
        self,
        error_type: str,
        extraction_engine: str,
        file_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-fix extraction errors by retrying with different strategies.
        
        Args:
            error_type: Type of extraction error
            extraction_engine: Engine that failed
            file_size: File size
            context: Additional context
        
        Returns:
            Dict with fix result (retry strategy), or None if no fix available
        """
        try:
            # Check for learned patterns
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.issue_type.like(f"%{error_type}%"),
                IssueKnowledgeBase.status == "active"
            ).first()
            
            if issue and issue.prevention_strategy:
                strategy = issue.prevention_strategy
                issue_context = issue.context or {}
                
                # Check if conditions match
                if issue_context.get("extraction_engine") == extraction_engine:
                    if file_size and issue_context.get("file_size_range"):
                        size_range = issue_context["file_size_range"]
                        if size_range.get("min") and file_size < size_range["min"]:
                            return None
                        if size_range.get("max") and file_size > size_range["max"]:
                            return None
                    
                    # Apply fix: use different engine/strategy
                    if strategy.get("auto_fix") == "use_fast_engine":
                        return {
                            "success": True,
                            "retry_engine": "pymupdf",
                            "retry_strategy": "fast",
                            "reason": "Using fast engine based on learned pattern"
                        }
                    
                    if strategy.get("auto_fix") == "use_accurate_engine":
                        return {
                            "success": True,
                            "retry_engine": "pdfplumber",
                            "retry_strategy": "accurate",
                            "reason": "Using accurate engine based on learned pattern"
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fixing extraction errors: {e}")
            return None
    
    def _context_matches(
        self,
        issue_context: Dict[str, Any],
        operation_context: Dict[str, Any]
    ) -> bool:
        """Check if operation context matches issue context pattern"""
        if not issue_context:
            return True
        
        # Check document type
        if "document_type" in issue_context:
            if operation_context.get("document_type") != issue_context["document_type"]:
                return False
        
        # Check property pattern
        if "property_pattern" in issue_context:
            import re
            property_code = operation_context.get("property_code", "")
            if not re.search(issue_context["property_pattern"], property_code, re.IGNORECASE):
                return False
        
        # Check keywords
        if "keywords" in issue_context:
            text = str(operation_context.get("filename", "") + " " + str(operation_context.get("content", ""))).lower()
            keywords = issue_context["keywords"]
            if not any(keyword.lower() in text for keyword in keywords):
                return False
        
        return True

