"""add data governance and gl tables

Revision ID: 20260128_0001
Revises: 20260125_0002_add_property_coordinates
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260128_0001"
down_revision = "20260125_0002_add_property_coordinates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_owners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_governance_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("data_owners.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "data_access_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("permission_level", sa.String(length=50), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_retention_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("retention_years", sa.Integer(), nullable=False),
        sa.Column("legal_basis", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document_uploads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_id", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_dq_issues_property", "data_quality_issues", ["property_id"], unique=False)
    op.create_index("ix_dq_issues_period", "data_quality_issues", ["period_id"], unique=False)
    op.create_index("ix_dq_issues_document", "data_quality_issues", ["document_id"], unique=False)

    op.create_table(
        "data_quality_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("data_quality_issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dq_corrections_issue", "data_quality_corrections", ["issue_id"], unique=False)

    op.create_table(
        "gl_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("imported_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gl_batch_property", "gl_import_batches", ["property_id"], unique=False)

    op.create_table(
        "general_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("gl_import_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("account_code", sa.String(length=50), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("debit_credit", sa.String(length=10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vendor_name", sa.String(length=255), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("transaction_id", sa.String(length=255), nullable=True),
        sa.Column("is_adjustment", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gl_property_period", "general_ledger_entries", ["property_id", "period_id"], unique=False)
    op.create_index("ix_gl_account", "general_ledger_entries", ["account_code"], unique=False)
    op.create_index("ix_gl_entry_date", "general_ledger_entries", ["entry_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gl_entry_date", table_name="general_ledger_entries")
    op.drop_index("ix_gl_account", table_name="general_ledger_entries")
    op.drop_index("ix_gl_property_period", table_name="general_ledger_entries")
    op.drop_table("general_ledger_entries")

    op.drop_index("ix_gl_batch_property", table_name="gl_import_batches")
    op.drop_table("gl_import_batches")

    op.drop_index("ix_dq_corrections_issue", table_name="data_quality_corrections")
    op.drop_table("data_quality_corrections")

    op.drop_index("ix_dq_issues_document", table_name="data_quality_issues")
    op.drop_index("ix_dq_issues_period", table_name="data_quality_issues")
    op.drop_index("ix_dq_issues_property", table_name="data_quality_issues")
    op.drop_table("data_quality_issues")

    op.drop_table("data_retention_policies")
    op.drop_table("data_access_controls")
    op.drop_table("data_governance_policies")
    op.drop_table("data_owners")
