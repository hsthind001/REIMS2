"""
Forensic Audit Background Tasks

Celery tasks for running complete 7-phase forensic audits in the background.
Prevents UI blocking during long-running audits (2-5 minutes).
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime
from celery import Task
from sqlalchemy.orm import Session
import logging

# Import Celery app
from app.core.celery_config import celery_app

from app.db.database import SessionLocal
from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
from app.services.fraud_detection_service import FraudDetectionService
from app.services.covenant_compliance_service import CovenantComplianceService
from app.services.audit_scorecard_generator_service import AuditScorecardGeneratorService
from app.services.forensic_audit_anomaly_integration_service import ForensicAuditAnomalyIntegrationService
from app.services.tenant_risk_analysis_service import TenantRiskAnalysisService
from app.services.collections_revenue_quality_service import CollectionsRevenueQualityService
from app.models.document_upload import DocumentUpload
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.services.validation_service import ValidationService
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from datetime import timedelta


class AsyncSessionWrapper:
    """
    Async-style wrapper for sync SQLAlchemy sessions.

    Forensic audit services expect AsyncSession methods, but the app uses
    sync sessions. This wrapper provides async-compatible methods while
    delegating to the underlying sync session.
    """

    def __init__(self, session: Session):
        self._session = session

    def __getattr__(self, name: str):
        return getattr(self._session, name)

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        return self._session.commit()

    async def flush(self):
        return self._session.flush()

    async def refresh(self, *args, **kwargs):
        return self._session.refresh(*args, **kwargs)

    async def close(self):
        return self._session.close()

    def add(self, *args, **kwargs):
        return self._session.add(*args, **kwargs)

    def add_all(self, *args, **kwargs):
        return self._session.add_all(*args, **kwargs)

    def rollback(self):
        return self._session.rollback()


logger = logging.getLogger(__name__)


def normalize_id(value: Union[str, int]) -> Union[str, int]:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


@celery_app.task(bind=True, name="forensic_audit.run_complete_audit")
def run_complete_forensic_audit_task(
    self: Task,
    property_id: Union[str, int],
    period_id: Union[str, int],
    document_id: Optional[int] = None,
    options: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """
    Run complete 7-phase forensic audit in background.

    This task executes all audit phases and updates progress:
    - Phase 1: Document Completeness (10% progress)
    - Phase 2: Mathematical Integrity (20% progress)
    - Phase 3: Cross-Document Reconciliation (40% progress)
    - Phase 4: Tenant Risk Analysis (55% progress)
    - Phase 5: Collections & Revenue Quality (70% progress)
    - Phase 6: Fraud Detection (85% progress)
    - Phase 7: Covenant Compliance (95% progress)
    - Phase 8: Generate Scorecard (100% progress)

    Args:
        self: Celery task instance (auto-bound)
        property_id: Property UUID (as string)
        period_id: Financial period UUID (as string)
        document_id: Document upload ID for anomaly linking
        options: Optional settings (refresh_views, run_fraud_detection, etc.)

    Returns:
        Complete audit results with scorecard
    """

    # Parse options
    if options is None:
        options = {
            'refresh_views': True,
            'run_fraud_detection': True,
            'run_covenant_analysis': True,
            'create_anomalies': document_id is not None
        }
    elif document_id is None:
        options['create_anomalies'] = False

    property_ref = normalize_id(property_id)
    period_ref = normalize_id(period_id)

    # Create database session
    sync_db = SessionLocal()
    db = AsyncSessionWrapper(sync_db)

    try:
        # Update state: STARTED
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Initializing',
                'phase_number': 0,
                'progress': 0,
                'message': 'Starting forensic audit...'
            }
        )

        audit_results = {
            'property_id': property_ref,
            'period_id': period_ref,
            'started_at': datetime.now().isoformat(),
            'phases': {}
        }

        # =====================================================================
        # PHASE 1: Document Completeness Check (10% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Document Completeness',
                'phase_number': 1,
                'progress': 10,
                'message': 'Checking document completeness...'
            }
        )

        required_documents = {
            'balance_sheet': 'Balance Sheet',
            'income_statement': 'Income Statement',
            'cash_flow': 'Cash Flow Statement',
            'rent_roll': 'Rent Roll',
            'mortgage_statement': 'Mortgage Statement'
        }
        missing_documents = []
        present_count = 0

        for document_type, label in required_documents.items():
            exists = sync_db.query(DocumentUpload.id).filter(
                DocumentUpload.property_id == property_ref,
                DocumentUpload.period_id == period_ref,
                DocumentUpload.document_type == document_type,
                DocumentUpload.is_active.is_(True)
            ).first()
            if exists:
                present_count += 1
            else:
                missing_documents.append(label)

        completeness_pct = round((present_count / len(required_documents)) * 100, 2)

        audit_results['phases']['document_completeness'] = {
            'status': 'COMPLETE' if completeness_pct == 100.0 else 'INCOMPLETE',
            'completeness_pct': completeness_pct,
            'missing_documents': missing_documents
        }

        # =====================================================================
        # PHASE 2: Mathematical Integrity Testing (20% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Mathematical Integrity',
                'phase_number': 2,
                'progress': 20,
                'message': 'Testing mathematical integrity (balance sheet equation, etc.)...'
            }
        )

        validation_service = ValidationService(sync_db)
        rule_types = ['balance_check', 'calculation_check']
        document_types = [
            'balance_sheet',
            'income_statement',
            'cash_flow',
            'rent_roll',
            'mortgage_statement'
        ]

        math_total = 0
        math_passed = 0
        math_failed = 0
        math_warnings = 0
        math_errors = 0

        for document_type in document_types:
            upload = sync_db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property_ref,
                DocumentUpload.period_id == period_ref,
                DocumentUpload.document_type == document_type,
                DocumentUpload.is_active.is_(True)
            ).order_by(
                DocumentUpload.upload_date.desc().nullslast(),
                DocumentUpload.id.desc()
            ).first()

            if not upload:
                continue

            base_query = sync_db.query(ValidationResult, ValidationRule).join(
                ValidationRule, ValidationRule.id == ValidationResult.rule_id
            ).filter(
                ValidationResult.upload_id == upload.id,
                ValidationRule.document_type == document_type,
                ValidationRule.rule_type.in_(rule_types)
            ).order_by(ValidationResult.created_at.desc())

            results = base_query.all()
            if not results:
                validation_service.validate_upload(upload.id)
                results = base_query.all()

            seen_rules = set()
            for result, rule in results:
                if rule.id in seen_rules:
                    continue
                seen_rules.add(rule.id)
                math_total += 1
                if result.passed:
                    math_passed += 1
                else:
                    math_failed += 1
                    if result.severity == 'warning':
                        math_warnings += 1
                    elif result.severity == 'error':
                        math_errors += 1

        audit_results['phases']['mathematical_integrity'] = {
            'status': 'COMPLETE' if math_total > 0 else 'SKIPPED',
            'tests_passed': math_passed,
            'tests_total': math_total,
            'warnings': math_warnings,
            'errors': math_errors
        }

        # =====================================================================
        # PHASE 3: Cross-Document Reconciliation (40% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Cross-Document Reconciliation',
                'phase_number': 3,
                'progress': 40,
                'message': 'Running 9 cross-document reconciliations...'
            }
        )

        # Run reconciliation service
        recon_service = CrossDocumentReconciliationService(db)
        recon_results = await_async(
            recon_service.run_all_reconciliations(property_ref, period_ref)
        )

        # Save to database
        await_async(
            recon_service.save_reconciliation_results(
                property_ref, period_ref, recon_results
            )
        )

        # Count results
        total_recons = (
            len(recon_results.get('critical', [])) +
            len(recon_results.get('important', [])) +
            len(recon_results.get('informational', []))
        )
        passed_recons = sum(
            1 for recon_list in recon_results.values()
            for recon in recon_list
            if recon.status.value == 'PASS'
        )

        audit_results['phases']['cross_document_reconciliation'] = {
            'status': 'COMPLETE',
            'total_reconciliations': total_recons,
            'passed': passed_recons,
            'pass_rate': round((passed_recons / total_recons * 100), 2) if total_recons > 0 else 0
        }

        # =====================================================================
        # PHASE 4: Tenant Risk Analysis (55% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Tenant Risk Analysis',
                'phase_number': 4,
                'progress': 55,
                'message': 'Analyzing tenant concentration and lease rollover risk...'
            }
        )

        tenant_service = TenantRiskAnalysisService(db)
        tenant_results = await_async(
            tenant_service.run_all_tenant_risk_tests(property_ref, period_ref)
        )

        try:
            await_async(
                tenant_service.save_tenant_risk_results(property_ref, period_ref, tenant_results)
            )
        except Exception as tenant_save_error:
            logger.warning(f"Tenant risk results not saved: {tenant_save_error}")

        audit_results['phases']['tenant_risk_analysis'] = {
            'status': 'COMPLETE',
            'concentration_risk': tenant_results['concentration_risk_status'],
            'rollover_risk': tenant_results['rollover_risk_status']
        }

        # =====================================================================
        # PHASE 5: Collections & Revenue Quality (70% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Collections & Revenue Quality',
                'phase_number': 5,
                'progress': 70,
                'message': 'Calculating DSO and revenue quality score...'
            }
        )

        collections_service = CollectionsRevenueQualityService(db)
        collections_results = await_async(
            collections_service.run_all_collections_tests(property_ref, period_ref)
        )

        try:
            await_async(
                collections_service.save_collections_results(property_ref, period_ref, collections_results)
            )
        except Exception as collections_save_error:
            logger.warning(f"Collections results not saved: {collections_save_error}")

        audit_results['phases']['collections_quality'] = {
            'status': 'COMPLETE',
            'dso': collections_results['summary']['dso_days'],
            'revenue_quality_score': collections_results['summary']['quality_score'],
            'overall_status': collections_results['overall_status']
        }

        # =====================================================================
        # PHASE 6: Fraud Detection (85% progress)
        # =====================================================================
        if options.get('run_fraud_detection', True):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_phase': 'Fraud Detection',
                    'phase_number': 6,
                    'progress': 85,
                    'message': 'Running fraud detection tests (Benford\'s Law, round numbers, etc.)...'
                }
            )

            # Run fraud detection service
            fraud_service = FraudDetectionService(db)
            fraud_results = await_async(
            fraud_service.run_all_fraud_tests(property_ref, period_ref)
        )

            # Save to database
            await_async(
            fraud_service.save_fraud_detection_results(
                property_ref, period_ref, fraud_results
            )
        )

            audit_results['phases']['fraud_detection'] = {
                'status': 'COMPLETE',
                'overall_risk_level': fraud_results['overall_fraud_risk_level'],
                'red_flags_found': fraud_results['red_flags_found']
            }
        else:
            audit_results['phases']['fraud_detection'] = {
                'status': 'SKIPPED'
            }

        # =====================================================================
        # PHASE 7: Covenant Compliance (95% progress)
        # =====================================================================
        if options.get('run_covenant_analysis', True):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_phase': 'Covenant Compliance',
                    'phase_number': 7,
                    'progress': 95,
                    'message': 'Monitoring DSCR, LTV, and lender covenants...'
                }
            )

            # Run covenant compliance service
            covenant_service = CovenantComplianceService(db)
            covenant_results = await_async(
            covenant_service.calculate_all_covenants(property_ref, period_ref)
        )

            # Save to database
            await_async(
            covenant_service.save_covenant_compliance_results(
                property_ref, period_ref, covenant_results
            )
        )

            audit_results['phases']['covenant_compliance'] = {
                'status': 'COMPLETE',
                'overall_compliance_status': covenant_results['overall_compliance_status'],
                'covenant_breaches': covenant_results['covenant_breaches']
            }
        else:
            audit_results['phases']['covenant_compliance'] = {
                'status': 'SKIPPED'
            }

        # =====================================================================
        # PHASE 8: Generate Audit Scorecard (100% progress)
        # =====================================================================
        self.update_state(
            state='PROGRESS',
            meta={
                'current_phase': 'Generating Scorecard',
                'phase_number': 8,
                'progress': 98,
                'message': 'Generating executive audit scorecard...'
            }
        )

        # Generate scorecard
        scorecard_service = AuditScorecardGeneratorService(db)
        scorecard = await_async(
            scorecard_service.generate_complete_scorecard(property_ref, period_ref)
        )

        audit_results['scorecard'] = scorecard

        # =====================================================================
        # PHASE 9: Create Anomaly Records (if enabled)
        # =====================================================================
        if options.get('create_anomalies', True) and document_id is not None:
            self.update_state(
                state='PROGRESS',
                meta={
                    'current_phase': 'Creating Anomaly Records',
                    'phase_number': 9,
                    'progress': 99,
                    'message': 'Converting findings to anomaly records...'
                }
            )

            # Run anomaly integration
            integration_service = ForensicAuditAnomalyIntegrationService(db)
            anomaly_results = await_async(
                integration_service.run_complete_integration(
                    property_ref, period_ref, document_id
                )
            )

            audit_results['anomaly_integration'] = anomaly_results
        elif options.get('create_anomalies', True):
            audit_results['anomaly_integration'] = {
                'status': 'SKIPPED',
                'reason': 'No document_id provided for anomaly linkage'
            }

        # =====================================================================
        # COMPLETE
        # =====================================================================
        audit_results['completed_at'] = datetime.now().isoformat()
        audit_results['duration_seconds'] = (
            datetime.fromisoformat(audit_results['completed_at']) -
            datetime.fromisoformat(audit_results['started_at'])
        ).total_seconds()

        self.update_state(
            state='SUCCESS',
            meta={
                'current_phase': 'Complete',
                'phase_number': 9,
                'progress': 100,
                'message': 'Forensic audit completed successfully',
                'results': audit_results
            }
        )

        return audit_results

    except Exception as e:
        # Log the full traceback so we can see what went wrong
        logger.exception(f"Forensic audit failed: {str(e)}")
        # Raise the exception so Celery marks the task as FAILURE automatically
        # Do NOT manually update_state to FAILURE here as it conflicts with the raise
        raise e

    finally:
        sync_db.close()


# Helper function to run async functions in sync context
def await_async(coroutine):
    """
    Run async coroutine in synchronous Celery task context.

    This is a workaround since Celery tasks are synchronous but our
    services use async/await.
    """
    import asyncio

    # Try to get existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new loop if existing one is running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop in current thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coroutine)
    finally:
        # Don't close the loop if we created a new one
        pass


@celery_app.task(name="forensic_audit.get_task_status")
def get_audit_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a running or completed audit task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status with progress information
    """
    from celery.result import AsyncResult

    task = AsyncResult(task_id, app=celery_app)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current_phase': 'Waiting',
            'progress': 0,
            'message': 'Task is queued and waiting to start'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'current_phase': task.info.get('current_phase', 'Unknown'),
            'phase_number': task.info.get('phase_number', 0),
            'progress': task.info.get('progress', 0),
            'message': task.info.get('message', 'Processing...')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'current_phase': 'Complete',
            'progress': 100,
            'message': 'Audit completed successfully',
            'results': task.info.get('results', {})
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'current_phase': 'Error',
            'progress': 0,
            'message': task.info.get('message', 'Audit failed'),
            'error': str(task.info) if task.info else 'Unknown error'
        }
    else:
        response = {
            'state': task.state,
            'current_phase': 'Unknown',
            'progress': 0,
            'message': f'Task in state: {task.state}'
        }

    return response


