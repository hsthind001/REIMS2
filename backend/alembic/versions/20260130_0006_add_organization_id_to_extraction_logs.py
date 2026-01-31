"""Add organization_id to extraction_logs (E2-S3)

Revision ID: 20260130_0006
Revises: 20260130_0005
Create Date: 2026-01-30

Part of tenant isolation - extraction_logs can be scoped by org.
Backfill from document_uploads (upload.extraction_id -> extraction_log).
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0006"
down_revision = "20260130_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extraction_logs",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_extraction_logs_organization",
        "extraction_logs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        UPDATE extraction_logs el
        SET organization_id = du.organization_id
        FROM document_uploads du
        WHERE du.extraction_id = el.id AND du.organization_id IS NOT NULL
    """)
    op.create_index(
        "ix_extraction_logs_organization_id",
        "extraction_logs",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_logs_organization_id", table_name="extraction_logs")
    op.drop_constraint(
        "fk_extraction_logs_organization",
        "extraction_logs",
        type_="foreignkey",
    )
    op.drop_column("extraction_logs", "organization_id")
