"""Add committee_alerts and workflow_locks tables

Revision ID: 20251114_risk_mgmt
Revises: 20251114_next_level_features
Create Date: 2025-11-14 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251114_risk_mgmt'
down_revision = '20251114_next_level_features'
branch_labels = None
depends_on = None


def upgrade():
    # Create committee_alerts table
    op.create_table(
        'committee_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('financial_period_id', sa.Integer(), nullable=True),
        sa.Column('alert_type', sa.Enum(
            'DSCR_BREACH', 'OCCUPANCY_WARNING', 'OCCUPANCY_CRITICAL',
            'LTV_BREACH', 'COVENANT_VIOLATION', 'VARIANCE_BREACH',
            'ANOMALY_DETECTED', 'FINANCIAL_THRESHOLD',
            name='alerttype'
        ), nullable=False),
        sa.Column('severity', sa.Enum(
            'INFO', 'WARNING', 'CRITICAL', 'URGENT',
            name='alertseverity'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED',
            name='alertstatus'
        ), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('actual_value', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('threshold_unit', sa.String(length=50), nullable=True),
        sa.Column('assigned_committee', sa.Enum(
            'FINANCE_SUBCOMMITTEE', 'OCCUPANCY_SUBCOMMITTEE',
            'RISK_COMMITTEE', 'EXECUTIVE_COMMITTEE',
            name='committeetype'
        ), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('dismissed_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('dismissal_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('related_metric', sa.String(length=100), nullable=True),
        sa.Column('br_id', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dismissed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['financial_period_id'], ['financial_periods.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_committee_alerts_id'), 'committee_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_committee_alerts_property_id'), 'committee_alerts', ['property_id'], unique=False)
    op.create_index(op.f('ix_committee_alerts_alert_type'), 'committee_alerts', ['alert_type'], unique=False)
    op.create_index(op.f('ix_committee_alerts_status'), 'committee_alerts', ['status'], unique=False)
    op.create_index(op.f('ix_committee_alerts_triggered_at'), 'committee_alerts', ['triggered_at'], unique=False)

    # Create workflow_locks table
    op.create_table(
        'workflow_locks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=True),
        sa.Column('lock_reason', sa.Enum(
            'DSCR_BREACH', 'OCCUPANCY_THRESHOLD', 'COVENANT_VIOLATION',
            'COMMITTEE_REVIEW', 'FINANCIAL_ANOMALY', 'VARIANCE_BREACH',
            'MANUAL_HOLD', 'DATA_QUALITY_ISSUE',
            name='lockreason'
        ), nullable=False),
        sa.Column('lock_scope', sa.Enum(
            'PROPERTY_ALL', 'FINANCIAL_UPDATES', 'REPORTING_ONLY',
            'TRANSACTION_APPROVAL', 'DATA_ENTRY',
            name='lockscope'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'ACTIVE', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'RELEASED',
            name='lockstatus'
        ), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requires_committee_approval', sa.Boolean(), nullable=True),
        sa.Column('approval_committee', sa.String(length=100), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('locked_by', sa.Integer(), nullable=False),
        sa.Column('unlocked_by', sa.Integer(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('auto_release_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_released', sa.Boolean(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('br_id', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['committee_alerts.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['locked_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['unlocked_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_locks_id'), 'workflow_locks', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_locks_property_id'), 'workflow_locks', ['property_id'], unique=False)
    op.create_index(op.f('ix_workflow_locks_alert_id'), 'workflow_locks', ['alert_id'], unique=False)
    op.create_index(op.f('ix_workflow_locks_status'), 'workflow_locks', ['status'], unique=False)
    op.create_index(op.f('ix_workflow_locks_locked_at'), 'workflow_locks', ['locked_at'], unique=False)


def downgrade():
    # Drop workflow_locks table
    op.drop_index(op.f('ix_workflow_locks_locked_at'), table_name='workflow_locks')
    op.drop_index(op.f('ix_workflow_locks_status'), table_name='workflow_locks')
    op.drop_index(op.f('ix_workflow_locks_alert_id'), table_name='workflow_locks')
    op.drop_index(op.f('ix_workflow_locks_property_id'), table_name='workflow_locks')
    op.drop_index(op.f('ix_workflow_locks_id'), table_name='workflow_locks')
    op.drop_table('workflow_locks')

    # Drop committee_alerts table
    op.drop_index(op.f('ix_committee_alerts_triggered_at'), table_name='committee_alerts')
    op.drop_index(op.f('ix_committee_alerts_status'), table_name='committee_alerts')
    op.drop_index(op.f('ix_committee_alerts_alert_type'), table_name='committee_alerts')
    op.drop_index(op.f('ix_committee_alerts_property_id'), table_name='committee_alerts')
    op.drop_index(op.f('ix_committee_alerts_id'), table_name='committee_alerts')
    op.drop_table('committee_alerts')

    # Drop enums
    sa.Enum(name='lockstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='lockscope').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='lockreason').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='committeetype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alertstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alertseverity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alerttype').drop(op.get_bind(), checkfirst=True)
