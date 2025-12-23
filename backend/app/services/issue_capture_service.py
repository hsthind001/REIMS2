"""
Issue Capture Service

Automatically captures errors and issues with full context for the self-learning system.
"""

import logging
import traceback
from typing import Dict, Optional, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.issue_capture import IssueCapture

logger = logging.getLogger(__name__)


class IssueCaptureService:
    """Service for capturing and managing issues"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def capture_error(
        self,
        error: Exception,
        error_message: str,
        issue_category: str,
        severity: str = "error",
        context: Optional[Dict[str, Any]] = None,
        upload_id: Optional[int] = None,
        document_type: Optional[str] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> IssueCapture:
        """
        Capture an error with full context.
        
        Args:
            error: The exception object
            error_message: Human-readable error message
            issue_category: Category ('extraction', 'validation', 'frontend', 'backend', 'ml_ai')
            severity: Severity level ('critical', 'error', 'warning', 'info')
            context: Additional context dictionary
            upload_id: Related document upload ID
            document_type: Document type if applicable
            property_id: Property ID if applicable
            period_id: Period ID if applicable
        
        Returns:
            IssueCapture: The created issue capture record
        """
        try:
            # Get stack trace
            stack_trace = None
            if error:
                stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            
            # Build context dictionary
            capture_context = context or {}
            capture_context.update({
                "error_type": type(error).__name__ if error else None,
                "error_class": str(type(error)) if error else None,
            })
            
            # Try to match existing issue pattern
            issue_kb = self.match_existing_issue(
                error_message=error_message,
                issue_category=issue_category,
                context=capture_context
            )
            
            # Create issue capture
            issue_capture = IssueCapture(
                issue_kb_id=issue_kb.id if issue_kb else None,
                upload_id=upload_id,
                document_type=document_type,
                property_id=property_id,
                period_id=period_id,
                error_message=error_message,
                stack_trace=stack_trace,
                error_type=type(error).__name__ if error else None,
                context=capture_context,
                severity=severity,
                issue_category=issue_category
            )
            
            self.db.add(issue_capture)
            self.db.commit()
            self.db.refresh(issue_capture)
            
            # Update knowledge base if matched
            if issue_kb:
                issue_kb.occurrence_count += 1
                issue_kb.last_occurred_at = datetime.now()
                self.db.commit()
            
            logger.info(f"Captured issue: {issue_category}/{severity} - {error_message[:100]}")
            
            return issue_capture
            
        except Exception as e:
            logger.error(f"Failed to capture issue: {e}")
            self.db.rollback()
            # Don't fail the main operation if issue capture fails
            return None
    
    def capture_validation_issue(
        self,
        validation_type: str,
        expected_value: Any,
        detected_value: Any,
        confidence: Optional[float] = None,
        upload_id: Optional[int] = None,
        document_type: Optional[str] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IssueCapture:
        """
        Capture a validation issue (type mismatch, year mismatch, etc.).
        
        Args:
            validation_type: Type of validation ('document_type_mismatch', 'year_mismatch', 'period_mismatch')
            expected_value: Expected value
            detected_value: Detected value
            confidence: Confidence score if available
            upload_id: Related document upload ID
            document_type: Document type
            property_id: Property ID
            period_id: Period ID
            context: Additional context
        
        Returns:
            IssueCapture: The created issue capture record
        """
        error_message = f"{validation_type}: Expected {expected_value} but detected {detected_value}"
        if confidence is not None:
            error_message += f" (confidence: {confidence}%)"
        
        capture_context = context or {}
        capture_context.update({
            "validation_type": validation_type,
            "expected_value": str(expected_value),
            "detected_value": str(detected_value),
            "confidence": confidence
        })
        
        return self.capture_error(
            error=None,
            error_message=error_message,
            issue_category="validation",
            severity="warning",
            context=capture_context,
            upload_id=upload_id,
            document_type=document_type,
            property_id=property_id,
            period_id=period_id
        )
    
    def capture_extraction_issue(
        self,
        error: Exception,
        error_message: str,
        extraction_engine: Optional[str] = None,
        file_size: Optional[int] = None,
        page_count: Optional[int] = None,
        upload_id: Optional[int] = None,
        document_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IssueCapture:
        """
        Capture an extraction issue.
        
        Args:
            error: The exception object
            error_message: Error message
            extraction_engine: Extraction engine used
            file_size: File size in bytes
            page_count: Number of pages
            upload_id: Related document upload ID
            document_type: Document type
            context: Additional context
        
        Returns:
            IssueCapture: The created issue capture record
        """
        capture_context = context or {}
        capture_context.update({
            "extraction_engine": extraction_engine,
            "file_size": file_size,
            "page_count": page_count
        })
        
        return self.capture_error(
            error=error,
            error_message=error_message,
            issue_category="extraction",
            severity="error",
            context=capture_context,
            upload_id=upload_id,
            document_type=document_type
        )
    
    def capture_frontend_error(
        self,
        error_message: str,
        api_endpoint: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IssueCapture:
        """
        Capture a frontend/API error.
        
        Args:
            error_message: Error message
            api_endpoint: API endpoint that failed
            request_id: Request ID for tracking
            user_id: User ID if available
            context: Additional context
        
        Returns:
            IssueCapture: The created issue capture record
        """
        capture_context = context or {}
        capture_context.update({
            "api_endpoint": api_endpoint,
            "request_id": request_id,
            "user_id": user_id
        })
        
        return self.capture_error(
            error=None,
            error_message=error_message,
            issue_category="frontend",
            severity="error",
            context=capture_context
        )
    
    def match_existing_issue(
        self,
        error_message: str,
        issue_category: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[IssueKnowledgeBase]:
        """
        Check if an issue matches an existing pattern in the knowledge base.
        
        Args:
            error_message: Error message to match
            issue_category: Issue category
            context: Context dictionary
        
        Returns:
            IssueKnowledgeBase: Matching issue if found, None otherwise
        """
        try:
            # Query active issues in the same category
            active_issues = self.db.query(IssueKnowledgeBase).filter(
                and_(
                    IssueKnowledgeBase.issue_category == issue_category,
                    IssueKnowledgeBase.status == 'active'
                )
            ).all()
            
            # Try to match against error patterns
            for issue in active_issues:
                # Check error message pattern
                if issue.error_message_pattern:
                    import re
                    try:
                        if re.search(issue.error_message_pattern, error_message, re.IGNORECASE):
                            # Check context match if available
                            if self._matches_context(issue.context, context):
                                return issue
                    except re.error:
                        # Invalid regex, skip
                        continue
                
                # Check error pattern
                if issue.error_pattern:
                    import re
                    try:
                        if re.search(issue.error_pattern, error_message, re.IGNORECASE):
                            if self._matches_context(issue.context, context):
                                return issue
                    except re.error:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error matching existing issue: {e}")
            return None
    
    def _matches_context(
        self,
        issue_context: Optional[Dict[str, Any]],
        capture_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if capture context matches issue context pattern.
        
        Args:
            issue_context: Context pattern from knowledge base
            capture_context: Context from current capture
        
        Returns:
            bool: True if contexts match
        """
        if not issue_context or not capture_context:
            return True  # No context to match, consider it a match
        
        # Check document type
        if 'document_type' in issue_context:
            if capture_context.get('document_type') != issue_context['document_type']:
                return False
        
        # Check property pattern
        if 'property_pattern' in issue_context:
            import re
            property_code = capture_context.get('property_code') or ''
            if not re.search(issue_context['property_pattern'], property_code, re.IGNORECASE):
                return False
        
        # Check extraction engine
        if 'extraction_engine' in issue_context:
            if capture_context.get('extraction_engine') != issue_context['extraction_engine']:
                return False
        
        # Check file size range
        if 'file_size_range' in issue_context:
            file_size = capture_context.get('file_size', 0)
            size_range = issue_context['file_size_range']
            if 'min' in size_range and file_size < size_range['min']:
                return False
            if 'max' in size_range and file_size > size_range['max']:
                return False
        
        return True
    
    def get_issue_captures(
        self,
        issue_kb_id: Optional[int] = None,
        resolved: Optional[bool] = None,
        severity: Optional[str] = None,
        issue_category: Optional[str] = None,
        limit: int = 100
    ) -> List[IssueCapture]:
        """
        Get issue captures with filters.
        
        Args:
            issue_kb_id: Filter by knowledge base issue ID
            resolved: Filter by resolved status
            severity: Filter by severity
            issue_category: Filter by category
            limit: Maximum number of results
        
        Returns:
            List[IssueCapture]: List of issue captures
        """
        query = self.db.query(IssueCapture)
        
        if issue_kb_id:
            query = query.filter(IssueCapture.issue_kb_id == issue_kb_id)
        if resolved is not None:
            query = query.filter(IssueCapture.resolved == resolved)
        if severity:
            query = query.filter(IssueCapture.severity == severity)
        if issue_category:
            query = query.filter(IssueCapture.issue_category == issue_category)
        
        return query.order_by(IssueCapture.captured_at.desc()).limit(limit).all()
    
    def mark_resolved(
        self,
        capture_id: int,
        resolved_by: Optional[int] = None,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """
        Mark an issue capture as resolved.
        
        Args:
            capture_id: Issue capture ID
            resolved_by: User ID who resolved it
            resolution_notes: Notes about the resolution
        
        Returns:
            bool: True if successful
        """
        try:
            capture = self.db.query(IssueCapture).filter(IssueCapture.id == capture_id).first()
            if not capture:
                return False
            
            capture.resolved = True
            capture.resolved_at = datetime.now()
            capture.resolved_by = resolved_by
            capture.resolution_notes = resolution_notes
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark issue as resolved: {e}")
            self.db.rollback()
            return False

