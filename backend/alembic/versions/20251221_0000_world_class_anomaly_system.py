"""World-class anomaly detection system

Revision ID: 20251221_0000
Revises: 20251220_0300
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
down_revision = '20251220_0300'
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
