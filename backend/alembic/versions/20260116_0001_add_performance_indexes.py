"""Add performance indexes for frequently queried columns

Revision ID: 20260116_0001
Revises: 20260111_0001_add_ai_insights_embeddings_table
Create Date: 2026-01-16

This migration adds database indexes to improve query performance for:
1. Property lookups by property_code
2. Document status filtering by extraction_status
3. Composite index for document queries by property_id, period_id, extraction_status
4. Financial data lookups by property_id and period_id
5. Anomaly detection queries
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260116_0001_perf_indexes'
down_revision = '20260111_0001_ai_embeddings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # PROPERTY TABLE INDEXES
    # ==========================================================================
    # Property code is the primary lookup field for all property queries
    op.create_index(
        'ix_property_property_code',
        'properties',
        ['property_code'],
        unique=False,
        if_not_exists=True
    )

    # Property status for filtering active/inactive properties
    op.create_index(
        'ix_property_status',
        'properties',
        ['status'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # DOCUMENT UPLOAD TABLE INDEXES
    # ==========================================================================
    # Extraction status is frequently filtered (pending, processing, completed, failed)
    op.create_index(
        'ix_document_upload_extraction_status',
        'document_uploads',
        ['extraction_status'],
        unique=False,
        if_not_exists=True
    )

    # Composite index for common query pattern: get documents for a property/period
    op.create_index(
        'ix_document_upload_property_period_status',
        'document_uploads',
        ['property_id', 'period_id', 'extraction_status'],
        unique=False,
        if_not_exists=True
    )

    # Document type filtering
    op.create_index(
        'ix_document_upload_document_type',
        'document_uploads',
        ['document_type'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # BALANCE SHEET DATA INDEXES
    # ==========================================================================
    # Composite index for financial data lookups
    op.create_index(
        'ix_balance_sheet_data_property_period',
        'balance_sheet_data',
        ['property_id', 'period_id'],
        unique=False,
        if_not_exists=True
    )

    # Account code lookups for specific account queries
    op.create_index(
        'ix_balance_sheet_data_account_code',
        'balance_sheet_data',
        ['account_code'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # INCOME STATEMENT DATA INDEXES
    # ==========================================================================
    op.create_index(
        'ix_income_statement_data_property_period',
        'income_statement_data',
        ['property_id', 'period_id'],
        unique=False,
        if_not_exists=True
    )

    op.create_index(
        'ix_income_statement_data_account_code',
        'income_statement_data',
        ['account_code'],
        unique=False,
        if_not_exists=True
    )

    # Account category for filtering revenue vs expenses
    op.create_index(
        'ix_income_statement_data_line_category',
        'income_statement_data',
        ['line_category'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # CASH FLOW DATA INDEXES
    # ==========================================================================
    op.create_index(
        'ix_cash_flow_data_property_period',
        'cash_flow_data',
        ['property_id', 'period_id'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # RENT ROLL DATA INDEXES
    # ==========================================================================
    op.create_index(
        'ix_rent_roll_data_property_period',
        'rent_roll_data',
        ['property_id', 'period_id'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # ANOMALY DETECTION INDEXES
    # ==========================================================================


    # ==========================================================================
    # COMMITTEE ALERT INDEXES
    # ==========================================================================
    op.create_index(
        'ix_committee_alert_status',
        'committee_alerts',
        ['status'],
        unique=False,
        if_not_exists=True
    )

    op.create_index(
        'ix_committee_alert_property_id',
        'committee_alerts',
        ['property_id'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # FINANCIAL METRICS INDEXES
    # ==========================================================================
    op.create_index(
        'ix_financial_metrics_property_period',
        'financial_metrics',
        ['property_id', 'period_id'],
        unique=False,
        if_not_exists=True
    )

    # ==========================================================================
    # FINANCIAL PERIOD INDEXES
    # ==========================================================================
    # Year/month lookups for temporal queries
    op.create_index(
        'ix_financial_period_year_month',
        'financial_periods',
        ['period_year', 'period_month'],
        unique=False,
        if_not_exists=True
    )


def downgrade() -> None:
    # Remove all indexes in reverse order
    op.drop_index('ix_financial_period_year_month', table_name='financial_periods', if_exists=True)
    op.drop_index('ix_financial_metrics_property_period', table_name='financial_metrics', if_exists=True)
    op.drop_index('ix_committee_alert_property_id', table_name='committee_alerts', if_exists=True)
    op.drop_index('ix_committee_alert_status', table_name='committee_alerts', if_exists=True)
    op.drop_index('ix_anomaly_detection_property_id', table_name='anomaly_detections', if_exists=True)
    op.drop_index('ix_rent_roll_data_property_period', table_name='rent_roll_data', if_exists=True)
    op.drop_index('ix_cash_flow_data_property_period', table_name='cash_flow_data', if_exists=True)
    op.drop_index('ix_income_statement_data_line_category', table_name='income_statement_data', if_exists=True)
    op.drop_index('ix_income_statement_data_account_code', table_name='income_statement_data', if_exists=True)
    op.drop_index('ix_income_statement_data_property_period', table_name='income_statement_data', if_exists=True)
    op.drop_index('ix_balance_sheet_data_account_code', table_name='balance_sheet_data', if_exists=True)
    op.drop_index('ix_balance_sheet_data_property_period', table_name='balance_sheet_data', if_exists=True)
    op.drop_index('ix_document_upload_document_type', table_name='document_uploads', if_exists=True)
    op.drop_index('ix_document_upload_property_period_status', table_name='document_uploads', if_exists=True)
    op.drop_index('ix_document_upload_extraction_status', table_name='document_uploads', if_exists=True)
    op.drop_index('ix_property_status', table_name='properties', if_exists=True)
    op.drop_index('ix_property_property_code', table_name='properties', if_exists=True)
