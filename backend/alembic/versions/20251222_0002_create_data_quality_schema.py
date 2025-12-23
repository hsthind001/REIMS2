"""Create Data Quality Schema

Revision ID: 20251222_0002
Revises: 20251222_0001
Create Date: 2025-12-22 00:02:00.000000

Creates data_quality_scores table for tracking data quality metrics:
- quality_index (0-100): Overall quality score
- completeness, consistency, timeliness, validity (0-100 each)
- extraction_confidence_avg, match_confidence_avg (0-1)
- unmatched_accounts_count, manual_corrections_count
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251222_0002'
down_revision = '20251222_0001'
branch_labels = None
depends_on = None


def upgrade():
    """Create data_quality_scores table"""
    
    op.create_table(
        'data_quality_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # References
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=False),
        
        # Quality Index (0-100)
        sa.Column('quality_index', sa.Numeric(5, 2), nullable=False),
        
        # Component Scores (0-100 each)
        sa.Column('completeness', sa.Numeric(5, 2), nullable=True),
        sa.Column('consistency', sa.Numeric(5, 2), nullable=True),
        sa.Column('timeliness', sa.Numeric(5, 2), nullable=True),
        sa.Column('validity', sa.Numeric(5, 2), nullable=True),
        
        # Extraction Metrics
        sa.Column('extraction_confidence_avg', sa.Numeric(5, 4), nullable=True),
        sa.Column('match_confidence_avg', sa.Numeric(5, 4), nullable=True),
        
        # Quality Indicators
        sa.Column('unmatched_accounts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('manual_corrections_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Metadata
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['document_uploads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        
        # Check constraints
        sa.CheckConstraint('quality_index >= 0 AND quality_index <= 100', name='check_quality_index_range'),
        sa.CheckConstraint('completeness >= 0 AND completeness <= 100', name='check_completeness_range'),
        sa.CheckConstraint('consistency >= 0 AND consistency <= 100', name='check_consistency_range'),
        sa.CheckConstraint('timeliness >= 0 AND timeliness <= 100', name='check_timeliness_range'),
        sa.CheckConstraint('validity >= 0 AND validity <= 100', name='check_validity_range'),
        sa.CheckConstraint('extraction_confidence_avg >= 0 AND extraction_confidence_avg <= 1', name='check_extraction_confidence_range'),
        sa.CheckConstraint('match_confidence_avg >= 0 AND match_confidence_avg <= 1', name='check_match_confidence_range'),
    )
    
    # Create indexes for performance
    op.create_index('ix_data_quality_document_id', 'data_quality_scores', ['document_id'])
    op.create_index('ix_data_quality_period_id', 'data_quality_scores', ['period_id'])
    op.create_index('ix_data_quality_property_id', 'data_quality_scores', ['property_id'])
    op.create_index('ix_data_quality_index', 'data_quality_scores', ['quality_index'])
    op.create_index('ix_data_quality_calculated_at', 'data_quality_scores', ['calculated_at'])
    
    # Composite index for common queries
    op.create_index('ix_data_quality_document_period', 'data_quality_scores', ['document_id', 'period_id'])


def downgrade():
    """Drop data_quality_scores table"""
    
    # Drop indexes
    op.drop_index('ix_data_quality_document_period', table_name='data_quality_scores')
    op.drop_index('ix_data_quality_calculated_at', table_name='data_quality_scores')
    op.drop_index('ix_data_quality_index', table_name='data_quality_scores')
    op.drop_index('ix_data_quality_property_id', table_name='data_quality_scores')
    op.drop_index('ix_data_quality_period_id', table_name='data_quality_scores')
    op.drop_index('ix_data_quality_document_id', table_name='data_quality_scores')
    
    # Drop table
    op.drop_table('data_quality_scores')

