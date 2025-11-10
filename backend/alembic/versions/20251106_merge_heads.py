"""Merge multiple heads

Revision ID: merge_heads_2025
Revises: 20251104_1205, e5a2f9c1d8b3
Create Date: 2025-11-06 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_2025'
down_revision = ('20251104_1205', 'e5a2f9c1d8b3')
branch_labels = None
depends_on = None


def upgrade():
    """Merge two migration branches - no operations needed"""
    pass


def downgrade():
    """Merge downgrade - no operations needed"""
    pass

