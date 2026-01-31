"""Add plan_id and quota fields to organizations (P2)

Revision ID: 20260130_0003
Revises: 20260130_0002
Create Date: 2026-01-30

Adds plan_id, documents_limit, storage_limit_gb for quota enforcement.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0003"
down_revision = "20260130_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("plan_id", sa.String(50), nullable=True))
    op.add_column("organizations", sa.Column("documents_limit", sa.Integer, nullable=True))
    op.add_column("organizations", sa.Column("storage_limit_gb", sa.Numeric(10, 2), nullable=True))
    op.add_column("organizations", sa.Column("documents_used", sa.Integer, nullable=True, server_default="0"))
    op.add_column("organizations", sa.Column("storage_used_bytes", sa.BigInteger, nullable=True, server_default="0"))


def downgrade() -> None:
    op.drop_column("organizations", "storage_used_bytes")
    op.drop_column("organizations", "documents_used")
    op.drop_column("organizations", "storage_limit_gb")
    op.drop_column("organizations", "documents_limit")
    op.drop_column("organizations", "plan_id")
