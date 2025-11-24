"""Add extraction coordinates for PDF source navigation

Revision ID: 20251123_coords
Revises: 20251114_risk_mgmt
Create Date: 2025-11-23 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251123_coords'
down_revision = '20251112_0001'  # Point to existing head
branch_labels = None
depends_on = None


def upgrade():
    # Add extraction coordinates to balance_sheet_data
    op.add_column('balance_sheet_data', sa.Column('extraction_x0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('extraction_y0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('extraction_x1', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('extraction_y1', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('line_number', sa.Integer(), nullable=True))
    
    # Add extraction coordinates to income_statement_data
    op.add_column('income_statement_data', sa.Column('extraction_x0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('income_statement_data', sa.Column('extraction_y0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('income_statement_data', sa.Column('extraction_x1', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('income_statement_data', sa.Column('extraction_y1', sa.DECIMAL(10, 2), nullable=True))
    
    # Add extraction coordinates to rent_roll_data
    op.add_column('rent_roll_data', sa.Column('page_number', sa.Integer(), nullable=True))
    op.add_column('rent_roll_data', sa.Column('extraction_x0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('rent_roll_data', sa.Column('extraction_y0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('rent_roll_data', sa.Column('extraction_x1', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('rent_roll_data', sa.Column('extraction_y1', sa.DECIMAL(10, 2), nullable=True))
    
    # Add extraction coordinates to cash_flow_data
    op.add_column('cash_flow_data', sa.Column('extraction_x0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('cash_flow_data', sa.Column('extraction_y0', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('cash_flow_data', sa.Column('extraction_x1', sa.DECIMAL(10, 2), nullable=True))
    op.add_column('cash_flow_data', sa.Column('extraction_y1', sa.DECIMAL(10, 2), nullable=True))


def downgrade():
    # Remove extraction coordinates from cash_flow_data
    op.drop_column('cash_flow_data', 'extraction_y1')
    op.drop_column('cash_flow_data', 'extraction_x1')
    op.drop_column('cash_flow_data', 'extraction_y0')
    op.drop_column('cash_flow_data', 'extraction_x0')
    
    # Remove extraction coordinates from rent_roll_data
    op.drop_column('rent_roll_data', 'extraction_y1')
    op.drop_column('rent_roll_data', 'extraction_x1')
    op.drop_column('rent_roll_data', 'extraction_y0')
    op.drop_column('rent_roll_data', 'extraction_x0')
    op.drop_column('rent_roll_data', 'page_number')
    
    # Remove extraction coordinates from income_statement_data
    op.drop_column('income_statement_data', 'extraction_y1')
    op.drop_column('income_statement_data', 'extraction_x1')
    op.drop_column('income_statement_data', 'extraction_y0')
    op.drop_column('income_statement_data', 'extraction_x0')
    
    # Remove extraction coordinates from balance_sheet_data
    op.drop_column('balance_sheet_data', 'line_number')
    op.drop_column('balance_sheet_data', 'extraction_y1')
    op.drop_column('balance_sheet_data', 'extraction_x1')
    op.drop_column('balance_sheet_data', 'extraction_y0')
    op.drop_column('balance_sheet_data', 'extraction_x0')

