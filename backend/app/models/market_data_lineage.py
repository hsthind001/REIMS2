"""
Market Data Lineage Model

Tracks data provenance, quality, and refresh history for market intelligence data.
Provides audit trail for all external data sources.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime


class MarketDataLineage(Base):
    """
    Data lineage and audit trail for market intelligence.

    Tracks every data pull from external sources with:
    - Source identification
    - Data vintage/timestamp
    - Quality metrics
    - Refresh history
    - Error tracking
    """

    __tablename__ = "market_data_lineage"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Source information
    data_source = Column(
        String(100),
        nullable=False,
        comment="Data source name (census_acs5, fred, bls, hud, nominatim, osm, etc.)"
    )
    endpoint = Column(String(255), nullable=True, comment="API endpoint used")
    data_category = Column(
        String(50),
        nullable=False,
        comment="Category (demographics, economic, location, esg, forecast, competitive, comparables, insights)"
    )

    # Data vintage and timing
    data_vintage = Column(String(20), nullable=True, comment="Data vintage/year (e.g., '2021', '2024-Q3', '2024-11')")
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    data_as_of_date = Column(DateTime(timezone=True), nullable=True, comment="Date the data represents")

    # Quality metrics
    confidence_score = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Confidence score (0-100) for this data"
    )
    quality_score = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Data quality score (0-100) based on completeness, accuracy, timeliness"
    )
    completeness_pct = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage of expected fields that were populated"
    )

    # Status tracking
    fetch_status = Column(
        String(20),
        nullable=False,
        comment="'success', 'partial', 'failure'"
    )
    error_message = Column(Text, nullable=True, comment="Error message if fetch failed")
    records_fetched = Column(Integer, nullable=True, comment="Number of records/data points fetched")

    # Performance metrics
    response_time_ms = Column(Integer, nullable=True, comment="API response time in milliseconds")
    cache_hit = Column(Boolean, default=False, comment="Whether data was served from cache")

    # Data snapshot (for audit trail)
    data_snapshot = Column(
        JSONB,
        nullable=True,
        comment="Snapshot of fetched data for audit purposes (may be truncated for large datasets)"
    )

    # Metadata
    extra_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional metadata about the data pull (request params, filters, etc.)"
    )

    # Relationships
    property_obj = relationship("Property", back_populates="market_data_lineage")

    def __repr__(self):
        return f"<MarketDataLineage(id={self.id}, source={self.data_source}, category={self.data_category}, status={self.fetch_status})>"

    # Indexes
    __table_args__ = (
        Index('idx_market_data_lineage_property', 'property_id'),
        Index('idx_market_data_lineage_source', 'data_source'),
        Index('idx_market_data_lineage_category', 'data_category'),
        Index('idx_market_data_lineage_fetched', 'fetched_at'),
        Index('idx_market_data_lineage_status', 'fetch_status'),
        Index('idx_market_data_lineage_property_category', 'property_id', 'data_category'),
        {'comment': 'Data lineage and audit trail for market intelligence sources'}
    )


class ForecastModel(Base):
    """
    Stores trained forecasting models for reuse.

    Caches model artifacts to avoid retraining for every forecast.
    Tracks model performance and versioning.
    """

    __tablename__ = "forecast_models"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=True, comment="Property-specific model (NULL for market-wide models)")

    # Model information
    model_type = Column(
        String(50),
        nullable=False,
        comment="Model type (prophet, arima, xgboost, lstm, ensemble)"
    )
    forecast_target = Column(
        String(50),
        nullable=False,
        comment="Forecast target (rent, occupancy, cap_rate, value, expenses)"
    )
    forecast_horizon_months = Column(Integer, nullable=False, comment="Forecast horizon in months")

    # Model artifacts
    model_artifact = Column(
        JSONB,
        nullable=True,
        comment="Serialized model (for lightweight models) or reference to storage location"
    )
    model_parameters = Column(
        JSONB,
        nullable=True,
        comment="Model hyperparameters and configuration"
    )

    # Training information
    training_data_start_date = Column(DateTime(timezone=True), nullable=True)
    training_data_end_date = Column(DateTime(timezone=True), nullable=True)
    training_sample_size = Column(Integer, nullable=True, comment="Number of training samples")

    # Performance metrics
    r_squared = Column(Numeric(5, 4), nullable=True, comment="R-squared (regression models)")
    mae = Column(Numeric(10, 2), nullable=True, comment="Mean Absolute Error")
    rmse = Column(Numeric(10, 2), nullable=True, comment="Root Mean Squared Error")
    mape = Column(Numeric(5, 2), nullable=True, comment="Mean Absolute Percentage Error")
    accuracy = Column(Numeric(5, 4), nullable=True, comment="Accuracy (classification models)")

    # Cross-validation results
    cv_scores = Column(
        JSONB,
        nullable=True,
        comment="Cross-validation scores (array of scores for each fold)"
    )
    cv_mean = Column(Numeric(10, 4), nullable=True, comment="Mean cross-validation score")
    cv_std = Column(Numeric(10, 4), nullable=True, comment="Standard deviation of CV scores")

    # Feature importance
    feature_importance = Column(
        JSONB,
        nullable=True,
        comment="Feature importance scores (for tree-based models)"
    )

    # Versioning
    version = Column(String(20), nullable=True, comment="Model version (e.g., 'v1.0.0')")
    is_active = Column(Boolean, default=True, comment="Whether this model is actively used")
    superseded_by_id = Column(Integer, ForeignKey("forecast_models.id"), nullable=True, comment="ID of model that replaced this one")

    # Timestamps
    trained_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Last time this model was used for prediction")

    # Metadata
    extra_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional metadata (data sources used, preprocessing steps, etc.)"
    )

    # Relationships
    property_obj = relationship("Property", back_populates="forecast_models", foreign_keys=[property_id])
    superseded_by = relationship("ForecastModel", remote_side=[id], foreign_keys=[superseded_by_id])

    def __repr__(self):
        return f"<ForecastModel(id={self.id}, type={self.model_type}, target={self.forecast_target}, accuracy={self.accuracy})>"

    # Indexes
    __table_args__ = (
        Index('idx_forecast_models_property', 'property_id'),
        Index('idx_forecast_models_type_target', 'model_type', 'forecast_target'),
        Index('idx_forecast_models_active', 'is_active'),
        Index('idx_forecast_models_trained_at', 'trained_at'),
        {'comment': 'Trained forecasting models with performance tracking'}
    )
