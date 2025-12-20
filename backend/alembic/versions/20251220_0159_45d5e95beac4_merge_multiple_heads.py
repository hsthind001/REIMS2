"""Merge multiple heads

Revision ID: 45d5e95beac4
Revises: 20250115_document_chunks, 20251108_1306, 20251114_risk_mgmt, XXXX_add_pgvector, add_hallucination_review
Create Date: 2025-12-20 01:59:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45d5e95beac4'
down_revision: Union[str, Sequence[str], None] = ('20250115_document_chunks', '20251108_1306', '20251114_risk_mgmt', 'XXXX_add_pgvector', 'add_hallucination_review')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Merge multiple migration heads - no schema changes needed."""
    pass


def downgrade() -> None:
    """Merge downgrade - no operations needed."""
    pass

