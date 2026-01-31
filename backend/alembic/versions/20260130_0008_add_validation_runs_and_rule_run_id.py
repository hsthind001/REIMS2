"""Add validation_runs table and validation_run_id to validation_results (E5-S3)

Revision ID: 20260130_0008
Revises: 20260130_0007
Create Date: 2026-01-30

Deterministic rule runs: track each run with inputs, version, timestamps.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0008"
down_revision = "20260130_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("upload_id", sa.Integer(), sa.ForeignKey("document_uploads.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rules_version_hash", sa.String(64), nullable=True, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rules_snapshot", sa.Text(), nullable=True),
        sa.Column("total_rules", sa.Integer(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=True),
        sa.Column("failed_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "validation_results",
        sa.Column("validation_run_id", sa.Integer(), sa.ForeignKey("validation_runs.id", ondelete="SET NULL"), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("validation_results", "validation_run_id")
    op.drop_table("validation_runs")
