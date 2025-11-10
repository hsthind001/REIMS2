"""add validation tracking to rent roll data

Revision ID: 20251106_1700
Revises: 20251106_1601
Create Date: 2025-11-06 17:00:00

Adds structured validation tracking for rent roll data:
- validation_score: Quality score from RentRollValidator (0-100)
- validation_flags_json: Structured validation flags as JSON
- field_extraction_quality: Per-field confidence scores
- critical_flag_count, warning_flag_count, info_flag_count: Flag severity counts

This enables transparent visibility of validation issues on the frontend,
supporting REIMS's 100% extraction quality objective.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DECIMAL, Integer, Text


# revision identifiers, used by Alembic.
revision = '20251106_1700'
down_revision = '20251106_1601'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add validation tracking fields to rent_roll_data"""
    
    # Add validation_score column
    op.add_column('rent_roll_data', 
        sa.Column('validation_score', DECIMAL(5, 2), nullable=True))
    
    # Add validation_flags_json column
    op.add_column('rent_roll_data', 
        sa.Column('validation_flags_json', Text, nullable=True))
    
    # Add field_extraction_quality column
    op.add_column('rent_roll_data', 
        sa.Column('field_extraction_quality', Text, nullable=True))
    
    # Add flag count columns
    op.add_column('rent_roll_data', 
        sa.Column('critical_flag_count', Integer, server_default='0', nullable=False))
    
    op.add_column('rent_roll_data', 
        sa.Column('warning_flag_count', Integer, server_default='0', nullable=False))
    
    op.add_column('rent_roll_data', 
        sa.Column('info_flag_count', Integer, server_default='0', nullable=False))
    
    # Backfill validation_score from extraction_confidence
    op.execute("""
        UPDATE rent_roll_data 
        SET validation_score = extraction_confidence
        WHERE validation_score IS NULL AND extraction_confidence IS NOT NULL
    """)
    
    # Create indexes for query performance
    op.create_index('idx_rr_critical_flag_count', 'rent_roll_data', ['critical_flag_count'])
    op.create_index('idx_rr_warning_flag_count', 'rent_roll_data', ['warning_flag_count'])


def downgrade() -> None:
    """Remove validation tracking fields from rent_roll_data"""
    
    # Drop indexes
    op.drop_index('idx_rr_warning_flag_count', 'rent_roll_data')
    op.drop_index('idx_rr_critical_flag_count', 'rent_roll_data')
    
    # Drop columns
    op.drop_column('rent_roll_data', 'info_flag_count')
    op.drop_column('rent_roll_data', 'warning_flag_count')
    op.drop_column('rent_roll_data', 'critical_flag_count')
    op.drop_column('rent_roll_data', 'field_extraction_quality')
    op.drop_column('rent_roll_data', 'validation_flags_json')
    op.drop_column('rent_roll_data', 'validation_score')

