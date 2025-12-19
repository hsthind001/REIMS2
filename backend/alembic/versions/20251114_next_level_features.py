"""Next Level Features - AI Agents, Research, NLQ

Revision ID: 20251114_next_level_features
Revises: (latest revision)
Create Date: 2025-11-14

Adds tables for:
- Property research data (demographics, employment, developments)
- Tenant recommendations
- Extraction corrections (active learning)
- Natural language queries
- Report audits
- Tenant performance history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251114_next_level_features'
down_revision = '20251112_0001'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Property Research table
    op.create_table(
        'property_research',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('research_date', sa.Date(), nullable=False),
        sa.Column('demographics_data', JSONB, nullable=True),
        sa.Column('employment_data', JSONB, nullable=True),
        sa.Column('developments_data', JSONB, nullable=True),
        sa.Column('market_data', JSONB, nullable=True),
        sa.Column('sources', JSONB, nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_research_property', 'property_research', ['property_id'])
    op.create_index('idx_research_date', 'property_research', ['research_date'])
    op.create_index('idx_research_demographics', 'property_research', ['demographics_data'], postgresql_using='gin')

    # 2. Tenant Recommendations table
    op.create_table(
        'tenant_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('unit_identifier', sa.String(100), nullable=True),
        sa.Column('space_sqft', sa.Integer(), nullable=True),
        sa.Column('recommendation_date', sa.Date(), nullable=False),
        sa.Column('recommendations', JSONB, nullable=False),  # Array of recommendation objects
        sa.Column('demographics_used', JSONB, nullable=True),
        sa.Column('tenant_mix_used', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_rec_property', 'tenant_recommendations', ['property_id'])
    op.create_index('idx_tenant_rec_date', 'tenant_recommendations', ['recommendation_date'])

    # 3. Extraction Corrections table (for active learning)
    op.create_table(
        'extraction_corrections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_metadata_id', sa.Integer(), nullable=True),
        sa.Column('original_value', sa.Text(), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('correction_type', sa.String(50), nullable=False),
        sa.Column('corrected_by', sa.Integer(), nullable=False),
        sa.Column('corrected_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('confidence_before', sa.Numeric(5, 4), nullable=True),
        sa.Column('pattern_detected', JSONB, nullable=True),
        sa.Column('applied_to_future', sa.Boolean(), server_default='false'),
        sa.ForeignKeyConstraint(['field_metadata_id'], ['extraction_field_metadata.id'], ondelete='SET NULL'),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['corrected_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_corrections_type', 'extraction_corrections', ['correction_type'])
    op.create_index('idx_corrections_pattern', 'extraction_corrections', ['pattern_detected'], postgresql_using='gin')
    op.create_index('idx_corrections_user', 'extraction_corrections', ['corrected_by'])

    # 4. Natural Language Queries table
    op.create_table(
        'nlq_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('intent', JSONB, nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('data_retrieved', JSONB, nullable=True),
        sa.Column('citations', JSONB, nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('sql_query', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_nlq_user', 'nlq_queries', ['user_id'])
    op.create_index('idx_nlq_date', 'nlq_queries', ['created_at'])

    # 5. Report Audits table
    op.create_table(
        'report_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('report_type', sa.String(100), nullable=False),
        sa.Column('audit_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('issues_found', JSONB, nullable=True),
        sa.Column('factual_accuracy', sa.Numeric(5, 4), nullable=True),
        sa.Column('citation_coverage', sa.Numeric(5, 4), nullable=True),
        sa.Column('hallucination_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('overall_quality', sa.String(10), nullable=True),
        sa.Column('audited_by', sa.String(100), server_default='M3-Auditor'),
        sa.Column('approved', sa.Boolean(), server_default='false'),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audits_report', 'report_audits', ['report_id', 'report_type'])
    op.create_index('idx_audits_quality', 'report_audits', ['overall_quality'])

    # 6. Tenant Performance History table
    op.create_table(
        'tenant_performance_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('tenant_name', sa.String(200), nullable=False),
        sa.Column('tenant_category', sa.String(100), nullable=True),
        sa.Column('lease_start_date', sa.Date(), nullable=True),
        sa.Column('lease_end_date', sa.Date(), nullable=True),
        sa.Column('monthly_rent', sa.Numeric(12, 2), nullable=True),
        sa.Column('space_sqft', sa.Integer(), nullable=True),
        sa.Column('performance_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('renewals_count', sa.Integer(), default=0),
        sa.Column('still_operating', sa.Boolean(), default=True),
        sa.Column('demographics_at_lease', JSONB, nullable=True),
        sa.Column('tenant_mix_at_lease', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tenant_perf_property', 'tenant_performance_history', ['property_id'])
    op.create_index('idx_tenant_perf_category', 'tenant_performance_history', ['tenant_category'])


def downgrade():
    op.drop_table('tenant_performance_history')
    op.drop_table('report_audits')
    op.drop_table('nlq_queries')
    op.drop_table('extraction_corrections')
    op.drop_table('tenant_recommendations')
    op.drop_table('property_research')
