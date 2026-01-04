"""
Learning Background Tasks

Background tasks for analyzing issues and syncing with MCP server.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from celery import Task
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.services.self_learning_engine import SelfLearningEngine
from app.services.mcp_learning_service import MCPLearningService
from app.services.issue_capture_service import IssueCaptureService
from app.services.self_learning_extraction_service import SelfLearningExtractionService
from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.issue_capture import IssueCapture
from app.models.extraction_learning_pattern import ExtractionLearningPattern
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.learning_tasks.discover_extraction_patterns", bind=True)
def discover_extraction_patterns(self: Task, min_occurrences: int = 10, min_confidence: float = 80.0):
    """
    🔥 CRITICAL LEARNING TASK: Automatically discovers patterns from successful extractions.

    Runs daily to analyze successful extractions and create learned patterns for auto-approval.
    This is the PRIMARY way the system learns from data (not just from errors).

    Args:
        min_occurrences: Minimum times an account must appear to create pattern (default: 10)
        min_confidence: Minimum extraction confidence to consider successful (default: 80%)

    Returns:
        Dict with patterns_created count
    """
    db = SessionLocal()
    patterns_created = 0
    patterns_updated = 0

    try:
        learning_service = SelfLearningExtractionService(db)

        logger.info(f"🔍 Starting extraction pattern discovery (min_occurrences={min_occurrences}, min_confidence={min_confidence}%)")

        # =========== BALANCE SHEET PATTERNS ===========
        logger.info("📊 Analyzing Balance Sheet data...")
        bs_patterns = db.query(
            BalanceSheetData.account_code,
            BalanceSheetData.account_name,
            BalanceSheetData.property_id,
            func.count(BalanceSheetData.id).label('count'),
            func.avg(BalanceSheetData.extraction_confidence).label('avg_confidence'),
            func.min(BalanceSheetData.extraction_confidence).label('min_confidence'),
            func.max(BalanceSheetData.extraction_confidence).label('max_confidence')
        ).filter(
            BalanceSheetData.extraction_confidence >= min_confidence,
            BalanceSheetData.account_code.isnot(None),
            BalanceSheetData.account_code != 'UNMATCHED'
        ).group_by(
            BalanceSheetData.account_code,
            BalanceSheetData.account_name,
            BalanceSheetData.property_id
        ).having(
            func.count(BalanceSheetData.id) >= min_occurrences
        ).all()

        for pattern in bs_patterns:
            result = _create_or_update_pattern(
                db, learning_service, pattern, 'balance_sheet'
            )
            if result == 'created':
                patterns_created += 1
            elif result == 'updated':
                patterns_updated += 1

        logger.info(f"✅ Balance Sheet: {len(bs_patterns)} patterns found")

        # =========== INCOME STATEMENT PATTERNS ===========
        logger.info("📈 Analyzing Income Statement data...")
        is_patterns = db.query(
            IncomeStatementData.account_code,
            IncomeStatementData.account_name,
            IncomeStatementData.property_id,
            func.count(IncomeStatementData.id).label('count'),
            func.avg(IncomeStatementData.extraction_confidence).label('avg_confidence'),
            func.min(IncomeStatementData.extraction_confidence).label('min_confidence'),
            func.max(IncomeStatementData.extraction_confidence).label('max_confidence')
        ).filter(
            IncomeStatementData.extraction_confidence >= min_confidence,
            IncomeStatementData.account_code.isnot(None),
            IncomeStatementData.account_code != 'UNMATCHED'
        ).group_by(
            IncomeStatementData.account_code,
            IncomeStatementData.account_name,
            IncomeStatementData.property_id
        ).having(
            func.count(IncomeStatementData.id) >= min_occurrences
        ).all()

        for pattern in is_patterns:
            result = _create_or_update_pattern(
                db, learning_service, pattern, 'income_statement'
            )
            if result == 'created':
                patterns_created += 1
            elif result == 'updated':
                patterns_updated += 1

        logger.info(f"✅ Income Statement: {len(is_patterns)} patterns found")

        # =========== CASH FLOW PATTERNS ===========
        logger.info("💵 Analyzing Cash Flow data...")
        cf_patterns = db.query(
            CashFlowData.account_code,
            CashFlowData.account_name,
            CashFlowData.property_id,
            func.count(CashFlowData.id).label('count'),
            func.avg(CashFlowData.extraction_confidence).label('avg_confidence'),
            func.min(CashFlowData.extraction_confidence).label('min_confidence'),
            func.max(CashFlowData.extraction_confidence).label('max_confidence')
        ).filter(
            CashFlowData.extraction_confidence >= min_confidence,
            CashFlowData.account_code.isnot(None),
            CashFlowData.account_code != 'UNMATCHED'
        ).group_by(
            CashFlowData.account_code,
            CashFlowData.account_name,
            CashFlowData.property_id
        ).having(
            func.count(CashFlowData.id) >= min_occurrences
        ).all()

        for pattern in cf_patterns:
            result = _create_or_update_pattern(
                db, learning_service, pattern, 'cash_flow'
            )
            if result == 'created':
                patterns_created += 1
            elif result == 'updated':
                patterns_updated += 1

        logger.info(f"✅ Cash Flow: {len(cf_patterns)} patterns found")

        # Commit all changes
        db.commit()

        logger.info(f"""
