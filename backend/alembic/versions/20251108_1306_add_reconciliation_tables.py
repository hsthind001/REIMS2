"""add_reconciliation_tables

Revision ID: 20251108_1306
Revises: (previous revision)
Create Date: 2025-11-08 13:06:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251108_1306'
down_revision = '20251107_1400'  # Points to cash flow template v1 tables
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create reconciliation_sessions table
    op.create_table(
        'reconciliation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_sessions_document_type'), 'reconciliation_sessions', ['document_type'], unique=False)
    op.create_index(op.f('ix_reconciliation_sessions_id'), 'reconciliation_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_reconciliation_sessions_period_id'), 'reconciliation_sessions', ['period_id'], unique=False)
    op.create_index(op.f('ix_reconciliation_sessions_property_id'), 'reconciliation_sessions', ['property_id'], unique=False)
    op.create_index(op.f('ix_reconciliation_sessions_status'), 'reconciliation_sessions', ['status'], unique=False)
    
    # Create reconciliation_differences table
    op.create_table(
        'reconciliation_differences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=True),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('pdf_value', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('db_value', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('difference', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('difference_percent', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('difference_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('needs_review', sa.Boolean(), nullable=True),
        sa.Column('flags', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['reconciliation_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_differences_account_code'), 'reconciliation_differences', ['account_code'], unique=False)
    op.create_index(op.f('ix_reconciliation_differences_difference_type'), 'reconciliation_differences', ['difference_type'], unique=False)
    op.create_index(op.f('ix_reconciliation_differences_id'), 'reconciliation_differences', ['id'], unique=False)
    op.create_index(op.f('ix_reconciliation_differences_session_id'), 'reconciliation_differences', ['session_id'], unique=False)
    op.create_index(op.f('ix_reconciliation_differences_status'), 'reconciliation_differences', ['status'], unique=False)
    
    # Create reconciliation_resolutions table
    op.create_table(
        'reconciliation_resolutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('difference_id', sa.Integer(), nullable=False),
        sa.Column('action_taken', sa.String(length=50), nullable=False),
        sa.Column('old_value', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('new_value', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['difference_id'], ['reconciliation_differences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_resolutions_difference_id'), 'reconciliation_resolutions', ['difference_id'], unique=False)
    op.create_index(op.f('ix_reconciliation_resolutions_id'), 'reconciliation_resolutions', ['id'], unique=False)
    
    # Check if users table exists (for foreign keys)
    connection = op.get_bind()
    users_result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'users'
    """))
    users_exists = users_result.scalar() > 0
    
    # Add reconciliation status fields to balance_sheet_data
    op.add_column('balance_sheet_data', sa.Column('reconciliation_status', sa.String(length=50), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('last_reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('balance_sheet_data', sa.Column('reconciled_by', sa.Integer(), nullable=True))
    
    # Only create foreign key if users table exists
    if users_exists:
        op.create_foreign_key('fk_balance_sheet_data_reconciled_by', 'balance_sheet_data', 'users', ['reconciled_by'], ['id'])
    op.create_index(op.f('ix_balance_sheet_data_reconciliation_status'), 'balance_sheet_data', ['reconciliation_status'], unique=False)
    
    # Add reconciliation status fields to income_statement_data
    op.add_column('income_statement_data', sa.Column('reconciliation_status', sa.String(length=50), nullable=True))
    op.add_column('income_statement_data', sa.Column('last_reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('income_statement_data', sa.Column('reconciled_by', sa.Integer(), nullable=True))
    
    # Only create foreign key if users table exists
    if users_exists:
        op.create_foreign_key('fk_income_statement_data_reconciled_by', 'income_statement_data', 'users', ['reconciled_by'], ['id'])
    op.create_index(op.f('ix_income_statement_data_reconciliation_status'), 'income_statement_data', ['reconciliation_status'], unique=False)
    
    # Add reconciliation status fields to cash_flow_data
    op.add_column('cash_flow_data', sa.Column('reconciliation_status', sa.String(length=50), nullable=True))
    op.add_column('cash_flow_data', sa.Column('last_reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cash_flow_data', sa.Column('reconciled_by', sa.Integer(), nullable=True))
    
    # Only create foreign key if users table exists
    if users_exists:
        op.create_foreign_key('fk_cash_flow_data_reconciled_by', 'cash_flow_data', 'users', ['reconciled_by'], ['id'])
    op.create_index(op.f('ix_cash_flow_data_reconciliation_status'), 'cash_flow_data', ['reconciliation_status'], unique=False)
    
    # Add reconciliation status fields to rent_roll_data
    op.add_column('rent_roll_data', sa.Column('reconciliation_status', sa.String(length=50), nullable=True))
    op.add_column('rent_roll_data', sa.Column('last_reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('rent_roll_data', sa.Column('reconciled_by', sa.Integer(), nullable=True))
    
    # Only create foreign key if users table exists
    if users_exists:
        op.create_foreign_key('fk_rent_roll_data_reconciled_by', 'rent_roll_data', 'users', ['reconciled_by'], ['id'])
    op.create_index(op.f('ix_rent_roll_data_reconciliation_status'), 'rent_roll_data', ['reconciliation_status'], unique=False)


def downgrade() -> None:
    # Remove reconciliation status fields from rent_roll_data
    op.drop_index(op.f('ix_rent_roll_data_reconciliation_status'), table_name='rent_roll_data')
    op.drop_constraint('fk_rent_roll_data_reconciled_by', 'rent_roll_data', type_='foreignkey')
    op.drop_column('rent_roll_data', 'reconciled_by')
    op.drop_column('rent_roll_data', 'last_reconciled_at')
    op.drop_column('rent_roll_data', 'reconciliation_status')
    
    # Remove reconciliation status fields from cash_flow_data
    op.drop_index(op.f('ix_cash_flow_data_reconciliation_status'), table_name='cash_flow_data')
    op.drop_constraint('fk_cash_flow_data_reconciled_by', 'cash_flow_data', type_='foreignkey')
    op.drop_column('cash_flow_data', 'reconciled_by')
    op.drop_column('cash_flow_data', 'last_reconciled_at')
    op.drop_column('cash_flow_data', 'reconciliation_status')
    
    # Remove reconciliation status fields from income_statement_data
    op.drop_index(op.f('ix_income_statement_data_reconciliation_status'), table_name='income_statement_data')
    op.drop_constraint('fk_income_statement_data_reconciled_by', 'income_statement_data', type_='foreignkey')
    op.drop_column('income_statement_data', 'reconciled_by')
    op.drop_column('income_statement_data', 'last_reconciled_at')
    op.drop_column('income_statement_data', 'reconciliation_status')
    
    # Remove reconciliation status fields from balance_sheet_data
    op.drop_index(op.f('ix_balance_sheet_data_reconciliation_status'), table_name='balance_sheet_data')
    op.drop_constraint('fk_balance_sheet_data_reconciled_by', 'balance_sheet_data', type_='foreignkey')
    op.drop_column('balance_sheet_data', 'reconciled_by')
    op.drop_column('balance_sheet_data', 'last_reconciled_at')
    op.drop_column('balance_sheet_data', 'reconciliation_status')
    
    # Drop reconciliation_resolutions table
    op.drop_index(op.f('ix_reconciliation_resolutions_id'), table_name='reconciliation_resolutions')
    op.drop_index(op.f('ix_reconciliation_resolutions_difference_id'), table_name='reconciliation_resolutions')
    op.drop_table('reconciliation_resolutions')
    
    # Drop reconciliation_differences table
    op.drop_index(op.f('ix_reconciliation_differences_status'), table_name='reconciliation_differences')
    op.drop_index(op.f('ix_reconciliation_differences_session_id'), table_name='reconciliation_differences')
    op.drop_index(op.f('ix_reconciliation_differences_id'), table_name='reconciliation_differences')
    op.drop_index(op.f('ix_reconciliation_differences_difference_type'), table_name='reconciliation_differences')
    op.drop_index(op.f('ix_reconciliation_differences_account_code'), table_name='reconciliation_differences')
    op.drop_table('reconciliation_differences')
    
    # Drop reconciliation_sessions table
    op.drop_index(op.f('ix_reconciliation_sessions_status'), table_name='reconciliation_sessions')
    op.drop_index(op.f('ix_reconciliation_sessions_property_id'), table_name='reconciliation_sessions')
    op.drop_index(op.f('ix_reconciliation_sessions_period_id'), table_name='reconciliation_sessions')
    op.drop_index(op.f('ix_reconciliation_sessions_id'), table_name='reconciliation_sessions')
    op.drop_index(op.f('ix_reconciliation_sessions_document_type'), table_name='reconciliation_sessions')
    op.drop_table('reconciliation_sessions')

