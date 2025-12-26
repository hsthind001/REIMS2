"""Add market intelligence tables

Revision ID: 20251225_0009
Revises: 20251225_0008
Create Date: 2025-12-25 10:00:00.000000

Creates tables for comprehensive market intelligence:
- market_intelligence: Store demographics, economic indicators, forecasts, ESG, etc.
- market_data_lineage: Audit trail for external data sources
- forecast_models: Store trained ML models for predictions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251225_0009'
down_revision = '20251225_0008'
branch_labels = None
depends_on = None


def upgrade():
    """Create market intelligence tables"""

    # Create market_intelligence table
    op.create_table(
        'market_intelligence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),

        # JSONB data fields
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Census demographics data with lineage'),
        sa.Column('economic_indicators', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='FRED economic indicators with lineage'),
        sa.Column('location_intelligence', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Walkability, transit, amenities, crime, schools'),
        sa.Column('esg_assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Environmental, Social, Governance risk scores'),
        sa.Column('forecasts', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Predictive forecasts (rent, occupancy, cap rate, value)'),
        sa.Column('competitive_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Submarket positioning and competitive threats'),
        sa.Column('comparables', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Comparable properties analysis with adjustments'),
        sa.Column('ai_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='AI-generated SWOT insights with confidence scores'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now(), nullable=False),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last time data was refreshed from external sources'),

        # Refresh metadata
        sa.Column('refresh_status', sa.String(length=50), nullable=True,
                  comment="'success', 'partial', 'failure'"),
        sa.Column('refresh_error', sa.Text(), nullable=True,
                  comment='Error message from last refresh attempt'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),

        comment='Comprehensive market intelligence data for properties'
    )

    # Create indexes for market_intelligence
    op.create_index('idx_market_intelligence_property', 'market_intelligence', ['property_id'])
    op.create_index('idx_market_intelligence_updated', 'market_intelligence', ['updated_at'])
    op.create_index('idx_market_intelligence_last_refreshed', 'market_intelligence', ['last_refreshed_at'])

    # Create market_data_lineage table
    op.create_table(
        'market_data_lineage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),

        # Source information
        sa.Column('data_source', sa.String(length=100), nullable=False,
                  comment='Data source name (census_acs5, fred, bls, hud, nominatim, osm, etc.)'),
        sa.Column('endpoint', sa.String(length=255), nullable=True,
                  comment='API endpoint used'),
        sa.Column('data_category', sa.String(length=50), nullable=False,
                  comment='Category (demographics, economic, location, esg, forecast, competitive, comparables, insights)'),

        # Data vintage and timing
        sa.Column('data_vintage', sa.String(length=20), nullable=True,
                  comment="Data vintage/year (e.g., '2021', '2024-Q3', '2024-11')"),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('data_as_of_date', sa.DateTime(timezone=True), nullable=True,
                  comment='Date the data represents'),

        # Quality metrics
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True,
                  comment='Confidence score (0-100) for this data'),
        sa.Column('quality_score', sa.Numeric(5, 2), nullable=True,
                  comment='Data quality score (0-100) based on completeness, accuracy, timeliness'),
        sa.Column('completeness_pct', sa.Numeric(5, 2), nullable=True,
                  comment='Percentage of expected fields that were populated'),

        # Status tracking
        sa.Column('fetch_status', sa.String(length=20), nullable=False,
                  comment="'success', 'partial', 'failure'"),
        sa.Column('error_message', sa.Text(), nullable=True,
                  comment='Error message if fetch failed'),
        sa.Column('records_fetched', sa.Integer(), nullable=True,
                  comment='Number of records/data points fetched'),

        # Performance metrics
        sa.Column('response_time_ms', sa.Integer(), nullable=True,
                  comment='API response time in milliseconds'),
        sa.Column('cache_hit', sa.Boolean(), server_default=sa.false(), nullable=True,
                  comment='Whether data was served from cache'),

        # Data snapshot
        sa.Column('data_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Snapshot of fetched data for audit purposes'),

        # Metadata
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Additional metadata about the data pull'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),

        comment='Data lineage and audit trail for market intelligence sources'
    )

    # Create indexes for market_data_lineage
    op.create_index('idx_market_data_lineage_property', 'market_data_lineage', ['property_id'])
    op.create_index('idx_market_data_lineage_source', 'market_data_lineage', ['data_source'])
    op.create_index('idx_market_data_lineage_category', 'market_data_lineage', ['data_category'])
    op.create_index('idx_market_data_lineage_fetched', 'market_data_lineage', ['fetched_at'])
    op.create_index('idx_market_data_lineage_status', 'market_data_lineage', ['fetch_status'])
    op.create_index('idx_market_data_lineage_property_category', 'market_data_lineage',
                    ['property_id', 'data_category'])

    # Create forecast_models table
    op.create_table(
        'forecast_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True,
                  comment='Property-specific model (NULL for market-wide models)'),

        # Model information
        sa.Column('model_type', sa.String(length=50), nullable=False,
                  comment='Model type (prophet, arima, xgboost, lstm, ensemble)'),
        sa.Column('forecast_target', sa.String(length=50), nullable=False,
                  comment='Forecast target (rent, occupancy, cap_rate, value, expenses)'),
        sa.Column('forecast_horizon_months', sa.Integer(), nullable=False,
                  comment='Forecast horizon in months'),

        # Model artifacts
        sa.Column('model_artifact', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Serialized model or reference to storage location'),
        sa.Column('model_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Model hyperparameters and configuration'),

        # Training information
        sa.Column('training_data_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_data_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_sample_size', sa.Integer(), nullable=True,
                  comment='Number of training samples'),

        # Performance metrics
        sa.Column('r_squared', sa.Numeric(5, 4), nullable=True,
                  comment='R-squared (regression models)'),
        sa.Column('mae', sa.Numeric(10, 2), nullable=True,
                  comment='Mean Absolute Error'),
        sa.Column('rmse', sa.Numeric(10, 2), nullable=True,
                  comment='Root Mean Squared Error'),
        sa.Column('mape', sa.Numeric(5, 2), nullable=True,
                  comment='Mean Absolute Percentage Error'),
        sa.Column('accuracy', sa.Numeric(5, 4), nullable=True,
                  comment='Accuracy (classification models)'),

        # Cross-validation results
        sa.Column('cv_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Cross-validation scores'),
        sa.Column('cv_mean', sa.Numeric(10, 4), nullable=True,
                  comment='Mean cross-validation score'),
        sa.Column('cv_std', sa.Numeric(10, 4), nullable=True,
                  comment='Standard deviation of CV scores'),

        # Feature importance
        sa.Column('feature_importance', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Feature importance scores'),

        # Versioning
        sa.Column('version', sa.String(length=20), nullable=True,
                  comment="Model version (e.g., 'v1.0.0')"),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=True,
                  comment='Whether this model is actively used'),
        sa.Column('superseded_by_id', sa.Integer(), nullable=True,
                  comment='ID of model that replaced this one'),

        # Timestamps
        sa.Column('trained_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last time this model was used for prediction'),

        # Metadata
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Additional metadata'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['forecast_models.id']),

        comment='Trained forecasting models with performance tracking'
    )

    # Create indexes for forecast_models
    op.create_index('idx_forecast_models_property', 'forecast_models', ['property_id'])
    op.create_index('idx_forecast_models_type_target', 'forecast_models', ['model_type', 'forecast_target'])
    op.create_index('idx_forecast_models_active', 'forecast_models', ['is_active'])
    op.create_index('idx_forecast_models_trained_at', 'forecast_models', ['trained_at'])


def downgrade():
    """Drop market intelligence tables"""
    op.drop_index('idx_forecast_models_trained_at', table_name='forecast_models')
    op.drop_index('idx_forecast_models_active', table_name='forecast_models')
    op.drop_index('idx_forecast_models_type_target', table_name='forecast_models')
    op.drop_index('idx_forecast_models_property', table_name='forecast_models')
    op.drop_table('forecast_models')

    op.drop_index('idx_market_data_lineage_property_category', table_name='market_data_lineage')
    op.drop_index('idx_market_data_lineage_status', table_name='market_data_lineage')
    op.drop_index('idx_market_data_lineage_fetched', table_name='market_data_lineage')
    op.drop_index('idx_market_data_lineage_category', table_name='market_data_lineage')
    op.drop_index('idx_market_data_lineage_source', table_name='market_data_lineage')
    op.drop_index('idx_market_data_lineage_property', table_name='market_data_lineage')
    op.drop_table('market_data_lineage')

    op.drop_index('idx_market_intelligence_last_refreshed', table_name='market_intelligence')
    op.drop_index('idx_market_intelligence_updated', table_name='market_intelligence')
    op.drop_index('idx_market_intelligence_property', table_name='market_intelligence')
    op.drop_table('market_intelligence')