🎉 Pattern discovery complete!
   Created: {patterns_created} new patterns
   Updated: {patterns_updated} existing patterns
   Total: {patterns_created + patterns_updated} patterns processed
        """)

        return {
            'success': True,
            'patterns_created': patterns_created,
            'patterns_updated': patterns_updated,
            'total_processed': patterns_created + patterns_updated
        }

    except Exception as e:
        logger.error(f"❌ Error discovering extraction patterns: {e}")
        db.rollback()
        return {
            'success': False,
            'error': str(e),
            'patterns_created': patterns_created,
            'patterns_updated': patterns_updated
        }
    finally:
        db.close()


def _create_or_update_pattern(
    db: Session,
    learning_service: SelfLearningExtractionService,
    pattern_data,
    document_type: str
) -> str:
    """
    Helper function to create or update an extraction learning pattern.

    Returns:
        'created' | 'updated' | 'skipped'
    """
    account_code, account_name, property_id, count, avg_confidence, min_conf, max_conf = pattern_data

    # Check if pattern already exists
    existing_pattern = db.query(ExtractionLearningPattern).filter(
        and_(
            ExtractionLearningPattern.account_code == account_code,
            ExtractionLearningPattern.document_type == document_type,
            ExtractionLearningPattern.property_id == property_id
        )
    ).first()

    if existing_pattern:
        # Update existing pattern
        old_total = existing_pattern.total_occurrences
        existing_pattern.total_occurrences = int(count)
        existing_pattern.avg_confidence = float(avg_confidence)
        existing_pattern.min_confidence_seen = float(min_conf)
        existing_pattern.max_confidence_seen = float(max_conf)
        existing_pattern.last_updated_at = datetime.now()

        # Recalculate reliability (assume all are successful if high confidence)
        if float(avg_confidence) >= 90.0:
            existing_pattern.reliability_score = 0.95
            existing_pattern.is_trustworthy = True
        elif float(avg_confidence) >= 85.0:
            existing_pattern.reliability_score = 0.85
            existing_pattern.is_trustworthy = int(count) >= 20  # Need more samples for mid-confidence
        else:
            existing_pattern.reliability_score = 0.75
            existing_pattern.is_trustworthy = False

        logger.debug(f"📝 Updated pattern: {account_code} ({old_total} → {count} occurrences)")
        return 'updated'
    else:
        # Create new pattern
        new_pattern = ExtractionLearningPattern(
            account_code=account_code,
            account_name=account_name,
            document_type=document_type,
            property_id=property_id,
            total_occurrences=int(count),
            approved_count=int(count),  # Assume all successful if high confidence
            rejected_count=0,
            auto_approved_count=0,
            min_confidence_seen=float(min_conf),
            max_confidence_seen=float(max_conf),
            avg_confidence=float(avg_confidence),
            learned_confidence_threshold=float(avg_confidence) - 5.0,  # Set threshold 5% below average
            auto_approve_threshold=float(avg_confidence) if float(avg_confidence) >= 90.0 else None,
            pattern_strength=min(1.0, float(count) / 50.0),  # Stronger with more occurrences
            reliability_score=0.95 if float(avg_confidence) >= 90.0 else 0.85 if float(avg_confidence) >= 85.0 else 0.75,
            is_trustworthy=(float(avg_confidence) >= 90.0 and int(count) >= 10) or (float(avg_confidence) >= 85.0 and int(count) >= 20),
            first_seen_at=datetime.now(),
            last_updated_at=datetime.now(),
            notes=f"Auto-discovered from {count} successful extractions (avg confidence: {avg_confidence:.1f}%)"
        )
        db.add(new_pattern)
        logger.debug(f"✨ Created new pattern: {account_code} ({count} occurrences, avg conf: {avg_confidence:.1f}%)")
        return 'created'


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

