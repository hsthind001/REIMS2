"""Merge heads

Revision ID: 20251225_0010
Revises: 20251225_0009
Create Date: 2025-12-25 20:00:00.000000

Merge two parallel migration branches
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251225_0010'
down_revision = '20251225_0009'
branch_labels = None
depends_on = None


def upgrade():
    """Merge - no changes needed"""
    pass


def downgrade():
    """Merge - no changes needed"""
    pass