@celery_app.task(name="forensic_audit.schedule_recurring_audits")
def schedule_recurring_audits():
    """
    Scheduled task to run audits for all properties on period close.

    This can be configured to run:
    - Daily at end of day
    - Monthly on period close
    - On-demand via API

    Returns:
        Summary of audits scheduled
    """
    from app.models.property import Property
    from app.models.financial_period import FinancialPeriod

    db = SessionLocal()

    try:
        # Find all periods that closed recently (e.g. last 7 days) and need audit
        # We look for closed periods where no validation results exist yet (proxy for audit run)
        
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        candidates = db.query(FinancialPeriod).join(Property).filter(
            Property.status == 'active',
            FinancialPeriod.is_closed.is_(True),
            FinancialPeriod.closed_date >= seven_days_ago
        ).all()

        scheduled_count = 0
        
        for period in candidates:
            # Check if any validation results exist for this period (indicating audit ran)
            # We join through DocumentUpload to connect ValidationResult to Period
            audit_exists = db.query(ValidationResult).join(DocumentUpload).filter(
                DocumentUpload.period_id == period.id
            ).first()
            
            if not audit_exists:
                # Schedule the audit
                run_complete_forensic_audit_task.delay(
                    property_id=period.property_id,
                    period_id=period.id,
                    options={'refresh_views': True}
                )
                scheduled_count += 1
                logger.info(f"Scheduled forensic audit for Property {period.property_id}, Period {period.id}")

        return {
            'status': 'success',
            'audits_scheduled': scheduled_count,
            'scheduled_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error scheduling audits: {e}")
        return {
            'status': 'error', 
            'error': str(e),
            'audits_scheduled': 0
        }

    finally:
        db.close()


@celery_app.task(name="forensic_audit.cleanup_old_results")
def cleanup_old_audit_results(days_to_keep: int = 90):
    """
    Clean up old audit results to save database space.

    Keeps audit scorecards and critical findings, but removes
    detailed test results older than specified days.

    Args:
        days_to_keep: Number of days of detailed results to retain

    Returns:
        Summary of cleanup operation
    """
    from datetime import timedelta

    db = SessionLocal()

    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Cleanup Validation Results (detailed logs)
        # Note: We keep high-level scorecards (if table exists) and compliance history primarily
        
        deleted_count = db.query(ValidationResult).filter(
            ValidationResult.created_at < cutoff_date
        ).delete(synchronize_session=False)
        
        # Also clean up other detailed logs if models are available/imported
        # For now, ValidationResult is the bulk of the data
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old validation results older than {cutoff_date}")

        return {
            'status': 'success',
            'records_deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'cleaned_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old results: {e}")
        db.rollback()
        return {
            'status': 'error',
            'error': str(e),
            'records_deleted': 0
        }

    finally:
        db.close()
