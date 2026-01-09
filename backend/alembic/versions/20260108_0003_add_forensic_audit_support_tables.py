"""Add forensic audit support tables and completeness view

Revision ID: 20260108_0003
Revises: 20260108_0002
Create Date: 2026-01-08 00:03:00.000000

Adds core tables used by forensic audit phases and a completeness view.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260108_0003'
down_revision = '20260108_0002'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'document_completeness' not in existing_tables:
        op.create_table(
            'document_completeness',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
            sa.Column('completeness_percentage', sa.Numeric(6, 2), nullable=True),
            sa.Column('documents_present', sa.Integer(), nullable=True),
            sa.Column('documents_complete', sa.Integer(), nullable=True),
            sa.Column('overall_status', sa.String(length=20), nullable=True),
            sa.Column('can_proceed', sa.Boolean(), nullable=True),
            sa.Column('results_json', postgresql.JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('property_id', 'period_id', name='uq_document_completeness_property_period')
        )
        op.create_index('ix_document_completeness_property_id', 'document_completeness', ['property_id'])
        op.create_index('ix_document_completeness_period_id', 'document_completeness', ['period_id'])

    if 'tenant_risk_analysis' not in existing_tables:
        op.create_table(
            'tenant_risk_analysis',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
            sa.Column('top_1_tenant_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('top_3_tenant_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('top_5_tenant_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('top_10_tenant_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('concentration_risk_status', sa.String(length=20), nullable=True),
            sa.Column('lease_rollover_12mo_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('lease_rollover_24mo_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('lease_rollover_36mo_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('occupancy_rate', sa.Numeric(6, 2), nullable=True),
            sa.Column('investment_grade_tenant_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('tenant_profiles', postgresql.JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('property_id', 'period_id', name='uq_tenant_risk_analysis_property_period')
        )
        op.create_index('ix_tenant_risk_analysis_property_id', 'tenant_risk_analysis', ['property_id'])
        op.create_index('ix_tenant_risk_analysis_period_id', 'tenant_risk_analysis', ['period_id'])

    if 'collections_revenue_quality' not in existing_tables:
        op.create_table(
            'collections_revenue_quality',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
            sa.Column('days_sales_outstanding', sa.Numeric(10, 2), nullable=True),
            sa.Column('dso_status', sa.String(length=20), nullable=True),
            sa.Column('cash_conversion_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('revenue_quality_score', sa.Numeric(6, 2), nullable=True),
            sa.Column('ar_aging_details', postgresql.JSONB, nullable=True),
            sa.Column('overall_status', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('property_id', 'period_id', name='uq_collections_revenue_quality_property_period')
        )
        op.create_index('ix_collections_revenue_quality_property_id', 'collections_revenue_quality', ['property_id'])
        op.create_index('ix_collections_revenue_quality_period_id', 'collections_revenue_quality', ['period_id'])

    if 'fraud_detection_results' not in existing_tables:
        op.create_table(
            'fraud_detection_results',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
            sa.Column('benfords_law_chi_square', sa.Numeric(10, 4), nullable=True),
            sa.Column('benfords_law_status', sa.String(length=20), nullable=True),
            sa.Column('round_number_pct', sa.Numeric(6, 2), nullable=True),
            sa.Column('round_number_status', sa.String(length=20), nullable=True),
            sa.Column('duplicate_payment_count', sa.Integer(), nullable=True),
            sa.Column('duplicate_payment_details', postgresql.JSONB, nullable=True),
            sa.Column('cash_conversion_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('cash_ratio_status', sa.String(length=20), nullable=True),
            sa.Column('overall_fraud_risk_level', sa.String(length=20), nullable=True),
            sa.Column('red_flags_found', sa.Integer(), nullable=True),
            sa.Column('test_details', postgresql.JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('property_id', 'period_id', name='uq_fraud_detection_results_property_period')
        )
        op.create_index('ix_fraud_detection_results_property_id', 'fraud_detection_results', ['property_id'])
        op.create_index('ix_fraud_detection_results_period_id', 'fraud_detection_results', ['period_id'])

    if 'covenant_compliance_tracking' not in existing_tables:
        op.create_table(
            'covenant_compliance_tracking',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
            sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False),
            sa.Column('dscr', sa.Numeric(10, 4), nullable=True),
            sa.Column('dscr_covenant_threshold', sa.Numeric(10, 4), nullable=True),
            sa.Column('dscr_cushion', sa.Numeric(10, 4), nullable=True),
            sa.Column('dscr_status', sa.String(length=20), nullable=True),
            sa.Column('dscr_trend', sa.String(length=20), nullable=True),
            sa.Column('ltv_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('ltv_covenant_threshold', sa.Numeric(10, 4), nullable=True),
            sa.Column('ltv_cushion', sa.Numeric(10, 4), nullable=True),
            sa.Column('ltv_status', sa.String(length=20), nullable=True),
            sa.Column('ltv_trend', sa.String(length=20), nullable=True),
            sa.Column('interest_coverage_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('current_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('quick_ratio', sa.Numeric(10, 4), nullable=True),
            sa.Column('overall_compliance_status', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('property_id', 'period_id', name='uq_covenant_compliance_property_period')
        )
        op.create_index('ix_covenant_compliance_property_id', 'covenant_compliance_tracking', ['property_id'])
        op.create_index('ix_covenant_compliance_period_id', 'covenant_compliance_tracking', ['period_id'])

    op.execute("""
        CREATE OR REPLACE VIEW document_completeness_matrix AS
        SELECT
            du.property_id,
            du.period_id,
            fp.period_year,
            fp.period_month,
            BOOL_OR(du.document_type = 'balance_sheet' AND du.is_active IS TRUE) AS has_balance_sheet,
            BOOL_OR(du.document_type = 'income_statement' AND du.is_active IS TRUE) AS has_income_statement,
            BOOL_OR(du.document_type = 'cash_flow' AND du.is_active IS TRUE) AS has_cash_flow_statement,
            BOOL_OR(du.document_type = 'rent_roll' AND du.is_active IS TRUE) AS has_rent_roll,
            BOOL_OR(du.document_type = 'mortgage_statement' AND du.is_active IS TRUE) AS has_mortgage_statement,
            (
                (CASE WHEN BOOL_OR(du.document_type = 'balance_sheet' AND du.is_active IS TRUE) THEN 1 ELSE 0 END) +
                (CASE WHEN BOOL_OR(du.document_type = 'income_statement' AND du.is_active IS TRUE) THEN 1 ELSE 0 END) +
                (CASE WHEN BOOL_OR(du.document_type = 'cash_flow' AND du.is_active IS TRUE) THEN 1 ELSE 0 END) +
                (CASE WHEN BOOL_OR(du.document_type = 'rent_roll' AND du.is_active IS TRUE) THEN 1 ELSE 0 END) +
                (CASE WHEN BOOL_OR(du.document_type = 'mortgage_statement' AND du.is_active IS TRUE) THEN 1 ELSE 0 END)
            )::numeric / 5 * 100 AS completeness_percentage,
            MAX(du.upload_date) AS created_at
        FROM document_uploads du
        JOIN financial_periods fp ON fp.id = du.period_id
        GROUP BY du.property_id, du.period_id, fp.period_year, fp.period_month;
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS document_completeness_matrix")

    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if 'covenant_compliance_tracking' in existing_tables:
        op.drop_index('ix_covenant_compliance_period_id', table_name='covenant_compliance_tracking')
        op.drop_index('ix_covenant_compliance_property_id', table_name='covenant_compliance_tracking')
        op.drop_table('covenant_compliance_tracking')

    if 'fraud_detection_results' in existing_tables:
        op.drop_index('ix_fraud_detection_results_period_id', table_name='fraud_detection_results')
        op.drop_index('ix_fraud_detection_results_property_id', table_name='fraud_detection_results')
        op.drop_table('fraud_detection_results')

    if 'collections_revenue_quality' in existing_tables:
        op.drop_index('ix_collections_revenue_quality_period_id', table_name='collections_revenue_quality')
        op.drop_index('ix_collections_revenue_quality_property_id', table_name='collections_revenue_quality')
        op.drop_table('collections_revenue_quality')

    if 'tenant_risk_analysis' in existing_tables:
        op.drop_index('ix_tenant_risk_analysis_period_id', table_name='tenant_risk_analysis')
        op.drop_index('ix_tenant_risk_analysis_property_id', table_name='tenant_risk_analysis')
        op.drop_table('tenant_risk_analysis')

    if 'document_completeness' in existing_tables:
        op.drop_index('ix_document_completeness_period_id', table_name='document_completeness')
        op.drop_index('ix_document_completeness_property_id', table_name='document_completeness')
        op.drop_table('document_completeness')
