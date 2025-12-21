"""
Portfolio Analytics API

Endpoints for portfolio-wide analytics and benchmarking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.cross_property_intelligence import CrossPropertyIntelligenceService
from app.models.property import Property
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio-analytics", tags=["portfolio-analytics"])


# Response Models
class BenchmarkCalculationResponse(BaseModel):
    """Response for benchmark calculation."""
    success: bool
    benchmarks_created: int
    account_codes: List[str]
    message: str


class PortfolioAnalyticsResponse(BaseModel):
    """Portfolio-wide analytics."""
    total_properties: int
    total_anomalies: int
    anomalies_by_severity: Dict[str, int]
    top_accounts_with_anomalies: List[Dict[str, Any]]
    average_anomalies_per_property: float
    properties_with_most_anomalies: List[Dict[str, Any]]


class PropertyComparisonResponse(BaseModel):
    """Property comparison to portfolio."""
    property_id: int
    property_name: str
    property_code: str
    account_code: str
    property_value: Optional[float]
    portfolio_mean: Optional[float]
    portfolio_median: Optional[float]
    portfolio_std: Optional[float]
    percentile_rank: Optional[float]
    z_score: Optional[float]
    comparison_status: str  # 'above_average', 'average', 'below_average'


class OutlierResponse(BaseModel):
    """Portfolio outlier information."""
    property_id: int
    property_name: str
    property_code: str
    account_code: str
    value: float
    outlier_type: str  # 'high', 'low', 'extreme'
    z_score: float
    percentile_rank: float
    portfolio_mean: float
    portfolio_std: float


@router.post("/calculate-benchmarks", response_model=BenchmarkCalculationResponse)
async def calculate_benchmarks(
    account_codes: Optional[List[str]] = Query(None, description="Specific account codes to calculate (all if None)"),
    metric_type: str = Query("balance_sheet", description="Metric type: balance_sheet, income_statement"),
    property_group: Optional[str] = Query(None, description="Property group filter (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate portfolio benchmarks for specified accounts.
    
    Creates or updates CrossPropertyBenchmark records with statistical data
    (mean, median, std, percentiles) for portfolio-wide comparison.
    
    Args:
        account_codes: List of account codes to calculate benchmarks for (all if None)
        metric_type: Type of financial metric
        property_group: Optional property group filter
    
    Returns:
        Number of benchmarks created/updated
    """
    try:
        cross_property_service = CrossPropertyIntelligenceService(db)
        
        if not cross_property_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portfolio benchmarks are not enabled"
            )
        
        # If no account codes specified, get all unique account codes from properties
        if not account_codes:
            # Get all account codes from the specified metric type
            if metric_type == 'balance_sheet':
                from app.models.balance_sheet_data import BalanceSheetData
                account_codes = db.query(BalanceSheetData.account_code).distinct().all()
                account_codes = [ac[0] for ac in account_codes]
            elif metric_type == 'income_statement':
                from app.models.income_statement_data import IncomeStatementData
                account_codes = db.query(IncomeStatementData.account_code).distinct().all()
                account_codes = [ac[0] for ac in account_codes]
            else:
                account_codes = []
        
        benchmarks_created = 0
        
        for account_code in account_codes:
            try:
                benchmark = cross_property_service.calculate_benchmarks(
                    account_code=account_code,
                    metric_type=metric_type,
                    property_group=property_group
                )
                if benchmark:
                    benchmarks_created += 1
            except Exception as e:
                logger.warning(f"Failed to calculate benchmark for {account_code}: {e}")
                continue
        
        return BenchmarkCalculationResponse(
            success=True,
            benchmarks_created=benchmarks_created,
            account_codes=account_codes[:10],  # Return first 10 for display
            message=f"Successfully calculated {benchmarks_created} benchmarks"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating benchmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate benchmarks: {str(e)}"
        )


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
async def get_portfolio_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get portfolio-wide analytics and statistics.
    
    Returns:
        Comprehensive portfolio analytics including:
        - Total properties and anomalies
        - Anomalies by severity
        - Top accounts with anomalies
        - Properties with most anomalies
    """
    try:
        from app.models.anomaly_detection import AnomalyDetection
        from sqlalchemy import func
        
        # Get total properties
        total_properties = db.query(Property).filter(Property.is_active == True).count()
        
        # Get total anomalies
        total_anomalies = db.query(AnomalyDetection).filter(
            AnomalyDetection.context_suppressed == False
        ).count()
        
        # Get anomalies by severity
        severity_counts = db.query(
            AnomalyDetection.severity,
            func.count(AnomalyDetection.id).label('count')
        ).filter(
            AnomalyDetection.context_suppressed == False
        ).group_by(AnomalyDetection.severity).all()
        
        anomalies_by_severity = {severity: count for severity, count in severity_counts}
        
        # Get top accounts with anomalies
        top_accounts = db.query(
            AnomalyDetection.account_code,
            func.count(AnomalyDetection.id).label('anomaly_count')
        ).filter(
            AnomalyDetection.context_suppressed == False
        ).group_by(AnomalyDetection.account_code).order_by(
            func.count(AnomalyDetection.id).desc()
        ).limit(10).all()
        
        top_accounts_with_anomalies = [
            {
                "account_code": account_code,
                "anomaly_count": count
            }
            for account_code, count in top_accounts
        ]
        
        # Get properties with most anomalies
        properties_with_anomalies = db.query(
            AnomalyDetection.property_id,
            func.count(AnomalyDetection.id).label('anomaly_count')
        ).filter(
            AnomalyDetection.context_suppressed == False
        ).group_by(AnomalyDetection.property_id).order_by(
            func.count(AnomalyDetection.id).desc()
        ).limit(10).all()
        
        properties_with_most_anomalies = []
        for property_id, count in properties_with_anomalies:
            property_obj = db.query(Property).filter(Property.id == property_id).first()
            if property_obj:
                properties_with_most_anomalies.append({
                    "property_id": property_id,
                    "property_name": property_obj.property_name,
                    "property_code": property_obj.property_code,
                    "anomaly_count": count
                })
        
        # Calculate average anomalies per property
        average_anomalies = total_anomalies / total_properties if total_properties > 0 else 0
        
        return PortfolioAnalyticsResponse(
            total_properties=total_properties,
            total_anomalies=total_anomalies,
            anomalies_by_severity=anomalies_by_severity,
            top_accounts_with_anomalies=top_accounts_with_anomalies,
            average_anomalies_per_property=average_anomalies,
            properties_with_most_anomalies=properties_with_most_anomalies
        )
    
    except Exception as e:
        logger.error(f"Error getting portfolio analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio analytics: {str(e)}"
        )


@router.get("/property/{property_id}/comparison", response_model=PropertyComparisonResponse)
async def get_property_comparison(
    property_id: int,
    account_code: str = Query(..., description="Account code to compare"),
    metric_type: str = Query("balance_sheet", description="Metric type: balance_sheet, income_statement"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare a property's value to portfolio benchmarks.
    
    Returns:
        Property comparison including percentile rank, z-score, and comparison status.
    """
    try:
        cross_property_service = CrossPropertyIntelligenceService(db)
        
        if not cross_property_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portfolio benchmarks are not enabled"
            )
        
        # Get property
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {property_id} not found"
            )
        
        # Get property ranking
        ranking = cross_property_service.get_property_ranking(
            property_id=property_id,
            account_code=account_code,
            metric_type=metric_type
        )
        
        if not ranking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No benchmark data available for account {account_code}"
            )
        
        # Determine comparison status
        percentile = ranking.get('percentile', 50)
        if percentile >= 75:
            comparison_status = 'above_average'
        elif percentile >= 25:
            comparison_status = 'average'
        else:
            comparison_status = 'below_average'
        
        return PropertyComparisonResponse(
            property_id=property_id,
            property_name=property_obj.property_name,
            property_code=property_obj.property_code,
            account_code=account_code,
            property_value=ranking.get('property_value'),
            portfolio_mean=ranking.get('portfolio_mean'),
            portfolio_median=ranking.get('portfolio_median'),
            portfolio_std=ranking.get('portfolio_std'),
            percentile_rank=ranking.get('percentile'),
            z_score=ranking.get('z_score'),
            comparison_status=comparison_status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get property comparison: {str(e)}"
        )


