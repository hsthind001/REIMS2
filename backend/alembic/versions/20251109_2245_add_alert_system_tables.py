"""add alert system tables

Revision ID: 20251109_2245
Revises: 20251109_1330
Create Date: 2025-11-09 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20251109_2245'
down_revision = '20251109_1330'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(50), nullable=False),  # statistical, ml, threshold
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('condition', sa.String(50), nullable=False),  # gt, lt, change, anomaly
        sa.Column('threshold_value', sa.Numeric(15, 4), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False),  # critical, high, medium, low
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('cooldown_minutes', sa.Integer(), default=60),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_alert_rules_severity', 'alert_rules', ['severity'])
    op.create_index('ix_alert_rules_is_active', 'alert_rules', ['is_active'])
    
    # Create anomaly_detections table
    op.create_table(
        'anomaly_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_value', sa.String(500), nullable=True),
        sa.Column('expected_value', sa.String(500), nullable=True),
        sa.Column('z_score', sa.Numeric(10, 4), nullable=True),
        sa.Column('percentage_change', sa.Numeric(10, 4), nullable=True),
        sa.Column('anomaly_type', sa.String(50), nullable=False),  # statistical, ml, missing_data
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['document_uploads.id'],
            name='fk_anomaly_document',
            ondelete='CASCADE'
        )
    )
    
    op.create_index('ix_anomaly_document_id', 'anomaly_detections', ['document_id'])
    op.create_index('ix_anomaly_severity', 'anomaly_detections', ['severity'])
    op.create_index('ix_anomaly_detected_at', 'anomaly_detections', ['detected_at'])
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_rule_id', sa.Integer(), nullable=False),
        sa.Column('anomaly_detection_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),  # pending, acknowledged, resolved, dismissed
        sa.Column('channels_sent', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('delivery_status', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['alert_rule_id'],
            ['alert_rules.id'],
            name='fk_alert_rule',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['anomaly_detection_id'],
            ['anomaly_detections.id'],
            name='fk_alert_anomaly',
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['document_uploads.id'],
            name='fk_alert_document',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['acknowledged_by'],
            ['users.id'],
            name='fk_alert_acknowledged_user',
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['resolved_by'],
            ['users.id'],
            name='fk_alert_resolved_user',
            ondelete='SET NULL'
        )
    )
    
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])
    op.create_index('ix_alerts_document_id', 'alerts', ['document_id'])


def downgrade() -> None:
    op.drop_index('ix_alerts_document_id', table_name='alerts')
    op.drop_index('ix_alerts_created_at', table_name='alerts')
    op.drop_index('ix_alerts_severity', table_name='alerts')
    op.drop_index('ix_alerts_status', table_name='alerts')
    op.drop_table('alerts')
    
    op.drop_index('ix_anomaly_detected_at', table_name='anomaly_detections')
    op.drop_index('ix_anomaly_severity', table_name='anomaly_detections')
    op.drop_index('ix_anomaly_document_id', table_name='anomaly_detections')
    op.drop_table('anomaly_detections')
    
    op.drop_index('ix_alert_rules_is_active', table_name='alert_rules')
    op.drop_index('ix_alert_rules_severity', table_name='alert_rules')
    op.drop_table('alert_rules')

