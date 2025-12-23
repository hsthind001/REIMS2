"""Create account_mapping_rules table

Revision ID: 20251222_0003
Revises: 20251222_0002
Create Date: 2025-12-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251222_0003'
down_revision = '20251222_0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'account_mapping_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raw_label', sa.String(length=500), nullable=False),
        sa.Column('account_code', sa.String(length=100), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.5'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('last_used_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['last_used_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_mapping_rules_id'), 'account_mapping_rules', ['id'], unique=False)
    op.create_index(op.f('ix_account_mapping_rules_raw_label'), 'account_mapping_rules', ['raw_label'], unique=False)
    op.create_index(op.f('ix_account_mapping_rules_account_code'), 'account_mapping_rules', ['account_code'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_account_mapping_rules_account_code'), table_name='account_mapping_rules')
    op.drop_index(op.f('ix_account_mapping_rules_raw_label'), table_name='account_mapping_rules')
    op.drop_index(op.f('ix_account_mapping_rules_id'), table_name='account_mapping_rules')
    op.drop_table('account_mapping_rules')
