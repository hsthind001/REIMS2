"""Fix committee alerts schema

Revision ID: 20260107_0002
Revises: 20260106_1722, 20260107_0001
Create Date: 2026-01-07 00:02:00.000000

Ensures committee_alerts has the enhanced alert fields expected by the model.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260107_0002'
down_revision = ('20260106_1722', '20260107_0001')
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'committee_alerts' not in existing_tables:
        print("⚠️  committee_alerts table does not exist. Skipping schema fix migration.")
        return

    existing_columns = {col['name'] for col in inspector.get_columns('committee_alerts')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('committee_alerts')}

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

    if 'business_impact_score' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('business_impact_score', sa.Numeric(10, 4), nullable=True))
    if 'sla_due_at' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True))
    if 'mtta' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('mtta', sa.Integer(), nullable=True))
    if 'mttr' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('mttr', sa.Integer(), nullable=True))
    if 'incident_group_id' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('incident_group_id', postgresql.UUID(as_uuid=True), nullable=True))
    if 'alert_fatigue_score' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('alert_fatigue_score', sa.Numeric(5, 2), nullable=True))

    if 'ix_committee_alerts_priority_score' not in existing_indexes:
        op.create_index('ix_committee_alerts_priority_score', 'committee_alerts', ['priority_score'])
    if 'ix_committee_alerts_correlation_group' not in existing_indexes:
        op.create_index('ix_committee_alerts_correlation_group', 'committee_alerts', ['correlation_group_id'])
    if 'ix_committee_alerts_escalation_level' not in existing_indexes:
        op.create_index('ix_committee_alerts_escalation_level', 'committee_alerts', ['escalation_level'])
    if 'ix_committee_alerts_escalated_at' not in existing_indexes:
        op.create_index('ix_committee_alerts_escalated_at', 'committee_alerts', ['escalated_at'])
    if 'ix_committee_alerts_business_impact_score' not in existing_indexes:
        op.create_index('ix_committee_alerts_business_impact_score', 'committee_alerts', ['business_impact_score'])
    if 'ix_committee_alerts_sla_due_at' not in existing_indexes:
        op.create_index('ix_committee_alerts_sla_due_at', 'committee_alerts', ['sla_due_at'])
    if 'ix_committee_alerts_incident_group_id' not in existing_indexes:
        op.create_index('ix_committee_alerts_incident_group_id', 'committee_alerts', ['incident_group_id'])
    if 'ix_committee_alerts_fatigue_score' not in existing_indexes:
        op.create_index('ix_committee_alerts_fatigue_score', 'committee_alerts', ['alert_fatigue_score'])
    if 'ix_committee_alerts_sla_status' not in existing_indexes:
        op.create_index('ix_committee_alerts_sla_status', 'committee_alerts', ['sla_due_at', 'status'])


def downgrade():
    existing_indexes = {idx['name'] for idx in sa.inspect(op.get_bind()).get_indexes('committee_alerts')}

    if 'ix_committee_alerts_sla_status' in existing_indexes:
        op.drop_index('ix_committee_alerts_sla_status', table_name='committee_alerts')
    if 'ix_committee_alerts_fatigue_score' in existing_indexes:
        op.drop_index('ix_committee_alerts_fatigue_score', table_name='committee_alerts')
    if 'ix_committee_alerts_incident_group_id' in existing_indexes:
        op.drop_index('ix_committee_alerts_incident_group_id', table_name='committee_alerts')
    if 'ix_committee_alerts_sla_due_at' in existing_indexes:
        op.drop_index('ix_committee_alerts_sla_due_at', table_name='committee_alerts')
    if 'ix_committee_alerts_business_impact_score' in existing_indexes:
        op.drop_index('ix_committee_alerts_business_impact_score', table_name='committee_alerts')
    if 'ix_committee_alerts_escalated_at' in existing_indexes:
        op.drop_index('ix_committee_alerts_escalated_at', table_name='committee_alerts')
    if 'ix_committee_alerts_escalation_level' in existing_indexes:
        op.drop_index('ix_committee_alerts_escalation_level', table_name='committee_alerts')
    if 'ix_committee_alerts_correlation_group' in existing_indexes:
        op.drop_index('ix_committee_alerts_correlation_group', table_name='committee_alerts')
    if 'ix_committee_alerts_priority_score' in existing_indexes:
        op.drop_index('ix_committee_alerts_priority_score', table_name='committee_alerts')

    op.drop_column('committee_alerts', 'alert_fatigue_score')
    op.drop_column('committee_alerts', 'incident_group_id')
    op.drop_column('committee_alerts', 'mttr')
    op.drop_column('committee_alerts', 'mtta')
    op.drop_column('committee_alerts', 'sla_due_at')
    op.drop_column('committee_alerts', 'business_impact_score')
    op.drop_column('committee_alerts', 'performance_impact')
    op.drop_column('committee_alerts', 'alert_tags')
    op.drop_column('committee_alerts', 'related_alert_ids')
    op.drop_column('committee_alerts', 'resolution_template_id')
    op.drop_column('committee_alerts', 'escalated_at')
    op.drop_column('committee_alerts', 'escalation_level')
    op.drop_column('committee_alerts', 'correlation_group_id')
    op.drop_column('committee_alerts', 'priority_score')
