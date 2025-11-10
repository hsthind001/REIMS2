"""allow_null_account_id_in_income_statement

Revision ID: a103c3096fdd
Revises: 20251106_1700
Create Date: 2025-11-06 12:31:48.478262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a103c3096fdd'
down_revision: Union[str, Sequence[str], None] = '20251106_1700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow NULL values in account_id column of income_statement_data table."""
    # Drop NOT NULL constraint to allow unmatched accounts
    op.alter_column('income_statement_data', 'account_id',
                   existing_type=sa.Integer(),
                   nullable=True)


def downgrade() -> None:
    """Restore NOT NULL constraint on account_id column."""
    # Note: This will fail if there are NULL values in the column
    op.alter_column('income_statement_data', 'account_id',
                   existing_type=sa.Integer(),
                   nullable=False)
