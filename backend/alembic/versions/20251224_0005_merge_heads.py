"""Merge migration heads

Revision ID: 20251224_0005
Revises: 20251219_remove_old_cf_constraint, 20251224_0004
Create Date: 2025-12-24 19:00:00.000000

Merges the two migration heads:
- 20251219_remove_old_cf_constraint
- 20251224_0004 (alert workflow enhancements)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251224_0005'
down_revision = ('20251219_remove_old_cf_constraint', '20251224_0004')
branch_labels = None
depends_on = None


def upgrade():
    """Merge heads - no changes needed, just merging branches"""
    pass


def downgrade():
    """Merge heads - no changes needed, just merging branches"""
    pass

