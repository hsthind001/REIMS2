"""Create model_performance_metrics table

Revision ID: 20251222_0005
Revises: 20251222_0004
Create Date: 2025-12-22 23:50:00.000000

Creates model_performance_metrics table for tracking ML model performance:
- Detection coverage, runtime, latency metrics
- Alert volumes by severity
- Quality metrics (FPR, TPR, precision, F1 score)
- Additional metrics stored as JSONB
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251222_0005'
down_revision = '20251222_0004'
branch_labels = None
depends_on = None


def upgrade():
    """Create model_performance_metrics table"""
    
    op.create_table(
        'model_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Model identification
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('detector_method', sa.String(100), nullable=True),
        
        # Performance metrics
        sa.Column('detection_coverage', sa.Float(), nullable=True, comment='Percentage of accounts/periods scanned (0-100)'),
        sa.Column('runtime_per_batch_ms', sa.Float(), nullable=True, comment='Average runtime per batch in milliseconds'),
        sa.Column('queue_latency_ms', sa.Float(), nullable=True, comment='Queue latency in milliseconds'),
        
        # Alert metrics
        sa.Column('alert_volume_total', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('alert_volume_critical', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('alert_volume_high', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('alert_volume_medium', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('alert_volume_low', sa.Integer(), nullable=True, server_default='0'),
        
        # Quality metrics
        sa.Column('false_positive_rate', sa.Float(), nullable=True, comment='False positive ratio (0-1)'),
        sa.Column('true_positive_rate', sa.Float(), nullable=True, comment='True positive rate / recall (0-1)'),
        sa.Column('precision', sa.Float(), nullable=True, comment='Precision score (0-1)'),
        sa.Column('f1_score', sa.Float(), nullable=True, comment='F1 score (0-1)'),
        
        # Additional metrics (stored as JSONB for flexibility)
        sa.Column('additional_metrics', postgresql.JSONB(), nullable=True),
        
        # Context
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.String(100), nullable=True),
        
        # Timestamps
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        
        # Check constraints for metric ranges
        sa.CheckConstraint('detection_coverage >= 0 AND detection_coverage <= 100', name='check_detection_coverage_range'),
        sa.CheckConstraint('false_positive_rate >= 0 AND false_positive_rate <= 1', name='check_fpr_range'),
        sa.CheckConstraint('true_positive_rate >= 0 AND true_positive_rate <= 1', name='check_tpr_range'),
        sa.CheckConstraint('precision >= 0 AND precision <= 1', name='check_precision_range'),
        sa.CheckConstraint('f1_score >= 0 AND f1_score <= 1', name='check_f1_score_range'),
    )
    
    # Create indexes for performance
    op.create_index('ix_model_performance_metrics_model_name', 'model_performance_metrics', ['model_name'])
    op.create_index('ix_model_performance_metrics_model_type', 'model_performance_metrics', ['model_type'])
    op.create_index('ix_model_performance_metrics_property_id', 'model_performance_metrics', ['property_id'])
    op.create_index('ix_model_performance_metrics_period_id', 'model_performance_metrics', ['period_id'])
    op.create_index('ix_model_performance_metrics_batch_id', 'model_performance_metrics', ['batch_id'])
    op.create_index('ix_model_performance_metrics_recorded_at', 'model_performance_metrics', ['recorded_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_model_performance_model_type', 'model_performance_metrics', ['model_type', 'recorded_at'])
    op.create_index('idx_model_performance_property_period', 'model_performance_metrics', ['property_id', 'period_id', 'recorded_at'])


def downgrade():
    """Drop model_performance_metrics table"""
    
    # Drop indexes
    op.drop_index('idx_model_performance_property_period', table_name='model_performance_metrics')
    op.drop_index('idx_model_performance_model_type', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_recorded_at', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_batch_id', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_period_id', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_property_id', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_model_type', table_name='model_performance_metrics')
    op.drop_index('ix_model_performance_metrics_model_name', table_name='model_performance_metrics')
    
    # Drop table
    op.drop_table('model_performance_metrics')

