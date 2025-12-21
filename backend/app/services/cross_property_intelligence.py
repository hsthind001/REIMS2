"""
Cross-Property Intelligence Service

Provides portfolio-level intelligence for anomaly detection:
- Cross-property benchmarking
- Portfolio-wide anomaly detection
- Property comparison and ranking
- Statistical benchmarks calculation
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import numpy as np
import pandas as pd
import logging

from app.models.property import Property
from app.models.anomaly_detection import AnomalyDetection
from app.models.cross_property_benchmark import CrossPropertyBenchmark
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.core.config import settings
from app.core.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class CrossPropertyIntelligenceService:
    """
    Cross-property intelligence service for portfolio-level anomaly detection.
    
    Features:
    - Portfolio benchmarking (mean, median, percentiles)
    - Cross-property anomaly detection
    - Property ranking and comparison
    - Statistical outlier detection across portfolio
    """
    
    def __init__(self, db: Session):
        """Initialize cross-property intelligence service."""
        self.db = db
        self.enabled = FeatureFlags.is_portfolio_benchmarks_enabled()
        self.min_properties = settings.BENCHMARK_MIN_PROPERTIES
    
    def calculate_benchmarks(
        self,
        account_code: str,
        metric_type: str = 'balance_sheet',  # 'balance_sheet', 'income_statement'
        period_id: Optional[int] = None
    ) -> CrossPropertyBenchmark:
        """
        Calculate portfolio benchmarks for a specific account/metric.
        
        Args:
            account_code: Account code to benchmark
            metric_type: Type of financial metric
            period_id: Optional specific period, otherwise uses latest
        
        Returns:
            CrossPropertyBenchmark object
        """
        if not self.enabled:
            logger.warning("Cross-property intelligence is disabled")
            return None
        
        # Get all properties
        properties = self.db.query(Property).filter(
            Property.is_active == True
        ).all()
        
        if len(properties) < self.min_properties:
            logger.warning(f"Insufficient properties for benchmarking: {len(properties)} < {self.min_properties}")
            return None
        
        property_ids = [p.id for p in properties]
        
        # Get data for the account across all properties
        if metric_type == 'balance_sheet':
            data_query = self.db.query(
                BalanceSheetData.property_id,
                BalanceSheetData.period_id,
                func.sum(BalanceSheetData.period_amount).label('value')
            ).filter(
                and_(
                    BalanceSheetData.account_code == account_code,
                    BalanceSheetData.property_id.in_(property_ids)
                )
            )
        elif metric_type == 'income_statement':
            data_query = self.db.query(
                IncomeStatementData.property_id,
                IncomeStatementData.period_id,
                func.sum(IncomeStatementData.period_amount).label('value')
            ).filter(
                and_(
                    IncomeStatementData.account_code == account_code,
                    IncomeStatementData.property_id.in_(property_ids)
                )
            )
        else:
            return None
        
        if period_id:
            data_query = data_query.filter(
                BalanceSheetData.period_id == period_id if metric_type == 'balance_sheet' 
                else IncomeStatementData.period_id == period_id
            )
        else:
            # Get latest period for each property
            # This is simplified - in production, you'd want to get the most recent common period
            pass
        
        data = data_query.group_by(
            BalanceSheetData.property_id if metric_type == 'balance_sheet' else IncomeStatementData.property_id,
            BalanceSheetData.period_id if metric_type == 'balance_sheet' else IncomeStatementData.period_id
        ).all()
        
        if len(data) < self.min_properties:
            return None
        
        values = [float(row.value) for row in data if row.value is not None]
        
        if not values:
            return None
        
        # Calculate statistics
        mean_value = np.mean(values)
        median_value = np.median(values)
        std_value = np.std(values)
        p25 = np.percentile(values, 25)
        p75 = np.percentile(values, 75)
        p90 = np.percentile(values, 90)
        p95 = np.percentile(values, 95)
        min_value = np.min(values)
        max_value = np.max(values)
        
        # Check if benchmark already exists
        existing = self.db.query(CrossPropertyBenchmark).filter(
            and_(
                CrossPropertyBenchmark.account_code == account_code,
                CrossPropertyBenchmark.metric_type == metric_type,
                CrossPropertyBenchmark.period_id == period_id
            )
        ).first()
        
        if existing:
            # Update existing benchmark
            existing.mean_value = mean_value
            existing.median_value = median_value
            existing.std_value = std_value
            existing.p25_value = p25
            existing.p75_value = p75
            existing.p90_value = p90
            existing.p95_value = p95
            existing.p5_value = p25  # Use p25 as approximation for p5 if not calculated
            existing.min_value = min_value
            existing.max_value = max_value
            existing.property_count = len(values)
            existing.last_calculated_at = datetime.utcnow()
            benchmark = existing
        else:
            # Create new benchmark
            benchmark = CrossPropertyBenchmark(
                account_code=account_code,
                metric_type=metric_type,
                period_id=period_id,
                mean_value=mean_value,
                median_value=median_value,
                std_value=std_value,
                p25_value=p25,
                p75_value=p75,
                p90_value=p90,
                p95_value=p95,
                p5_value=p25,  # Use p25 as approximation for p5 if not calculated
                min_value=min_value,
                max_value=max_value,
                property_count=len(values),
                last_calculated_at=datetime.utcnow()
            )
            self.db.add(benchmark)
        
        self.db.commit()
        self.db.refresh(benchmark)
        
        return benchmark
    
    def detect_cross_property_anomalies(
        self,
        property_id: int,
        account_code: str,
        value: float,
        metric_type: str = 'balance_sheet'
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if a value is anomalous compared to portfolio benchmarks.
        
        Args:
            property_id: Property ID
            account_code: Account code
            value: Value to check
            metric_type: Type of metric
        
        Returns:
            Dictionary with anomaly information if detected, None otherwise
        """
        if not self.enabled:
            return None
        
        # Get benchmark
        benchmark = self.db.query(CrossPropertyBenchmark).filter(
            and_(
                CrossPropertyBenchmark.account_code == account_code,
                CrossPropertyBenchmark.metric_type == metric_type
            )
        ).order_by(
            CrossPropertyBenchmark.last_calculated_at.desc()
        ).first()
        
        if not benchmark:
            # Calculate benchmark if it doesn't exist
            benchmark = self.calculate_benchmarks(account_code, metric_type)
            if not benchmark:
                return None
        
        # Check if value is outside normal range (beyond 2 standard deviations)
        z_score = (value - benchmark.mean_value) / benchmark.std_value if benchmark.std_value > 0 else 0
        
        if abs(z_score) > 2.0:
            return {
                'type': 'cross_property_outlier',
                'severity': 'high' if abs(z_score) > 3.0 else 'medium',
                'z_score': z_score,
                'portfolio_mean': benchmark.mean_value,
                'portfolio_median': benchmark.median_value,
                'portfolio_std': benchmark.std_value,
                'percentile_rank': self._calculate_percentile_rank(value, benchmark),
                'message': f"Value {value:,.2f} is {abs(z_score):.2f} standard deviations from portfolio mean ({benchmark.mean_value:,.2f})"
            }
        
        # Check if value is in extreme percentiles
        if value < benchmark.p5_value or value > benchmark.p95_value:
            return {
                'type': 'cross_property_extreme',
                'severity': 'medium',
                'percentile_rank': self._calculate_percentile_rank(value, benchmark),
                'portfolio_p5': benchmark.p5_value if hasattr(benchmark, 'p5_value') else benchmark.p25_value,
                'portfolio_p95': benchmark.p95_value,
                'message': f"Value {value:,.2f} is in extreme percentile compared to portfolio"
            }
        
        return None
    
    def _calculate_percentile_rank(
        self,
        value: float,
        benchmark: CrossPropertyBenchmark
    ) -> float:
        """
        Calculate percentile rank of value compared to benchmark.
        
        Args:
            value: Value to rank
            benchmark: Benchmark statistics
        
        Returns:
            Percentile rank (0-100)
        """
        # Simplified percentile calculation
        # In production, you'd use the actual distribution
        if value <= benchmark.p25_value:
            return 25.0 * (value / benchmark.p25_value) if benchmark.p25_value > 0 else 0.0
        elif value <= benchmark.median_value:
            return 25.0 + 25.0 * ((value - benchmark.p25_value) / (benchmark.median_value - benchmark.p25_value))
        elif value <= benchmark.p75_value:
            return 50.0 + 25.0 * ((value - benchmark.median_value) / (benchmark.p75_value - benchmark.median_value))
        elif value <= benchmark.p95_value:
            return 75.0 + 20.0 * ((value - benchmark.p75_value) / (benchmark.p95_value - benchmark.p75_value))
        else:
            return 95.0 + 5.0 * min(1.0, (value - benchmark.p95_value) / (benchmark.max_value - benchmark.p95_value))
    
    def get_property_ranking(
        self,
        property_id: int,
        account_code: str,
        metric_type: str = 'balance_sheet'
    ) -> Dict[str, Any]:
        """
        Get property ranking compared to portfolio for a specific metric.
        
        Args:
            property_id: Property ID
            account_code: Account code
            metric_type: Type of metric
        
        Returns:
            Dictionary with ranking information
        """
        benchmark = self.db.query(CrossPropertyBenchmark).filter(
            and_(
                CrossPropertyBenchmark.account_code == account_code,
                CrossPropertyBenchmark.metric_type == metric_type
            )
        ).order_by(
            CrossPropertyBenchmark.last_calculated_at.desc()
        ).first()
        
        if not benchmark:
            return None
        
        # Get property's value
        if metric_type == 'balance_sheet':
            property_data = self.db.query(BalanceSheetData).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.account_code == account_code
                )
            ).order_by(BalanceSheetData.id.desc()).first()
        else:
            property_data = self.db.query(IncomeStatementData).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.account_code == account_code
                )
            ).order_by(IncomeStatementData.id.desc()).first()
        
        if not property_data:
            return None
        
        value = float(property_data.period_amount or 0)
        percentile_rank = self._calculate_percentile_rank(value, benchmark)
        
        return {
            'property_id': property_id,
            'account_code': account_code,
            'value': value,
            'portfolio_mean': benchmark.mean_value,
            'portfolio_median': benchmark.median_value,
            'percentile_rank': percentile_rank,
            'ranking': 'top' if percentile_rank >= 90 else 'bottom' if percentile_rank <= 10 else 'middle',
            'property_count': benchmark.property_count
        }

