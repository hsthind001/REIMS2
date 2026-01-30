"""add covenant_thresholds table

Revision ID: 20260129_0001
Revises: 20260128_0001
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa

revision = "20260129_0001"
down_revision = "20260128_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "covenant_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("covenant_type", sa.String(50), nullable=False),
        sa.Column("threshold_value", sa.Numeric(15, 4), nullable=False),
        sa.Column("comparison_operator", sa.String(10), nullable=False, server_default=">="),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_covenant_thresholds_property_id", "covenant_thresholds", ["property_id"])
    op.create_index("ix_covenant_thresholds_covenant_type", "covenant_thresholds", ["covenant_type"])
    op.create_index("ix_covenant_thresholds_effective_date", "covenant_thresholds", ["effective_date"])
    op.create_index("ix_covenant_thresholds_is_active", "covenant_thresholds", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_covenant_thresholds_is_active", table_name="covenant_thresholds")
    op.drop_index("ix_covenant_thresholds_effective_date", table_name="covenant_thresholds")
    op.drop_index("ix_covenant_thresholds_covenant_type", table_name="covenant_thresholds")
    op.drop_index("ix_covenant_thresholds_property_id", table_name="covenant_thresholds")
    op.drop_table("covenant_thresholds")
