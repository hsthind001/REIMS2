"""Add organization_id to batch_reprocessing_jobs (E2-S3)

Revision ID: 20260130_0005
Revises: 20260130_0004
Create Date: 2026-01-30

For WebSocket/tenant isolation when subscribing to batch job status.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0005"
down_revision = "20260130_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "batch_reprocessing_jobs",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_batch_reprocessing_jobs_organization",
        "batch_reprocessing_jobs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_batch_reprocessing_jobs_organization_id",
        "batch_reprocessing_jobs",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_batch_reprocessing_jobs_organization_id", table_name="batch_reprocessing_jobs")
    op.drop_constraint(
        "fk_batch_reprocessing_jobs_organization",
        "batch_reprocessing_jobs",
        type_="foreignkey",
    )
    op.drop_column("batch_reprocessing_jobs", "organization_id")
