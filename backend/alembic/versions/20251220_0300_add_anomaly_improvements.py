"""add_anomaly_detection_improvements

Revision ID: 20251220_0300
Revises: 20251220_0202_add_alert_history
Create Date: 2025-12-20 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251220_0300'
down_revision = '20251220_0202_add_alert_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if anomaly_detections table exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'anomaly_detections' not in existing_tables:
        print("⚠️  anomaly_detections table does not exist. Skipping anomaly improvements migration.")
        return

    # Add new fields to anomaly_detections table
    op.add_column('anomaly_detections', sa.Column('forecast_method', sa.String(50), nullable=True))
    op.add_column('anomaly_detections', sa.Column('confidence_calibrated', sa.Numeric(5, 4), nullable=True))
    op.add_column('anomaly_detections', sa.Column('detection_window', sa.String(20), nullable=True))  # short_term, medium_term, long_term
    op.add_column('anomaly_detections', sa.Column('windows_detected', sa.Integer(), nullable=True))  # Number of windows that detected this
    op.add_column('anomaly_detections', sa.Column('ensemble_confidence', sa.Numeric(5, 4), nullable=True))
    op.add_column('anomaly_detections', sa.Column('detection_methods', postgresql.ARRAY(sa.String(50)), nullable=True))  # Array of methods used
    op.add_column('anomaly_detections', sa.Column('is_consensus', sa.Boolean(), default=False, nullable=True))
    op.add_column('anomaly_detections', sa.Column('change_point_detected', sa.Boolean(), default=False, nullable=True))
    op.add_column('anomaly_detections', sa.Column('context_suppressed', sa.Boolean(), default=False, nullable=True))
    op.add_column('anomaly_detections', sa.Column('suppression_reason', sa.String(255), nullable=True))
    
    # Create indexes for new fields
    op.create_index('ix_anomaly_forecast_method', 'anomaly_detections', ['forecast_method'])
    op.create_index('ix_anomaly_detection_window', 'anomaly_detections', ['detection_window'])
    op.create_index('ix_anomaly_is_consensus', 'anomaly_detections', ['is_consensus'])
    
    # Create anomaly_feedback table
    op.create_table(
        'anomaly_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anomaly_detection_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('feedback_type', sa.String(20), nullable=False),  # confirmed, dismissed, false_positive, false_negative
        sa.Column('is_anomaly', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('account_code', sa.String(50), nullable=True),
        sa.Column('anomaly_type', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['anomaly_detection_id'],
            ['anomaly_detections.id'],
            name='fk_anomaly_feedback_detection',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_anomaly_feedback_user',
            ondelete='SET NULL'
        )
    )
    
    op.create_index('ix_anomaly_feedback_detection_id', 'anomaly_feedback', ['anomaly_detection_id'])
    op.create_index('ix_anomaly_feedback_user_id', 'anomaly_feedback', ['user_id'])
    op.create_index('ix_anomaly_feedback_account_code', 'anomaly_feedback', ['account_code'])
    op.create_index('ix_anomaly_feedback_type', 'anomaly_feedback', ['feedback_type'])
    
    # Create anomaly_learning_patterns table
    op.create_table(
        'anomaly_learning_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(50), nullable=True),
        sa.Column('anomaly_type', sa.String(50), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), default=0),
        sa.Column('suppression_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('auto_suppress', sa.Boolean(), default=False),
        sa.Column('confidence', sa.Numeric(5, 4), default=0.5),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.Column('last_applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['property_id'],
            ['properties.id'],
            name='fk_anomaly_pattern_property',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='fk_anomaly_pattern_user',
            ondelete='SET NULL'
        )
    )
    
    op.create_index('ix_anomaly_pattern_account_code', 'anomaly_learning_patterns', ['account_code'])
    op.create_index('ix_anomaly_pattern_anomaly_type', 'anomaly_learning_patterns', ['anomaly_type'])
    op.create_index('ix_anomaly_pattern_property_id', 'anomaly_learning_patterns', ['property_id'])
    op.create_index('ix_anomaly_pattern_auto_suppress', 'anomaly_learning_patterns', ['auto_suppress'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('anomaly_learning_patterns')
    op.drop_table('anomaly_feedback')
    
    # Drop indexes
    op.drop_index('ix_anomaly_is_consensus', table_name='anomaly_detections')
    op.drop_index('ix_anomaly_detection_window', table_name='anomaly_detections')
    op.drop_index('ix_anomaly_forecast_method', table_name='anomaly_detections')
    
    # Drop columns from anomaly_detections
    op.drop_column('anomaly_detections', 'suppression_reason')
    op.drop_column('anomaly_detections', 'context_suppressed')
    op.drop_column('anomaly_detections', 'change_point_detected')
    op.drop_column('anomaly_detections', 'is_consensus')
    op.drop_column('anomaly_detections', 'detection_methods')
    op.drop_column('anomaly_detections', 'ensemble_confidence')
    op.drop_column('anomaly_detections', 'windows_detected')
    op.drop_column('anomaly_detections', 'detection_window')
    op.drop_column('anomaly_detections', 'confidence_calibrated')
    op.drop_column('anomaly_detections', 'forecast_method')

