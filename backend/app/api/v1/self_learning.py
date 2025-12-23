"""
Self-Learning API Endpoints

API endpoints for the self-learning system.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.services.issue_capture_service import IssueCaptureService
from app.services.preflight_check_service import PreflightCheckService
from app.services.self_learning_engine import SelfLearningEngine
from app.services.mcp_learning_service import MCPLearningService
from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.issue_capture import IssueCapture

router = APIRouter()


class CaptureIssueRequest(BaseModel):
    error_message: str
    issue_category: str
    severity: str = "error"
    context: Optional[Dict[str, Any]] = None
    upload_id: Optional[int] = None
    document_type: Optional[str] = None
    property_id: Optional[int] = None
    period_id: Optional[int] = None


class ResolveIssueRequest(BaseModel):
    fix_description: str
    fix_code_location: Optional[str] = None
    fix_implementation: Optional[str] = None


class PreflightCheckRequest(BaseModel):
    operation: str  # 'upload' or 'extraction'
    document_type: Optional[str] = None
    property_code: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/self-learning/capture-issue")
async def capture_issue(
    request: CaptureIssueRequest,
    db: Session = Depends(get_db)
):
    """Capture a new issue"""
    try:
        service = IssueCaptureService(db)
        capture = service.capture_error(
            error=None,
            error_message=request.error_message,
            issue_category=request.issue_category,
            severity=request.severity,
            context=request.context,
            upload_id=request.upload_id,
            document_type=request.document_type,
            property_id=request.property_id,
            period_id=request.period_id
        )
        
        if capture:
            return {
                "success": True,
                "capture_id": capture.id,
                "issue_kb_id": capture.issue_kb_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to capture issue"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/self-learning/preflight-check")
async def preflight_check(
    request: PreflightCheckRequest,
    db: Session = Depends(get_db)
):
    """Get pre-flight check results"""
    try:
        service = PreflightCheckService(db)
        
        if request.operation == "upload":
            result = service.check_before_upload(
                document_type=request.document_type,
                property_code=request.property_code,
                filename=request.filename,
                file_size=request.file_size,
                context=request.context
            )
        elif request.operation == "extraction":
            result = service.check_before_extraction(
                upload_id=request.context.get("upload_id") if request.context else None,
                document_type=request.document_type,
                extraction_engine=request.context.get("extraction_engine") if request.context else None,
                file_size=request.file_size,
                context=request.context
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {request.operation}"
            )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/self-learning/known-issues")
async def get_known_issues(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get list of known issues"""
    try:
        query = db.query(IssueKnowledgeBase)
        
        if status_filter:
            query = query.filter(IssueKnowledgeBase.status == status_filter)
        if category:
            query = query.filter(IssueKnowledgeBase.issue_category == category)
        
        issues = query.order_by(IssueKnowledgeBase.occurrence_count.desc()).limit(limit).all()
        
        return {
            "issues": [
                {
                    "id": issue.id,
                    "issue_type": issue.issue_type,
                    "issue_category": issue.issue_category,
                    "status": issue.status,
                    "occurrence_count": issue.occurrence_count,
                    "last_occurred_at": issue.last_occurred_at.isoformat() if issue.last_occurred_at else None,
                    "confidence_score": float(issue.confidence_score) if issue.confidence_score else None,
                    "fix_applied": issue.fix_applied
                }
                for issue in issues
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/self-learning/resolve-issue/{issue_kb_id}")
async def resolve_issue(
    issue_kb_id: int,
    request: ResolveIssueRequest,
    db: Session = Depends(get_db)
):
    """Mark an issue as resolved"""
    try:
        engine = SelfLearningEngine(db)
        mcp_service = MCPLearningService(db)
        
        success = engine.learn_from_resolution(
            issue_kb_id=issue_kb_id,
            fix_description=request.fix_description,
            fix_code_location=request.fix_code_location,
            fix_implementation=request.fix_implementation
        )
        
        if success:
            # Update MCP task if exists
            mcp_service.update_task_on_resolution(issue_kb_id, request.fix_description)
            
            return {
                "success": True,
                "message": "Issue marked as resolved"
            }
        else:
            return {
                "success": False,
                "error": "Failed to resolve issue"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/self-learning/stats")
async def get_learning_stats(
    db: Session = Depends(get_db)
):
    """Get learning system statistics"""
    try:
        total_issues = db.query(IssueKnowledgeBase).count()
        active_issues = db.query(IssueKnowledgeBase).filter(
            IssueKnowledgeBase.status == "active"
        ).count()
        resolved_issues = db.query(IssueKnowledgeBase).filter(
            IssueKnowledgeBase.status == "resolved"
        ).count()
        
        total_captures = db.query(IssueCapture).count()
        unresolved_captures = db.query(IssueCapture).filter(
            IssueCapture.resolved == False
        ).count()
        
        total_rules = db.query(PreventionRule).filter(
            PreventionRule.is_active == True
        ).count()
        
        return {
            "knowledge_base": {
                "total_issues": total_issues,
                "active_issues": active_issues,
                "resolved_issues": resolved_issues
            },
            "captures": {
                "total_captures": total_captures,
                "unresolved_captures": unresolved_captures
            },
            "prevention_rules": {
                "active_rules": total_rules
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/self-learning/issue-captures/{issue_kb_id}")
async def get_issue_captures(
    issue_kb_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get captures for a specific issue"""
    try:
        service = IssueCaptureService(db)
        captures = service.get_issue_captures(issue_kb_id=issue_kb_id, limit=limit)
        
        return {
            "captures": [
                {
                    "id": capture.id,
                    "error_message": capture.error_message,
                    "severity": capture.severity,
                    "captured_at": capture.captured_at.isoformat() if capture.captured_at else None,
                    "resolved": capture.resolved,
                    "context": capture.context
                }
                for capture in captures
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

