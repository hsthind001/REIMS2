"""Add Forensic Reconciliation Tables

Revision ID: 20251223_0001
Revises: 20251222_0005
Create Date: 2025-12-23 16:40:00.000000

Creates tables for forensic financial document reconciliation:
- forensic_reconciliation_sessions: Tracks reconciliation sessions
- forensic_matches: Stores matches between documents across all 5 types
- forensic_discrepancies: Tracks discrepancies requiring resolution
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251223_0001'
down_revision = '20251222_0005'
branch_labels = None
depends_on = None


def upgrade():
    """Create forensic reconciliation tables"""
    
    # 1. Create forensic_reconciliation_sessions table
    op.create_table(
        'forensic_reconciliation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Foreign Keys
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('auditor_id', sa.Integer(), nullable=True),
        
        # Session Metadata
        sa.Column('session_type', sa.String(50), nullable=False, comment='full_reconciliation, cross_document, specific_match'),
        sa.Column('status', sa.String(50), nullable=False, server_default='in_progress', comment='in_progress, pending_review, approved, rejected'),
        
        # Timestamps
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Summary Statistics (JSONB)
        sa.Column('summary', postgresql.JSONB(), nullable=True, comment='{total_matches, exact_matches, fuzzy_matches, inferred_matches, discrepancies}'),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['auditor_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # 2. Create forensic_matches table
    op.create_table(
        'forensic_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        
        # Source Document Information
        sa.Column('source_document_type', sa.String(50), nullable=False, comment='balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement'),
        sa.Column('source_table_name', sa.String(100), nullable=False, comment='balance_sheet_data, income_statement_data, etc.'),
        sa.Column('source_record_id', sa.Integer(), nullable=False),
        sa.Column('source_account_code', sa.String(50), nullable=True),
        sa.Column('source_account_name', sa.String(255), nullable=True),
        sa.Column('source_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('source_field_name', sa.String(100), nullable=True, comment='amount, period_amount, etc.'),
        
        # Target Document Information
        sa.Column('target_document_type', sa.String(50), nullable=False),
        sa.Column('target_table_name', sa.String(100), nullable=False),
        sa.Column('target_record_id', sa.Integer(), nullable=False),
        sa.Column('target_account_code', sa.String(50), nullable=True),
        sa.Column('target_account_name', sa.String(255), nullable=True),
        sa.Column('target_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('target_field_name', sa.String(100), nullable=True),
        
        # Matching Metadata
        sa.Column('match_type', sa.String(50), nullable=False, comment='exact, fuzzy, inferred, calculated'),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=False, comment='0-100'),
        sa.Column('amount_difference', sa.Numeric(15, 2), nullable=True),
        sa.Column('amount_difference_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('match_algorithm', sa.String(100), nullable=True, comment='exact_match, fuzzy_string, account_code_range, calculated_relationship'),
        
        # Relationship Type
        sa.Column('relationship_type', sa.String(100), nullable=True, comment='equality, sum, difference, calculation'),
        sa.Column('relationship_formula', sa.Text(), nullable=True, comment='e.g., BS.current_period_earnings = IS.net_income'),
        
        # Review Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', comment='pending, approved, rejected, modified'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('auditor_override', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auditor_override_reason', sa.Text(), nullable=True),
        
        # Audit Trail
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['forensic_reconciliation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Check constraints
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='check_confidence_score_range'),
    )
    
    # 3. Create forensic_discrepancies table
    op.create_table(
        'forensic_discrepancies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        
        # Discrepancy Details
        sa.Column('discrepancy_type', sa.String(100), nullable=False, comment='amount_mismatch, missing_source, missing_target, date_mismatch'),
        sa.Column('severity', sa.String(50), nullable=False, comment='critical, high, medium, low'),
        
        # Values
        sa.Column('source_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('target_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('expected_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('actual_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('difference', sa.Numeric(15, 2), nullable=True),
        sa.Column('difference_percent', sa.Numeric(10, 4), nullable=True),
        
        # Description and Resolution
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('suggested_resolution', sa.Text(), nullable=True),
        
        # Resolution Status
        sa.Column('status', sa.String(50), nullable=False, server_default='open', comment='open, investigating, resolved, accepted'),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['forensic_reconciliation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['match_id'], ['forensic_matches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for forensic_reconciliation_sessions
    op.create_index('ix_forensic_reconciliation_sessions_property_id', 'forensic_reconciliation_sessions', ['property_id'])
    op.create_index('ix_forensic_reconciliation_sessions_period_id', 'forensic_reconciliation_sessions', ['period_id'])
    op.create_index('ix_forensic_reconciliation_sessions_auditor_id', 'forensic_reconciliation_sessions', ['auditor_id'])
    op.create_index('ix_forensic_reconciliation_sessions_status', 'forensic_reconciliation_sessions', ['status'])
    op.create_index('idx_forensic_reconciliation_sessions_property_period', 'forensic_reconciliation_sessions', ['property_id', 'period_id'])
    
    # Create indexes for forensic_matches
    op.create_index('idx_forensic_matches_session', 'forensic_matches', ['session_id'])
    op.create_index('idx_forensic_matches_source', 'forensic_matches', ['source_document_type', 'source_record_id'])
    op.create_index('idx_forensic_matches_target', 'forensic_matches', ['target_document_type', 'target_record_id'])
    op.create_index('idx_forensic_matches_status', 'forensic_matches', ['status', 'confidence_score'])
    op.create_index('idx_forensic_matches_match_type', 'forensic_matches', ['match_type', 'confidence_score'])
    
    # Create indexes for forensic_discrepancies
    op.create_index('idx_forensic_discrepancies_session', 'forensic_discrepancies', ['session_id'])
    op.create_index('idx_forensic_discrepancies_match', 'forensic_discrepancies', ['match_id'])
    op.create_index('idx_forensic_discrepancies_severity', 'forensic_discrepancies', ['severity', 'status'])
    op.create_index('idx_forensic_discrepancies_status', 'forensic_discrepancies', ['status', 'created_at'])


def downgrade():
    """Drop forensic reconciliation tables"""
    
    # Drop indexes for forensic_discrepancies
    op.drop_index('idx_forensic_discrepancies_status', table_name='forensic_discrepancies')
    op.drop_index('idx_forensic_discrepancies_severity', table_name='forensic_discrepancies')
    op.drop_index('idx_forensic_discrepancies_match', table_name='forensic_discrepancies')
    op.drop_index('idx_forensic_discrepancies_session', table_name='forensic_discrepancies')
    
    # Drop indexes for forensic_matches
    op.drop_index('idx_forensic_matches_match_type', table_name='forensic_matches')
    op.drop_index('idx_forensic_matches_status', table_name='forensic_matches')
    op.drop_index('idx_forensic_matches_target', table_name='forensic_matches')
    op.drop_index('idx_forensic_matches_source', table_name='forensic_matches')
    op.drop_index('idx_forensic_matches_session', table_name='forensic_matches')
    
    # Drop indexes for forensic_reconciliation_sessions
    op.drop_index('idx_forensic_reconciliation_sessions_property_period', table_name='forensic_reconciliation_sessions')
    op.drop_index('ix_forensic_reconciliation_sessions_status', table_name='forensic_reconciliation_sessions')
    op.drop_index('ix_forensic_reconciliation_sessions_auditor_id', table_name='forensic_reconciliation_sessions')
    op.drop_index('ix_forensic_reconciliation_sessions_period_id', table_name='forensic_reconciliation_sessions')
    op.drop_index('ix_forensic_reconciliation_sessions_property_id', table_name='forensic_reconciliation_sessions')
    
    # Drop tables (order matters due to foreign keys)
    op.drop_table('forensic_discrepancies')
    op.drop_table('forensic_matches')
    op.drop_table('forensic_reconciliation_sessions')