@router.get("/outliers", response_model=List[OutlierResponse])
async def get_portfolio_outliers(
    account_code: str = Query(..., description="Account code to check for outliers"),
    metric_type: str = Query("balance_sheet", description="Metric type: balance_sheet, income_statement"),
    threshold: float = Query(2.0, description="Z-score threshold for outlier detection"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of outliers to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get portfolio outliers for a specific account.
    
    Returns properties with values that are statistical outliers compared to the portfolio.
    
    Args:
        account_code: Account code to check
        metric_type: Type of financial metric
        threshold: Z-score threshold (default: 2.0)
        limit: Maximum number of outliers to return
    
    Returns:
        List of outlier properties with detailed statistics
    """
    try:
        cross_property_service = CrossPropertyIntelligenceService(db)
        
        if not cross_property_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portfolio benchmarks are not enabled"
            )
        
        # Get benchmark
        benchmark = cross_property_service.calculate_benchmarks(
            account_code=account_code,
            metric_type=metric_type
        )
        
        if not benchmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No benchmark data available for account {account_code}"
            )
        
        # Get all property values for this account
        if metric_type == 'balance_sheet':
            from app.models.balance_sheet_data import BalanceSheetData
            from app.models.financial_period import FinancialPeriod
            from sqlalchemy import and_
            
            # Get latest period for each property
            latest_periods = db.query(
                FinancialPeriod.property_id,
                func.max(FinancialPeriod.id).label('period_id')
            ).group_by(FinancialPeriod.property_id).subquery()
            
            property_values = db.query(
                BalanceSheetData.property_id,
                BalanceSheetData.account_value
            ).join(
                latest_periods,
                and_(
                    BalanceSheetData.period_id == latest_periods.c.period_id,
                    BalanceSheetData.property_id == latest_periods.c.property_id
                )
            ).filter(
                BalanceSheetData.account_code == account_code
            ).all()
        else:
            # Similar for income_statement
            from app.models.income_statement_data import IncomeStatementData
            from app.models.financial_period import FinancialPeriod
            from sqlalchemy import and_
            
            latest_periods = db.query(
                FinancialPeriod.property_id,
                func.max(FinancialPeriod.id).label('period_id')
            ).group_by(FinancialPeriod.property_id).subquery()
            
            property_values = db.query(
                IncomeStatementData.property_id,
                IncomeStatementData.account_value
            ).join(
                latest_periods,
                and_(
                    IncomeStatementData.period_id == latest_periods.c.period_id,
                    IncomeStatementData.property_id == latest_periods.c.property_id
                )
            ).filter(
                IncomeStatementData.account_code == account_code
            ).all()
        
        # Calculate outliers
        outliers = []
        for property_id, value in property_values:
            if value is None:
                continue
            
            z_score = (value - benchmark.mean_value) / benchmark.std_value if benchmark.std_value > 0 else 0
            
            if abs(z_score) >= threshold:
                property_obj = db.query(Property).filter(Property.id == property_id).first()
                if property_obj:
                    percentile_rank = cross_property_service._calculate_percentile_rank(value, benchmark)
                    
                    outlier_type = 'extreme' if abs(z_score) >= 3.0 else ('high' if z_score > 0 else 'low')
                    
                    outliers.append({
                        'property_id': property_id,
                        'property_name': property_obj.property_name,
                        'property_code': property_obj.property_code,
                        'account_code': account_code,
                        'value': float(value),
                        'outlier_type': outlier_type,
                        'z_score': z_score,
                        'percentile_rank': percentile_rank,
                        'portfolio_mean': benchmark.mean_value,
                        'portfolio_std': benchmark.std_value
                    })
        
        # Sort by absolute z-score (descending)
        outliers.sort(key=lambda x: abs(x['z_score']), reverse=True)
        
        # Limit results
        outliers = outliers[:limit]
        
        return [
            OutlierResponse(**outlier)
            for outlier in outliers
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio outliers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio outliers: {str(e)}"
        )

