"""Add Alert Enhancements

Revision ID: 20251220_0201
Revises: 20251220_0200
Create Date: 2025-12-20 02:01:00.000000

Enhances committee_alerts table with:
- priority_score (Numeric) - Calculated priority
- correlation_group_id (Integer) - Related alerts
- escalation_level (Integer) - Current escalation
- escalated_at (DateTime) - Last escalation time
- resolution_template_id (Integer) - Resolution template
- related_alert_ids (JSONB) - Linked alerts
- alert_tags (JSONB) - Custom tags
- performance_impact (String) - Estimated impact
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251220_0201'
down_revision = '20251220_0200'
branch_labels = None
depends_on = None


def upgrade():
    """Add enhancements to committee_alerts table"""

    # Check if table exists first
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'committee_alerts' not in existing_tables:
        # Table doesn't exist, skip this migration
        print("⚠️  committee_alerts table does not exist. Skipping alert enhancements migration.")
        return

    # Check if columns already exist
    existing_columns = [col['name'] for col in inspector.get_columns('committee_alerts')]
    
    # Add new columns to committee_alerts table (only if they don't exist)
    if 'priority_score' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('priority_score', sa.Numeric(10, 4), nullable=True))
    if 'correlation_group_id' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('correlation_group_id', sa.Integer(), nullable=True))
    if 'escalation_level' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('escalation_level', sa.Integer(), nullable=True, server_default='0'))
    if 'escalated_at' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('escalated_at', sa.DateTime(), nullable=True))
    if 'resolution_template_id' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('resolution_template_id', sa.Integer(), nullable=True))
    if 'related_alert_ids' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('related_alert_ids', postgresql.JSONB, nullable=True))
    if 'alert_tags' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('alert_tags', postgresql.JSONB, nullable=True))
    if 'performance_impact' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('performance_impact', sa.String(100), nullable=True))
    
    # Add indexes for performance
    op.create_index('ix_committee_alerts_priority_score', 'committee_alerts', ['priority_score'])
    op.create_index('ix_committee_alerts_correlation_group', 'committee_alerts', ['correlation_group_id'])
    op.create_index('ix_committee_alerts_escalation_level', 'committee_alerts', ['escalation_level'])
    op.create_index('ix_committee_alerts_escalated_at', 'committee_alerts', ['escalated_at'])


def downgrade():
    """Remove enhancements from committee_alerts table"""
    
    # Drop indexes
    op.drop_index('ix_committee_alerts_escalated_at', table_name='committee_alerts')
    op.drop_index('ix_committee_alerts_escalation_level', table_name='committee_alerts')
    op.drop_index('ix_committee_alerts_correlation_group', table_name='committee_alerts')
    op.drop_index('ix_committee_alerts_priority_score', table_name='committee_alerts')
    
    # Drop columns
    op.drop_column('committee_alerts', 'performance_impact')
    op.drop_column('committee_alerts', 'alert_tags')
    op.drop_column('committee_alerts', 'related_alert_ids')
    op.drop_column('committee_alerts', 'resolution_template_id')
    op.drop_column('committee_alerts', 'escalated_at')
    op.drop_column('committee_alerts', 'escalation_level')
    op.drop_column('committee_alerts', 'correlation_group_id')
    op.drop_column('committee_alerts', 'priority_score')

