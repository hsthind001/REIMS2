# Phase 1: Foundation & Infrastructure

**Duration**: Weeks 1-3
**Status**: Ready for Implementation
**Dependencies**: PostgreSQL 14+, Redis, Celery, Python 3.11+

---

## Table of Contents

1. [Overview](#overview)
2. [Dependencies Installation](#dependencies-installation)
3. [Task 1.1: Database Schema Enhancements](#task-11-database-schema-enhancements)
4. [Task 1.2: Batch Reprocessing System](#task-12-batch-reprocessing-system)
5. [Task 1.3: PyOD 2.0 Integration](#task-13-pyod-20-integration)
6. [Task 1.4: Model Caching Service](#task-14-model-caching-service)
7. [Task 1.5: Feature Flags Module](#task-15-feature-flags-module)
8. [Testing Requirements](#testing-requirements)
9. [Validation Checklist](#validation-checklist)

---

## Overview

Phase 1 establishes the foundation for all subsequent enhancements. This phase creates:

- **7 new database tables** for explanations, model caching, benchmarks, batch jobs, coordinates
- **Batch reprocessing system** to reprocess documents on-demand
- **PyOD 2.0 integration** with 45+ anomaly detection algorithms
- **Model caching** for 50x performance improvement
- **Feature flags** for gradual rollout

### Success Criteria

- ✅ All 7 tables created and migrated successfully
- ✅ Batch reprocessing API accepts and queues jobs
- ✅ PyOD detector trains and caches models
- ✅ Model cache achieves >50% hit rate in tests
- ✅ Feature flags control all new features

---

## Dependencies Installation

### Step 1: Update requirements.txt

**File**: `backend/requirements.txt`

Add these dependencies at the end of the file:

```txt
# ============================================================================
# ANOMALY DETECTION ENHANCEMENT - PHASE 1
# ============================================================================

# PyOD & ML Libraries
pyod==2.0.0  # Note: If 2.0.0 not released, use pyod>=1.1.0 and plan to upgrade
dtaianomaly==1.0.0
llama-index==0.9.48  # For LLM-powered model selection (optional)

# Data Science & ML Utilities
scipy>=1.11.0  # Statistical functions, required by PyOD
joblib>=1.3.0  # Model serialization (already present, ensure version)
tqdm>=4.66.0  # Progress bars for batch operations

# Optional: OpenAI for LLM model selection
# openai>=1.0.0  # Uncomment if using LLM-powered model selection
```

### Step 2: Install Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python -c "import pyod; print(f'PyOD version: {pyod.__version__}')"
python -c "import dtaianomaly; print('dtaianomaly installed successfully')"
python -c "import joblib; print(f'joblib version: {joblib.__version__}')"
```

Expected output:
```
PyOD version: 1.1.0 (or 2.0.0 if available)
dtaianomaly installed successfully
joblib version: 1.3.2
```

---

## Task 1.1: Database Schema Enhancements

### Overview

Create 7 new tables and update 1 existing table to support the enhanced anomaly detection system.

### Migration File

**Path**: `backend/alembic/versions/20251221_world_class_anomaly_system.py`

**Create this file with the following content**:

```python
"""World-class anomaly detection system

Revision ID: 20251221_0000
Revises: <PREVIOUS_MIGRATION_ID>
Create Date: 2025-12-21 00:00:00.000000

Creates 7 new tables for enhanced anomaly detection:
1. anomaly_explanations - XAI explanations (SHAP, LIME, root causes, actions)
2. anomaly_model_cache - Serialized trained models with metadata
3. cross_property_benchmarks - Portfolio statistical benchmarks
4. batch_reprocessing_jobs - Batch job tracking
5. pdf_field_coordinates - Dedicated coordinate storage
6. pyod_model_selection_log - LLM model selection reasoning
7. Updates anomaly_feedback - Enhanced with new columns
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251221_0000'
down_revision = None  # TODO: Set this to the last migration ID
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # TABLE 1: anomaly_explanations
    # ========================================================================
    op.create_table(
        'anomaly_explanations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anomaly_detection_id', sa.Integer(), nullable=False),

        # Root Cause Analysis
        sa.Column('root_cause_type', sa.String(length=50), nullable=False),
        sa.Column('root_cause_description', sa.Text(), nullable=False),
        sa.Column('contributing_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # SHAP Values (Global Feature Importance)
        sa.Column('shap_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('shap_base_value', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('shap_feature_importance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # LIME Explanation (Local Interpretable)
        sa.Column('lime_explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('lime_intercept', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('lime_score', sa.Numeric(precision=5, scale=4), nullable=True),

        # Suggested Actions
        sa.Column('suggested_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('action_category', sa.String(length=50), nullable=True),

        # Metadata
        sa.Column('explanation_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('explanation_method', sa.String(length=20), nullable=True),
        sa.Column('computation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['anomaly_detection_id'], ['anomaly_detections.id'], ondelete='CASCADE')
    )
    op.create_index('idx_anomaly_explanation_detection', 'anomaly_explanations', ['anomaly_detection_id'])
    op.create_index('idx_root_cause_type', 'anomaly_explanations', ['root_cause_type'])

    # ========================================================================
    # TABLE 2: anomaly_model_cache
    # ========================================================================
    op.create_table(
        'anomaly_model_cache',
        sa.Column('id', sa.Integer(), nullable=False),

        # Model Identification
        sa.Column('model_key', sa.String(length=255), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('account_code', sa.String(length=50), nullable=True),
        sa.Column('model_type', sa.String(length=50), nullable=False),

        # Model Storage
        sa.Column('model_binary', sa.LargeBinary(), nullable=True),
        sa.Column('model_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),

        # Performance Metrics
        sa.Column('training_accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('validation_accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('precision_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('recall_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=5, scale=4), nullable=True),

        # Training Info
        sa.Column('training_data_size', sa.Integer(), nullable=True),
        sa.Column('training_date_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trained_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),

        # Cache Management
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_key'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )
    op.create_index('idx_model_cache_key', 'anomaly_model_cache', ['model_key'])
    op.create_index('idx_model_cache_property', 'anomaly_model_cache', ['property_id'])
    op.create_index('idx_model_cache_type', 'anomaly_model_cache', ['model_type'])
    op.create_index('idx_model_cache_active', 'anomaly_model_cache', ['is_active', 'expires_at'])

    # ========================================================================
    # TABLE 3: cross_property_benchmarks
    # ========================================================================
    op.create_table(
        'cross_property_benchmarks',
        sa.Column('id', sa.Integer(), nullable=False),

        # Benchmark Identification
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('benchmark_period', sa.Date(), nullable=False),
        sa.Column('property_group', sa.String(length=50), nullable=True),

        # Statistical Benchmarks
        sa.Column('portfolio_mean', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('portfolio_median', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('portfolio_std', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('percentile_25', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('percentile_75', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('percentile_90', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('percentile_95', sa.Numeric(precision=15, scale=2), nullable=True),

        # Sample Info
        sa.Column('property_count', sa.Integer(), nullable=False),
        sa.Column('property_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Metadata
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_code', 'benchmark_period', 'property_group', name='uq_benchmark_account_period_group')
    )
    op.create_index('idx_benchmark_account', 'cross_property_benchmarks', ['account_code'])
    op.create_index('idx_benchmark_period', 'cross_property_benchmarks', ['benchmark_period'])
    op.create_index('idx_benchmark_group', 'cross_property_benchmarks', ['property_group'])

    # ========================================================================
    # TABLE 4: batch_reprocessing_jobs
    # ========================================================================
    op.create_table(
        'batch_reprocessing_jobs',
        sa.Column('id', sa.Integer(), nullable=False),

        # Job Configuration
        sa.Column('job_name', sa.String(length=255), nullable=True),
        sa.Column('initiated_by', sa.Integer(), nullable=True),

        # Filters
        sa.Column('property_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('date_range_start', sa.Date(), nullable=True),
        sa.Column('date_range_end', sa.Date(), nullable=True),
        sa.Column('document_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extraction_status_filter', sa.String(length=50), nullable=True),

        # Job Status
        sa.Column('status', sa.String(length=50), server_default='queued', nullable=False),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),

        # Progress Tracking
        sa.Column('total_documents', sa.Integer(), server_default='0', nullable=False),
        sa.Column('processed_documents', sa.Integer(), server_default='0', nullable=False),
        sa.Column('successful_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('skipped_count', sa.Integer(), server_default='0', nullable=False),

        # Results
        sa.Column('results_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_completion_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('idx_batch_job_status', 'batch_reprocessing_jobs', ['status'])
    op.create_index('idx_batch_job_user', 'batch_reprocessing_jobs', ['initiated_by'])
    op.create_index('idx_batch_job_created', 'batch_reprocessing_jobs', ['created_at'])

    # ========================================================================
    # TABLE 5: pdf_field_coordinates
    # ========================================================================
    op.create_table(
        'pdf_field_coordinates',
        sa.Column('id', sa.Integer(), nullable=False),

        # Document & Field Reference
        sa.Column('document_upload_id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=50), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('column_type', sa.String(length=20), nullable=True),

        # Coordinate Information
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('x0', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('y0', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('x1', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('y1', sa.Numeric(precision=10, scale=4), nullable=False),

        # Extraction Method
        sa.Column('extraction_method', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),

        # Matched Text
        sa.Column('matched_text', sa.String(length=500), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_upload_id'], ['document_uploads.id'], ondelete='CASCADE')
    )
    op.create_index('idx_pdf_coords_document', 'pdf_field_coordinates', ['document_upload_id'])
    op.create_index('idx_pdf_coords_field', 'pdf_field_coordinates', ['table_name', 'field_name'])
    op.create_index('idx_pdf_coords_record', 'pdf_field_coordinates', ['table_name', 'record_id'])
    op.create_index('idx_pdf_coords_page', 'pdf_field_coordinates', ['page_number'])

    # ========================================================================
    # TABLE 6: pyod_model_selection_log
    # ========================================================================
    op.create_table(
        'pyod_model_selection_log',
        sa.Column('id', sa.Integer(), nullable=False),

        # Selection Context
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('account_code', sa.String(length=50), nullable=True),
        sa.Column('data_characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # LLM Selection
        sa.Column('llm_recommended_models', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_model', sa.String(length=50), nullable=True),
        sa.Column('selection_reasoning', sa.Text(), nullable=True),

        # Model Performance
        sa.Column('cross_validation_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('actual_precision', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('actual_recall', sa.Numeric(precision=5, scale=4), nullable=True),

        # Metadata
        sa.Column('selected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )
    op.create_index('idx_pyod_selection_property', 'pyod_model_selection_log', ['property_id'])
    op.create_index('idx_pyod_selection_account', 'pyod_model_selection_log', ['account_code'])
    op.create_index('idx_pyod_selection_model', 'pyod_model_selection_log', ['selected_model'])

    # ========================================================================
    # TABLE 7: Update anomaly_feedback (add new columns)
    # ========================================================================
    op.add_column('anomaly_feedback', sa.Column('feedback_confidence', sa.Numeric(precision=5, scale=4), server_default='1.0', nullable=True))
    op.add_column('anomaly_feedback', sa.Column('business_context', sa.Text(), nullable=True))
    op.add_column('anomaly_feedback', sa.Column('learned_applied', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('anomaly_feedback', sa.Column('similar_anomalies_suppressed', sa.Integer(), server_default='0', nullable=True))


def downgrade():
    # Drop in reverse order
    op.drop_column('anomaly_feedback', 'similar_anomalies_suppressed')
    op.drop_column('anomaly_feedback', 'learned_applied')
    op.drop_column('anomaly_feedback', 'business_context')
    op.drop_column('anomaly_feedback', 'feedback_confidence')

    op.drop_index('idx_pyod_selection_model', table_name='pyod_model_selection_log')
    op.drop_index('idx_pyod_selection_account', table_name='pyod_model_selection_log')
    op.drop_index('idx_pyod_selection_property', table_name='pyod_model_selection_log')
    op.drop_table('pyod_model_selection_log')

    op.drop_index('idx_pdf_coords_page', table_name='pdf_field_coordinates')
    op.drop_index('idx_pdf_coords_record', table_name='pdf_field_coordinates')
    op.drop_index('idx_pdf_coords_field', table_name='pdf_field_coordinates')
    op.drop_index('idx_pdf_coords_document', table_name='pdf_field_coordinates')
    op.drop_table('pdf_field_coordinates')

    op.drop_index('idx_batch_job_created', table_name='batch_reprocessing_jobs')
    op.drop_index('idx_batch_job_user', table_name='batch_reprocessing_jobs')
    op.drop_index('idx_batch_job_status', table_name='batch_reprocessing_jobs')
    op.drop_table('batch_reprocessing_jobs')

    op.drop_index('idx_benchmark_group', table_name='cross_property_benchmarks')
    op.drop_index('idx_benchmark_period', table_name='cross_property_benchmarks')
    op.drop_index('idx_benchmark_account', table_name='cross_property_benchmarks')
    op.drop_table('cross_property_benchmarks')

    op.drop_index('idx_model_cache_active', table_name='anomaly_model_cache')
    op.drop_index('idx_model_cache_type', table_name='anomaly_model_cache')
    op.drop_index('idx_model_cache_property', table_name='anomaly_model_cache')
    op.drop_index('idx_model_cache_key', table_name='anomaly_model_cache')
    op.drop_table('anomaly_model_cache')

    op.drop_index('idx_root_cause_type', table_name='anomaly_explanations')
    op.drop_index('idx_anomaly_explanation_detection', table_name='anomaly_explanations')
    op.drop_table('anomaly_explanations')
```

### Running the Migration

```bash
cd backend

# Update the migration file's down_revision
# Open the file and set: down_revision = '<LAST_MIGRATION_ID>'
# Find last migration ID: alembic current

# Run migration
alembic upgrade head

# Verify tables created
psql -U reims_user -d reims_db -c "\dt anomaly*"
psql -U reims_user -d reims_db -c "\dt batch_reprocessing_jobs"
psql -U reims_user -d reims_db -c "\dt cross_property_benchmarks"
psql -U reims_user -d reims_db -c "\dt pdf_field_coordinates"
psql -U reims_user -d reims_db -c "\dt pyod_model_selection_log"
```

Expected output: All 7 tables listed

### Creating SQLAlchemy Models

**Create new model files** (Cursor should create these automatically, but here are references):

1. **`backend/app/models/anomaly_explanation.py`**
2. **`backend/app/models/anomaly_model_cache.py`**
3. **`backend/app/models/cross_property_benchmark.py`**
4. **`backend/app/models/batch_reprocessing_job.py`**
5. **`backend/app/models/pdf_field_coordinate.py`**
6. **`backend/app/models/pyod_model_selection_log.py`**

These models should mirror the table schemas exactly. See existing models like `anomaly_detection.py` for reference.

---

## Task 1.2: Batch Reprocessing System

### Overview

Create a system to batch reprocess documents for anomaly detection with filtering, progress tracking, and async execution.

### Components

1. **Service**: `batch_reprocessing_service.py` - Business logic
2. **Task**: `batch_reprocessing_tasks.py` - Celery async task
3. **API**: `batch_reprocessing.py` - REST endpoints
4. **Models**: Pydantic request/response models

---

### File 1: Service

**Path**: `backend/app/services/batch_reprocessing_service.py`

```python
"""
Batch Reprocessing Service

Handles batch reprocessing of documents for anomaly detection.
Allows filtering by property, date range, document type, and extraction status.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.tasks.batch_reprocessing_tasks import reprocess_documents_batch

logger = logging.getLogger(__name__)


class BatchReprocessingService:
    """Service for managing batch reprocessing jobs."""

    def __init__(self, db: Session):
        self.db = db

    def create_batch_job(
        self,
        user_id: int,
        property_ids: Optional[List[int]] = None,
        date_range_start: Optional[date] = None,
        date_range_end: Optional[date] = None,
        document_types: Optional[List[str]] = None,
        extraction_status_filter: str = 'all',
        job_name: Optional[str] = None
    ) -> BatchReprocessingJob:
        """
        Create a new batch reprocessing job.

        Args:
            user_id: User initiating the job
            property_ids: Optional list of property IDs to reprocess
            date_range_start: Optional start date filter
            date_range_end: Optional end date filter
            document_types: Optional list of document types (balance_sheet, income_statement, etc.)
            extraction_status_filter: Filter by extraction status (all, completed, failed)
            job_name: Optional human-readable job name

        Returns:
            Created batch job instance
        """
        # Validate property_ids exist
        if property_ids:
            valid_properties = self.db.query(Property.id).filter(Property.id.in_(property_ids)).all()
            valid_property_ids = [p.id for p in valid_properties]
            if len(valid_property_ids) != len(property_ids):
                invalid_ids = set(property_ids) - set(valid_property_ids)
                logger.warning(f"Invalid property IDs: {invalid_ids}")

        # Query documents matching filters
        query = self.db.query(DocumentUpload)

        # Apply filters
        filters = []
        if property_ids:
            filters.append(DocumentUpload.property_id.in_(property_ids))

        if date_range_start:
            filters.append(DocumentUpload.upload_date >= date_range_start)

        if date_range_end:
            filters.append(DocumentUpload.upload_date <= date_range_end)

        if document_types:
            filters.append(DocumentUpload.document_type.in_(document_types))

        if extraction_status_filter != 'all':
            filters.append(DocumentUpload.extraction_status == extraction_status_filter)

        if filters:
            query = query.filter(and_(*filters))

        # Count total documents
        total_documents = query.count()

        # Create job name if not provided
        if not job_name:
            property_names = "all properties" if not property_ids else f"{len(property_ids)} properties"
            job_name = f"Reprocess {total_documents} documents for {property_names}"

        # Create batch job record
        batch_job = BatchReprocessingJob(
            job_name=job_name,
            initiated_by=user_id,
            property_ids=property_ids,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            document_types=document_types,
            extraction_status_filter=extraction_status_filter,
            status='queued',
            total_documents=total_documents,
            processed_documents=0,
            successful_count=0,
            failed_count=0,
            skipped_count=0
        )

        self.db.add(batch_job)
        self.db.commit()
        self.db.refresh(batch_job)

        logger.info(f"Created batch reprocessing job {batch_job.id} with {total_documents} documents")

        return batch_job

    def start_batch_job(self, job_id: int) -> Dict[str, Any]:
        """
        Start a batch reprocessing job asynchronously.

        Args:
            job_id: Batch job ID to start

        Returns:
            Job info with Celery task ID
        """
        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        if job.status != 'queued':
            raise ValueError(f"Batch job {job_id} is not in 'queued' status (current: {job.status})")

        # Queue Celery task
        task = reprocess_documents_batch.delay(job_id)

        # Update job with task ID
        job.celery_task_id = task.id
        job.status = 'running'
        job.started_at = datetime.now()
        self.db.commit()

        logger.info(f"Started batch job {job_id} with Celery task {task.id}")

        return {
            "job_id": job.id,
            "task_id": task.id,
            "status": job.status,
            "total_documents": job.total_documents
        }

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get current status of batch job.

        Args:
            job_id: Batch job ID

        Returns:
            Job status information
        """
        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        # Calculate progress percentage
        progress_pct = 0
        if job.total_documents > 0:
            progress_pct = int((job.processed_documents / job.total_documents) * 100)

        # Calculate ETA
        eta = None
        if job.started_at and job.processed_documents > 0:
            elapsed = (datetime.now() - job.started_at).total_seconds()
            docs_per_second = job.processed_documents / elapsed
            remaining_docs = job.total_documents - job.processed_documents
            if docs_per_second > 0:
                eta_seconds = remaining_docs / docs_per_second
                eta = datetime.now() + timedelta(seconds=eta_seconds)

        return {
            "job_id": job.id,
            "job_name": job.job_name,
            "status": job.status,
            "progress_pct": progress_pct,
            "total_documents": job.total_documents,
            "processed_documents": job.processed_documents,
            "successful_count": job.successful_count,
            "failed_count": job.failed_count,
            "skipped_count": job.skipped_count,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "estimated_completion_at": eta,
            "celery_task_id": job.celery_task_id,
            "results_summary": job.results_summary
        }

    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel a running batch job.

        Args:
            job_id: Batch job ID to cancel

        Returns:
            True if cancelled successfully
        """
        from app.core.celery_app import celery_app

        job = self.db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()

        if not job:
            raise ValueError(f"Batch job {job_id} not found")

        if job.status not in ['queued', 'running']:
            raise ValueError(f"Cannot cancel job in status: {job.status}")

        # Revoke Celery task if running
        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        # Update job status
        job.status = 'cancelled'
        job.completed_at = datetime.now()
        self.db.commit()

        logger.info(f"Cancelled batch job {job_id}")

        return True

    def list_jobs(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[BatchReprocessingJob]:
        """
        List batch jobs with optional filters.

        Args:
            user_id: Filter by user
            status: Filter by status
            limit: Maximum number of jobs to return

        Returns:
            List of batch jobs
        """
        query = self.db.query(BatchReprocessingJob)

        if user_id:
            query = query.filter(BatchReprocessingJob.initiated_by == user_id)

        if status:
            query = query.filter(BatchReprocessingJob.status == status)

        query = query.order_by(BatchReprocessingJob.created_at.desc()).limit(limit)

        return query.all()
```

**Continue to next file...**

---

Due to length constraints, I'll continue creating the remaining implementation documents. Let me mark Phase 1 as in progress and continue.

