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


@celery_app.task(name="app.tasks.learning_tasks.analyze_reconciliation_patterns", bind=True)
def analyze_reconciliation_patterns(self: Task, days_back: int = 30):
    """
    Periodic task to analyze reconciliation patterns and discover new relationships.
    
    Args:
        days_back: Number of days to look back for analysis
    """
    db = SessionLocal()
    try:
        from app.services.match_learning_service import MatchLearningService
        from app.services.relationship_discovery_service import RelationshipDiscoveryService
        from app.models.forensic_reconciliation_session import ForensicReconciliationSession
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Get recent sessions
        recent_sessions = db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.started_at >= cutoff_date
        ).all()
        
        learning_service = MatchLearningService(db)
        discovery_service = RelationshipDiscoveryService(db)
        
        total_patterns = 0
        total_synonyms = 0
        
        # Analyze successful matches from recent sessions
        for session in recent_sessions:
            result = learning_service.analyze_successful_matches(
                session_id=session.id,
                property_id=session.property_id,
                period_id=session.period_id
            )
            total_patterns += result.get('patterns_created', 0)
            total_synonyms += result.get('synonyms_created', 0)
        
        # Discover new relationships
        discovery_result = discovery_service.discover_relationships()
        
        logger.info(f"Analyzed {len(recent_sessions)} sessions: {total_patterns} patterns, {total_synonyms} synonyms, {discovery_result.get('rules_suggested', 0)} rules suggested")
        
    except Exception as e:
        logger.error(f"Error analyzing reconciliation patterns: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.learning_tasks.update_matching_rules", bind=True)
def update_matching_rules(self: Task):
    """
    Periodic task to update matching rules based on learned patterns.
    """
    db = SessionLocal()
    try:
        from app.services.account_code_discovery_service import AccountCodeDiscoveryService
        from app.models.learned_match_pattern import LearnedMatchPattern
        
        discovery_service = AccountCodeDiscoveryService(db)
        
        # Discover account codes globally
        discovery_result = discovery_service.discover_all_account_codes()
        
        # Get high-confidence learned patterns
        high_confidence_patterns = db.query(LearnedMatchPattern).filter(
            and_(
                LearnedMatchPattern.is_active == True,
                LearnedMatchPattern.success_rate >= 80.0,
                LearnedMatchPattern.match_count >= 3
            )
        ).all()
        
        logger.info(f"Updated matching rules: {discovery_result.get('total_codes_discovered', 0)} codes, {len(high_confidence_patterns)} high-confidence patterns")
        
    except Exception as e:
        logger.error(f"Error updating matching rules: {e}")
    finally:
        db.close()


@celery_app.task(name="app.tasks.learning_tasks.train_ml_models", bind=True)
def train_ml_models(self: Task):
    """
    Periodic task to retrain ML models with new data.
    
    Note: This is a placeholder for future ML model training.
    Currently, the system uses rule-based and pattern-based matching.
    """
    db = SessionLocal()
    try:
        from app.models.match_confidence_model import MatchConfidenceModel
        from app.models.forensic_match import ForensicMatch
        
        # Get approved matches for training data
        approved_matches = db.query(ForensicMatch).filter(
            ForensicMatch.status == 'approved'
        ).limit(1000).all()
        
        if len(approved_matches) < 10:
            logger.info("Insufficient training data. Need at least 10 approved matches.")
            return
        
        # For now, just log statistics
        # In the future, this will train actual ML models
        confidences = [float(m.confidence_score) for m in approved_matches if m.confidence_score]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        logger.info(f"ML model training placeholder: {len(approved_matches)} training samples, avg confidence: {avg_confidence:.2f}")
        
        # TODO: Implement actual ML model training
        # - Train XGBoost classifier for relationship prediction
        # - Train BERT embeddings for account name similarity
        # - Train neural network for confidence prediction
        
    except Exception as e:
        logger.error(f"Error training ML models: {e}")
    finally:
        db.close()

