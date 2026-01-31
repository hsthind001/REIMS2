"""Add organization_id to tenant tables (E2-S3)

Revision ID: 20260130_0001
Revises: 20260129_0004
Create Date: 2026-01-30

Adds organization_id to financial_periods and document_uploads for tenant isolation.
Strategy: add nullable -> backfill from property -> set NOT NULL -> add index.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0001"
down_revision = "20260129_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. financial_periods
    op.add_column(
        "financial_periods",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_financial_periods_organization",
        "financial_periods",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    # Backfill from property (only where property has organization_id)
    op.execute("""
        UPDATE financial_periods fp
        SET organization_id = p.organization_id
        FROM properties p
        WHERE fp.property_id = p.id AND p.organization_id IS NOT NULL AND fp.organization_id IS NULL
    """)
    op.create_index(
        "ix_financial_periods_organization_id",
        "financial_periods",
        ["organization_id"],
        unique=False,
    )

    # 2. document_uploads
    op.add_column(
        "document_uploads",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_uploads_organization",
        "document_uploads",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    # Backfill from property (only where property has organization_id)
    op.execute("""
        UPDATE document_uploads du
        SET organization_id = p.organization_id
        FROM properties p
        WHERE du.property_id = p.id AND p.organization_id IS NOT NULL AND du.organization_id IS NULL
    """)
    op.create_index(
        "ix_document_uploads_organization_id",
        "document_uploads",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_uploads_organization_id", table_name="document_uploads")
    op.drop_constraint("fk_document_uploads_organization", "document_uploads", type_="foreignkey")
    op.drop_column("document_uploads", "organization_id")

    op.drop_index("ix_financial_periods_organization_id", table_name="financial_periods")
    op.drop_constraint("fk_financial_periods_organization", "financial_periods", type_="foreignkey")
    op.drop_column("financial_periods", "organization_id")
