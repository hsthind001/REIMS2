"""Add unique constraint for idempotent ingestion: (organization_id, property_id, period_id, document_type, file_hash) where file_hash not null (E5-S1)

Revision ID: 20260130_0010
Revises: 20260130_0009
Create Date: 2026-01-30

Prevents duplicate uploads of the same file within org/property/period/doc_type.
"""
from alembic import op


revision = "20260130_0010"
down_revision = "20260130_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index: same file hash in same org/property/period/doc_type = duplicate
    op.execute("""
        CREATE UNIQUE INDEX uq_document_uploads_org_prop_period_doctype_filehash
        ON document_uploads (organization_id, property_id, period_id, document_type, file_hash)
        WHERE file_hash IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_document_uploads_org_prop_period_doctype_filehash")
