"""Add extraction_runs table and extraction_run_id to document_uploads (Multi-LLM Master JSON)

Revision ID: 20260131_0001
Revises: 20260130_0010
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260131_0001"
down_revision = "20260130_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Create table only if not exists (idempotent)
    if not conn.dialect.has_table(conn, "extraction_runs"):
        op.create_table(
            "extraction_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(36), nullable=False, index=True),
            sa.Column("document_upload_id", sa.Integer(), sa.ForeignKey("document_uploads.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("extraction_log_id", sa.Integer(), sa.ForeignKey("extraction_logs.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("master_json", JSONB, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        # Use IF NOT EXISTS for index (idempotent)
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_extraction_runs_run_id ON extraction_runs (run_id)")

    # Add column to document_uploads only if not exists
    from sqlalchemy import inspect
    insp = inspect(conn)
    if "document_uploads" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("document_uploads")]
        if "extraction_run_id" not in cols:
            op.add_column(
                "document_uploads",
                sa.Column("extraction_run_id", sa.Integer(), sa.ForeignKey("extraction_runs.id", ondelete="SET NULL"), nullable=True, index=True),
            )


def downgrade() -> None:
    op.drop_column("document_uploads", "extraction_run_id")
    op.drop_index("ix_extraction_runs_run_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")
