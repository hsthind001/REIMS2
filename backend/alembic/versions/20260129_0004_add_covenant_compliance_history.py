"""add covenant_compliance_history table

Revision ID: 20260129_0004
Revises: 20260129_0003
Create Date: 2026-01-29

Stores per-period covenant check results (DSCR, LTV, etc.) for dashboard and audit.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260129_0004"
down_revision = "20260129_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "covenant_compliance_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("covenant_type", sa.String(50), nullable=False),
        sa.Column("rule_id", sa.String(20), nullable=False),
        sa.Column("calculated_value", sa.Numeric(15, 4), nullable=True),
        sa.Column("threshold_value", sa.Numeric(15, 4), nullable=True),
        sa.Column("is_compliant", sa.Boolean(), nullable=False),
        sa.Column("variance", sa.Numeric(15, 4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["financial_periods.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_covenant_compliance_history_property_id",
        "covenant_compliance_history",
        ["property_id"],
    )
    op.create_index(
        "ix_covenant_compliance_history_period_id",
        "covenant_compliance_history",
        ["period_id"],
    )
    op.create_index(
        "ix_covenant_compliance_history_covenant_type",
        "covenant_compliance_history",
        ["covenant_type"],
    )
    op.create_index(
        "ix_covenant_compliance_history_property_period",
        "covenant_compliance_history",
        ["property_id", "period_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_covenant_compliance_history_property_period",
        table_name="covenant_compliance_history",
    )
    op.drop_index(
        "ix_covenant_compliance_history_covenant_type",
        table_name="covenant_compliance_history",
    )
    op.drop_index(
        "ix_covenant_compliance_history_period_id",
        table_name="covenant_compliance_history",
    )
    op.drop_index(
        "ix_covenant_compliance_history_property_id",
        table_name="covenant_compliance_history",
    )
    op.drop_table("covenant_compliance_history")
