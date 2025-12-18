"""Budget and Forecast tables

Revision ID: 20251114_002
Revises: 20251114_next_level_features
Create Date: 2025-11-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251114_002'
down_revision = '20251114_next_level_features'
branch_labels = None
depends_on = None


def upgrade():
    # Create BudgetStatus enum (check if it exists first)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM pg_type 
        WHERE typname = 'budgetstatus'
    """))
    
    if result.scalar() == 0:
        # Use raw SQL to create enum with IF NOT EXISTS equivalent
        try:
            connection.execute(sa.text("""
                CREATE TYPE budgetstatus AS ENUM ('DRAFT', 'APPROVED', 'ACTIVE', 'REVISED', 'ARCHIVED')
            """))
        except Exception as e:
            # Enum might have been created by another migration
            if 'already exists' not in str(e).lower():
                raise
    
    # Get the enum type for use in table creation
    budget_status = postgresql.ENUM(
        'DRAFT', 'APPROVED', 'ACTIVE', 'REVISED', 'ARCHIVED',
        name='budgetstatus',
        create_type=False  # Don't try to create it, it already exists or was created above
    )

    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('financial_period_id', sa.Integer(), nullable=False),
        sa.Column('budget_name', sa.String(length=200), nullable=False),
        sa.Column('budget_year', sa.Integer(), nullable=False),
        sa.Column('budget_period_type', sa.String(length=20), nullable=False),
        sa.Column('status', budget_status, nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=200), nullable=True),
        sa.Column('account_category', sa.String(length=100), nullable=True),
        sa.Column('budgeted_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('tolerance_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('tolerance_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['financial_period_id'], ['financial_periods.id'], ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budgets_property_id'), 'budgets', ['property_id'], unique=False)
    op.create_index(op.f('ix_budgets_financial_period_id'), 'budgets', ['financial_period_id'], unique=False)
    op.create_index(op.f('ix_budgets_budget_year'), 'budgets', ['budget_year'], unique=False)
    op.create_index(op.f('ix_budgets_status'), 'budgets', ['status'], unique=False)
    op.create_index(op.f('ix_budgets_account_code'), 'budgets', ['account_code'], unique=False)

    # Create forecasts table
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('financial_period_id', sa.Integer(), nullable=False),
        sa.Column('forecast_name', sa.String(length=200), nullable=False),
        sa.Column('forecast_year', sa.Integer(), nullable=False),
        sa.Column('forecast_period_type', sa.String(length=20), nullable=False),
        sa.Column('forecast_type', sa.String(length=50), nullable=False),
        sa.Column('status', budget_status, nullable=False),
        sa.Column('forecast_date', sa.DateTime(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=200), nullable=True),
        sa.Column('account_category', sa.String(length=100), nullable=True),
        sa.Column('forecasted_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('tolerance_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('tolerance_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('assumptions', sa.String(length=1000), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['financial_period_id'], ['financial_periods.id'], ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_forecasts_property_id'), 'forecasts', ['property_id'], unique=False)
    op.create_index(op.f('ix_forecasts_financial_period_id'), 'forecasts', ['financial_period_id'], unique=False)
    op.create_index(op.f('ix_forecasts_forecast_year'), 'forecasts', ['forecast_year'], unique=False)
    op.create_index(op.f('ix_forecasts_status'), 'forecasts', ['status'], unique=False)
    op.create_index(op.f('ix_forecasts_account_code'), 'forecasts', ['account_code'], unique=False)
    op.create_index(op.f('ix_forecasts_forecast_date'), 'forecasts', ['forecast_date'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_forecasts_forecast_date'), table_name='forecasts')
    op.drop_index(op.f('ix_forecasts_account_code'), table_name='forecasts')
    op.drop_index(op.f('ix_forecasts_status'), table_name='forecasts')
    op.drop_index(op.f('ix_forecasts_forecast_year'), table_name='forecasts')
    op.drop_index(op.f('ix_forecasts_financial_period_id'), table_name='forecasts')
    op.drop_index(op.f('ix_forecasts_property_id'), table_name='forecasts')
    op.drop_table('forecasts')

    op.drop_index(op.f('ix_budgets_account_code'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_status'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_budget_year'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_financial_period_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_property_id'), table_name='budgets')
    op.drop_table('budgets')

    # Drop BudgetStatus enum
    sa.Enum(name='budgetstatus').drop(op.get_bind())
