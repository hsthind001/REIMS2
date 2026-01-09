"""Add cross document reconciliations table

Revision ID: 20260108_0002
Revises: 20260108_0001
Create Date: 2026-01-08 00:02:00.000000

Creates cross_document_reconciliations for storing reconciliation results.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260108_0002'
down_revision = '20260108_0001'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'cross_document_reconciliations' in existing_tables:
        print("WARN: cross_document_reconciliations already exists. Skipping migration.")
        return

    op.create_table(
        'cross_document_reconciliations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reconciliation_type', sa.String(length=100), nullable=False),
        sa.Column('rule_code', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source_document', sa.String(length=100), nullable=True),
        sa.Column('target_document', sa.String(length=100), nullable=True),
        sa.Column('source_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('target_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('difference', sa.Numeric(15, 2), nullable=True),
        sa.Column('materiality_threshold', sa.Numeric(15, 4), nullable=True),
        sa.Column('is_material', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('intermediate_calculations', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            'property_id',
            'period_id',
            'reconciliation_type',
            name='uq_cross_doc_reconciliations_property_period_type'
        )
    )

    op.create_index(
        'ix_cross_document_reconciliations_property_id',
        'cross_document_reconciliations',
        ['property_id']
    )
    op.create_index(
        'ix_cross_document_reconciliations_period_id',
        'cross_document_reconciliations',
        ['period_id']
    )
    op.create_index(
        'ix_cross_document_reconciliations_status',
        'cross_document_reconciliations',
        ['status']
    )


def downgrade():
    existing_tables = sa.inspect(op.get_bind()).get_table_names()
    if 'cross_document_reconciliations' not in existing_tables:
        return

    op.drop_index('ix_cross_document_reconciliations_status', table_name='cross_document_reconciliations')
    op.drop_index('ix_cross_document_reconciliations_period_id', table_name='cross_document_reconciliations')
    op.drop_index('ix_cross_document_reconciliations_property_id', table_name='cross_document_reconciliations')
    op.drop_table('cross_document_reconciliations')
