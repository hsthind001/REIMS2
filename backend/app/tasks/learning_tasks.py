"""
Learning Background Tasks

Background tasks for analyzing issues and syncing with MCP server.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from celery import Task
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.services.self_learning_engine import SelfLearningEngine
from app.services.mcp_learning_service import MCPLearningService
from app.services.issue_capture_service import IssueCaptureService
from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.issue_capture import IssueCapture

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.learning_tasks.analyze_captured_issues", bind=True)
def analyze_captured_issues(self: Task, days_back: int = 7, min_occurrences: int = 3):
    """
    Periodic task to analyze captured issues and identify patterns.
    
    Args:
        days_back: Number of days to look back
        min_occurrences: Minimum occurrences to consider a pattern
    """
    db = SessionLocal()
    try:
        engine = SelfLearningEngine(db)
        
        # Analyze patterns
        patterns = engine.analyze_issue_patterns(days_back=days_back, min_occurrences=min_occurrences)
        
        logger.info(f"Analyzed {len(patterns)} issue patterns")
        
        # For each pattern, create or update knowledge base entry
        for pattern in patterns:
            error_pattern = pattern["error_pattern"]
            occurrence_count = pattern["occurrence_count"]
            context = pattern.get("context", {})
            
            # Check if issue already exists
            existing_issue = db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.error_message_pattern == error_pattern
            ).first()
            
            if existing_issue:
                # Update existing issue
                existing_issue.occurrence_count += occurrence_count
                existing_issue.last_occurred_at = datetime.now()
                existing_issue.confidence_score = min(float(existing_issue.confidence_score) + 0.1, 1.0)
            else:
                # Create new issue entry
                # Determine issue type from pattern
                issue_type = "unknown_error"
                if "mismatch" in error_pattern.lower():
                    if "type" in error_pattern.lower():
                        issue_type = "document_type_mismatch"
                    elif "year" in error_pattern.lower():
                        issue_type = "year_mismatch"
                    elif "month" in error_pattern.lower() or "period" in error_pattern.lower():
                        issue_type = "period_mismatch"
                
                # Determine category from context
                issue_category = "validation"
                if context.get("extraction_engines"):
                    issue_category = "extraction"
                
                # Extract document type from context
                doc_types = context.get("document_types", {})
                most_common_doc_type = None
                if doc_types:
                    most_common_doc_type = max(doc_types.items(), key=lambda x: x[1])[0]
                
                new_issue = engine.create_issue_knowledge_entry(
                    issue_type=issue_type,
                    issue_category=issue_category,
                    error_message=error_pattern,
                    context={
                        "document_type": most_common_doc_type,
                        **(context or {})
                    },
                    error_pattern=error_pattern
                )
                
                if new_issue:
                    # Generate prevention strategy
                    engine.generate_prevention_strategy(new_issue.id, pattern)
        
        db.commit()
        logger.info(f"Successfully analyzed and processed {len(patterns)} patterns")
        
    except Exception as e:
        logger.error(f"Error analyzing captured issues: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="app.tasks.learning_tasks.sync_mcp_tasks", bind=True)
def sync_mcp_tasks(self: Task, tag: str = "self-learning"):
    """
    Periodic task to sync with MCP server.
    
    Args:
        tag: Tag context for MCP tasks
    """
    db = SessionLocal()
    try:
        mcp_service = MCPLearningService(db)
        
        # Sync learned fixes
        sync_result = mcp_service.sync_learned_fixes(tag=tag)
        logger.info(f"Synced {sync_result['synced_count']} fixes with MCP")
        
        # Create tasks for critical issues
        created_count = mcp_service.create_tasks_for_critical_issues(min_occurrences=5, tag=tag)
        logger.info(f"Created {created_count} MCP tasks for critical issues")
        
    except Exception as e:
        logger.error(f"Error syncing MCP tasks: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.learning_tasks.cleanup_old_issues", bind=True)
def cleanup_old_issues(self: Task, days_to_keep: int = 90):
    """
    Archive old resolved issues.
    
    Args:
        days_to_keep: Number of days to keep resolved issues
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Archive old resolved issues
        old_issues = db.query(IssueKnowledgeBase).filter(
            IssueKnowledgeBase.status == "resolved",
            IssueKnowledgeBase.resolved_at < cutoff_date
        ).all()
        
        archived_count = 0
        for issue in old_issues:
            issue.status = "archived"
            archived_count += 1
        
        # Delete old resolved captures (keep for 30 days)
        capture_cutoff = datetime.now() - timedelta(days=30)
        old_captures = db.query(IssueCapture).filter(
            IssueCapture.resolved == True,
            IssueCapture.resolved_at < capture_cutoff
        ).all()
        
        deleted_count = 0
        for capture in old_captures:
            db.delete(capture)
            deleted_count += 1
        
        db.commit()
        logger.info(f"Archived {archived_count} issues and deleted {deleted_count} old captures")
        
    except Exception as e:
        logger.error(f"Error cleaning up old issues: {e}")
        db.rollback()
    finally:
        db.close()

