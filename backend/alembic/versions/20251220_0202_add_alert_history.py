"""Add Alert History Table

Revision ID: 20251220_0202_add_alert_history
Revises: 20251220_0201_add_alert_enhancements
Create Date: 2025-12-20 02:02:00.000000

Creates alert_history table to track:
- All alert state changes
- User actions (acknowledge, resolve, dismiss)
- Escalation events
- Notification deliveries
- Resolution steps
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251220_0202_add_alert_history'
down_revision = '20251220_0201_add_alert_enhancements'
branch_labels = None
depends_on = None


def upgrade():
    """Create alert_history table"""
    
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),  # created, acknowledged, resolved, dismissed, escalated, notified
        sa.Column('action_by', sa.Integer(), nullable=True),  # User ID
        sa.Column('action_at', sa.DateTime(), nullable=False),
        sa.Column('previous_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=True),
        sa.Column('previous_severity', sa.String(20), nullable=True),
        sa.Column('new_severity', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('action_metadata', postgresql.JSONB, nullable=True),  # Additional action-specific data (renamed from metadata to avoid SQLAlchemy reserved word)
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add foreign key to committee_alerts
    try:
        op.create_foreign_key(
            'fk_alert_history_alert',
            'alert_history', 'committee_alerts',
            ['alert_id'], ['id'],
            ondelete='CASCADE'
        )
    except Exception:
        # Table might not exist yet
        pass
    
    # Add indexes for performance
    op.create_index('ix_alert_history_alert_id', 'alert_history', ['alert_id'])
    op.create_index('ix_alert_history_action_type', 'alert_history', ['action_type'])
    op.create_index('ix_alert_history_action_at', 'alert_history', ['action_at'])
    op.create_index('ix_alert_history_action_by', 'alert_history', ['action_by'])


def downgrade():
    """Drop alert_history table"""
    
    op.drop_index('ix_alert_history_action_by', table_name='alert_history')
    op.drop_index('ix_alert_history_action_at', table_name='alert_history')
    op.drop_index('ix_alert_history_action_type', table_name='alert_history')
    op.drop_index('ix_alert_history_alert_id', table_name='alert_history')
    
    try:
        op.drop_constraint('fk_alert_history_alert', 'alert_history', type_='foreignkey')
    except Exception:
        pass
    
    op.drop_table('alert_history')

