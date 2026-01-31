"""Add organization_id to validation_results, balance_sheet_data, income_statement_data, cash_flow_data, rent_roll_data (E2-S3)

Revision ID: 20260130_0007
Revises: 20260130_0006
Create Date: 2026-01-30

Part of tenant isolation - backfill from document_uploads or properties.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0007"
down_revision = "20260130_0006"
branch_labels = None
depends_on = None


def _add_org_column(table: str, backfill_sql: str, fk_name: str, idx_name: str) -> None:
    op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(fk_name, table, "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.execute(backfill_sql)
    op.create_index(idx_name, table, ["organization_id"], unique=False)


def _drop_org_column(table: str, fk_name: str, idx_name: str) -> None:
    op.drop_index(idx_name, table_name=table)
    op.drop_constraint(fk_name, table, type_="foreignkey")
    op.drop_column(table, "organization_id")


def upgrade() -> None:
    # validation_results: via document_uploads
    _add_org_column(
        "validation_results",
        """
        UPDATE validation_results vr
        SET organization_id = du.organization_id
        FROM document_uploads du
        WHERE vr.upload_id = du.id AND du.organization_id IS NOT NULL
        """,
        "fk_validation_results_organization",
        "ix_validation_results_organization_id",
    )

    # balance_sheet_data: via property
    _add_org_column(
        "balance_sheet_data",
        """
        UPDATE balance_sheet_data bs
        SET organization_id = p.organization_id
        FROM properties p
        WHERE bs.property_id = p.id AND p.organization_id IS NOT NULL
        """,
        "fk_balance_sheet_data_organization",
        "ix_balance_sheet_data_organization_id",
    )

    # income_statement_data: via property
    _add_org_column(
        "income_statement_data",
        """
        UPDATE income_statement_data isd
        SET organization_id = p.organization_id
        FROM properties p
        WHERE isd.property_id = p.id AND p.organization_id IS NOT NULL
        """,
        "fk_income_statement_data_organization",
        "ix_income_statement_data_organization_id",
    )

    # cash_flow_data: via property
    _add_org_column(
        "cash_flow_data",
        """
        UPDATE cash_flow_data cfd
        SET organization_id = p.organization_id
        FROM properties p
        WHERE cfd.property_id = p.id AND p.organization_id IS NOT NULL
        """,
        "fk_cash_flow_data_organization",
        "ix_cash_flow_data_organization_id",
    )

    # rent_roll_data: via property
    _add_org_column(
        "rent_roll_data",
        """
        UPDATE rent_roll_data rrd
        SET organization_id = p.organization_id
        FROM properties p
        WHERE rrd.property_id = p.id AND p.organization_id IS NOT NULL
        """,
        "fk_rent_roll_data_organization",
        "ix_rent_roll_data_organization_id",
    )


def downgrade() -> None:
    _drop_org_column("rent_roll_data", "fk_rent_roll_data_organization", "ix_rent_roll_data_organization_id")
    _drop_org_column("cash_flow_data", "fk_cash_flow_data_organization", "ix_cash_flow_data_organization_id")
    _drop_org_column("income_statement_data", "fk_income_statement_data_organization", "ix_income_statement_data_organization_id")
    _drop_org_column("balance_sheet_data", "fk_balance_sheet_data_organization", "ix_balance_sheet_data_organization_id")
    _drop_org_column("validation_results", "fk_validation_results_organization", "ix_validation_results_organization_id")
