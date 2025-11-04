"""enhance_rent_roll_schema

Revision ID: 20251104_1008
Revises: a9a5178a1b3f
Create Date: 2025-11-04 10:08:00.000000

Add 6 new fields to rent_roll_data table for Template v2.0 compliance:
- tenancy_years: Years of occupancy calculated from lease start
- annual_recoveries_per_sf: CAM, taxes, insurance reimbursements per SF
- annual_misc_per_sf: Miscellaneous charges per SF
- is_gross_rent_row: Flag for gross rent calculation rows
- parent_row_id: Self-referencing FK to link gross rent rows to parent tenant
- notes: Extraction notes, validation flags, special conditions

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251104_1008'
down_revision = 'a9a5178a1b3f'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to rent_roll_data table
    op.add_column('rent_roll_data', sa.Column('tenancy_years', sa.DECIMAL(precision=5, scale=2), nullable=True))
    op.add_column('rent_roll_data', sa.Column('annual_recoveries_per_sf', sa.DECIMAL(precision=10, scale=4), nullable=True))
    op.add_column('rent_roll_data', sa.Column('annual_misc_per_sf', sa.DECIMAL(precision=10, scale=4), nullable=True))
    op.add_column('rent_roll_data', sa.Column('is_gross_rent_row', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('rent_roll_data', sa.Column('parent_row_id', sa.Integer(), nullable=True))
    op.add_column('rent_roll_data', sa.Column('notes', sa.Text(), nullable=True))
    
    # Create index on is_gross_rent_row for faster filtering
    op.create_index('ix_rent_roll_data_is_gross_rent_row', 'rent_roll_data', ['is_gross_rent_row'])
    
    # Create self-referencing foreign key for parent_row_id
    op.create_foreign_key(
        'fk_rent_roll_data_parent_row_id',
        'rent_roll_data', 
        'rent_roll_data',
        ['parent_row_id'], 
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on parent_row_id for faster joins
    op.create_index('ix_rent_roll_data_parent_row_id', 'rent_roll_data', ['parent_row_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_rent_roll_data_parent_row_id', 'rent_roll_data')
    op.drop_index('ix_rent_roll_data_is_gross_rent_row', 'rent_roll_data')
    
    # Drop foreign key
    op.drop_constraint('fk_rent_roll_data_parent_row_id', 'rent_roll_data', type_='foreignkey')
    
    # Drop columns
    op.drop_column('rent_roll_data', 'notes')
    op.drop_column('rent_roll_data', 'parent_row_id')
    op.drop_column('rent_roll_data', 'is_gross_rent_row')
    op.drop_column('rent_roll_data', 'annual_misc_per_sf')
    op.drop_column('rent_roll_data', 'annual_recoveries_per_sf')
    op.drop_column('rent_roll_data', 'tenancy_years')

