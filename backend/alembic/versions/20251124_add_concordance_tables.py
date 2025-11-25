"""Add concordance tables for model comparison

Revision ID: 20251124_concordance
Revises: 20251123_coords
Create Date: 2025-11-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251124_concordance'
down_revision = '20251123_coords'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'concordance_tables',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=255), nullable=False),
        sa.Column('field_display_name', sa.String(length=255), nullable=True),
        sa.Column('account_code', sa.String(length=50), nullable=True),
        sa.Column('model_values', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('normalized_value', sa.String(length=255), nullable=True),
        sa.Column('agreement_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_models', sa.Integer(), server_default='0', nullable=False),
        sa.Column('agreement_percentage', sa.DECIMAL(precision=5, scale=2), server_default='0.0', nullable=False),
        sa.Column('has_consensus', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_perfect_agreement', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('conflicting_models', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('final_value', sa.String(length=255), nullable=True),
        sa.Column('final_model', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_concordance_tables_upload_id', 'concordance_tables', ['upload_id'])
    op.create_index('ix_concordance_tables_property_id', 'concordance_tables', ['property_id'])
    op.create_index('ix_concordance_tables_period_id', 'concordance_tables', ['period_id'])
    op.create_index('ix_concordance_tables_document_type', 'concordance_tables', ['document_type'])
    op.create_index('ix_concordance_tables_account_code', 'concordance_tables', ['account_code'])
    op.create_index('ix_concordance_upload_field', 'concordance_tables', ['upload_id', 'field_name'])
    op.create_index('ix_concordance_agreement', 'concordance_tables', ['has_consensus', 'agreement_percentage'])


def downgrade() -> None:
    op.drop_index('ix_concordance_agreement', table_name='concordance_tables')
    op.drop_index('ix_concordance_upload_field', table_name='concordance_tables')
    op.drop_index('ix_concordance_tables_account_code', table_name='concordance_tables')
    op.drop_index('ix_concordance_tables_document_type', table_name='concordance_tables')
    op.drop_index('ix_concordance_tables_period_id', table_name='concordance_tables')
    op.drop_index('ix_concordance_tables_property_id', table_name='concordance_tables')
    op.drop_index('ix_concordance_tables_upload_id', table_name='concordance_tables')
    op.drop_table('concordance_tables')

