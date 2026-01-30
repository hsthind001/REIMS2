"""add escrow_document_links table (FA-MORT-4)

Revision ID: 20260129_0003
Revises: 20260129_0002
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa

revision = "20260129_0003"
down_revision = "20260129_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "escrow_document_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("document_upload_id", sa.Integer(), nullable=False),
        sa.Column("escrow_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["financial_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_upload_id"], ["document_uploads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "property_id", "period_id", "document_upload_id", "escrow_type",
            name="uq_escrow_link_prop_period_doc_type",
        ),
    )
    op.create_index(
        "ix_escrow_document_links_property_id", "escrow_document_links", ["property_id"]
    )
    op.create_index(
        "ix_escrow_document_links_period_id", "escrow_document_links", ["period_id"]
    )
    op.create_index(
        "ix_escrow_document_links_document_upload_id", "escrow_document_links", ["document_upload_id"]
    )
    op.create_index(
        "ix_escrow_document_links_escrow_type", "escrow_document_links", ["escrow_type"]
    )
    op.create_index(
        "ix_escrow_document_links_property_period_type",
        "escrow_document_links",
        ["property_id", "period_id", "escrow_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_escrow_document_links_property_period_type", table_name="escrow_document_links"
    )
    op.drop_index(
        "ix_escrow_document_links_escrow_type", table_name="escrow_document_links"
    )
    op.drop_index(
        "ix_escrow_document_links_document_upload_id", table_name="escrow_document_links"
    )
    op.drop_index(
        "ix_escrow_document_links_period_id", table_name="escrow_document_links"
    )
    op.drop_index(
        "ix_escrow_document_links_property_id", table_name="escrow_document_links"
    )
    op.drop_table("escrow_document_links")
