"""
Cross Property Benchmark Model

Stores portfolio statistical benchmarks for cross-property anomaly detection.
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class CrossPropertyBenchmark(Base):
    """
    Portfolio statistical benchmarks for anomaly detection.
    
    Calculates mean, median, std, and percentiles across properties
    to enable cross-property anomaly detection.
    """
    
    __tablename__ = "cross_property_benchmarks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Benchmark Identification
    account_code = Column(String(50), nullable=False, index=True)
    benchmark_period = Column(Date, nullable=False, index=True)  # Period for which benchmark is calculated
    property_group = Column(String(50), nullable=True, index=True)  # Property grouping (size, location, type)
    
    # Statistical Benchmarks
    portfolio_mean = Column(Numeric(15, 2), nullable=True)
    portfolio_median = Column(Numeric(15, 2), nullable=True)
    portfolio_std = Column(Numeric(15, 2), nullable=True)
    percentile_25 = Column(Numeric(15, 2), nullable=True)
    percentile_75 = Column(Numeric(15, 2), nullable=True)
    percentile_90 = Column(Numeric(15, 2), nullable=True)
    percentile_95 = Column(Numeric(15, 2), nullable=True)
    
    # Sample Info
    property_count = Column(Integer, nullable=False)  # Number of properties in benchmark
    property_ids = Column(JSONB, nullable=True)  # Array of property IDs included in benchmark
    
    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('account_code', 'benchmark_period', 'property_group', name='uq_benchmark_account_period_group'),
    )
    
    def __repr__(self):
        return f"<CrossPropertyBenchmark(id={self.id}, account_code='{self.account_code}', period={self.benchmark_period}, property_count={self.property_count})>"

