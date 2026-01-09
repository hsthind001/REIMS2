"""Add audit scorecard summary table

Revision ID: 20260108_0001
Revises: 20260107_0002
Create Date: 2026-01-08 00:01:00.000000

Creates audit_scorecard_summary for executive scorecards and history.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260108_0001'
down_revision = '20260107_0002'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'audit_scorecard_summary' in existing_tables:
        print("WARN: audit_scorecard_summary already exists. Skipping migration.")
        return

    op.create_table(
        'audit_scorecard_summary',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
        sa.Column('overall_health_score', sa.Integer(), nullable=True),
        sa.Column('traffic_light_status', sa.String(length=20), nullable=True),
        sa.Column('audit_opinion', sa.String(length=20), nullable=True),
        sa.Column('priority_risks', postgresql.JSONB, nullable=True),
        sa.Column('action_items', postgresql.JSONB, nullable=True),
        sa.Column('critical_issues_count', sa.Integer(), nullable=True),
        sa.Column('scorecard_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('property_id', 'period_id', name='uq_audit_scorecard_summary_property_period')
    )

    op.create_index('ix_audit_scorecard_summary_property_id', 'audit_scorecard_summary', ['property_id'])
    op.create_index('ix_audit_scorecard_summary_period_id', 'audit_scorecard_summary', ['period_id'])
    op.create_index('ix_audit_scorecard_summary_created_at', 'audit_scorecard_summary', ['created_at'])


def downgrade():
    existing_tables = sa.inspect(op.get_bind()).get_table_names()
    if 'audit_scorecard_summary' not in existing_tables:
        return

    op.drop_index('ix_audit_scorecard_summary_created_at', table_name='audit_scorecard_summary')
    op.drop_index('ix_audit_scorecard_summary_period_id', table_name='audit_scorecard_summary')
    op.drop_index('ix_audit_scorecard_summary_property_id', table_name='audit_scorecard_summary')
    op.drop_table('audit_scorecard_summary')
