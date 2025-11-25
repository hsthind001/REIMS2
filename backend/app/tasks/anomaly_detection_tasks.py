"""
Anomaly Detection Periodic Tasks

BR-008: Nightly batch job for statistical anomaly detection
Runs z-score and CUSUM anomaly detection on all properties/metrics
"""
from celery import Task
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.services.statistical_anomaly_service import StatisticalAnomalyService
from app.models.property import Property
from app.models.financial_metrics import FinancialMetrics
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.anomaly_detection_tasks.run_nightly_anomaly_detection", bind=True)
def run_nightly_anomaly_detection(self: Task) -> dict:
    """
    Nightly batch job to detect anomalies across all properties and metrics
    
    BR-008: Runs z-score (≥2.0) and CUSUM trend shift detection
    Configurable sensitivity per property class
    
    Returns:
        dict: Summary of anomalies detected
    """
    db = SessionLocal()
    try:
        anomaly_service = StatisticalAnomalyService(db)
        
        # Get all active properties
        properties = db.query(Property).filter(Property.is_active == True).all()
        
        total_anomalies = 0
        properties_checked = 0
        anomalies_by_property = {}
        
        # Metrics to check for anomalies
        metrics_to_check = [
            "total_revenue",
            "net_operating_income",
            "occupancy_rate",
            "dscr",
            "total_expenses",
            "net_income"
        ]
        
        for property_obj in properties:
            try:
                property_anomalies = []
                
                # Check each metric
                for metric_name in metrics_to_check:
                    try:
                        # Z-score detection
                        zscore_result = anomaly_service.detect_anomalies_zscore(
                            property_id=property_obj.id,
                            metric_name=metric_name,
                            lookback_periods=12,
                            threshold=2.0  # BR-008 requirement: z-score ≥ 2.0
                        )
                        
                        if zscore_result.get("success") and zscore_result.get("anomalies"):
                            property_anomalies.extend(zscore_result["anomalies"])
                        
                        # CUSUM detection
                        cusum_result = anomaly_service.detect_anomalies_cusum(
                            property_id=property_obj.id,
                            metric_name=metric_name,
                            lookback_periods=12
                        )
                        
                        if cusum_result.get("success") and cusum_result.get("anomalies"):
                            property_anomalies.extend(cusum_result["anomalies"])
                            
                    except Exception as e:
                        logger.error(f"Error checking {metric_name} for property {property_obj.id}: {e}")
                        continue
                
                if property_anomalies:
                    anomalies_by_property[property_obj.id] = {
                        "property_name": property_obj.property_name,
                        "property_code": property_obj.property_code,
                        "anomaly_count": len(property_anomalies),
                        "anomalies": property_anomalies
                    }
                    total_anomalies += len(property_anomalies)
                
                properties_checked += 1
                
            except Exception as e:
                logger.error(f"Error processing property {property_obj.id}: {e}")
                continue
        
        result = {
            "success": True,
            "properties_checked": properties_checked,
            "total_anomalies": total_anomalies,
            "anomalies_by_property": anomalies_by_property,
            "timestamp": str(db.execute("SELECT NOW()").scalar())
        }
        
        logger.info(f"Nightly anomaly detection completed: {total_anomalies} anomalies found across {properties_checked} properties")
        
        return result
        
    except Exception as e:
        logger.error(f"Nightly anomaly detection failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.anomaly_detection_tasks.detect_anomalies_for_property")
def detect_anomalies_for_property(property_id: int, metric_name: str = None) -> dict:
    """
    Detect anomalies for a specific property (on-demand)
    
    Args:
        property_id: Property ID to check
        metric_name: Optional specific metric to check (checks all if None)
    
    Returns:
        dict: Anomalies detected
    """
    db = SessionLocal()
    try:
        anomaly_service = StatisticalAnomalyService(db)
        
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return {"success": False, "error": "Property not found"}
        
        metrics_to_check = [metric_name] if metric_name else [
            "total_revenue",
            "net_operating_income",
            "occupancy_rate",
            "dscr",
            "total_expenses",
            "net_income"
        ]
        
        all_anomalies = []
        
        for metric in metrics_to_check:
            try:
                # Z-score detection
                zscore_result = anomaly_service.detect_anomalies_zscore(
                    property_id=property_id,
                    metric_name=metric,
                    lookback_periods=12,
                    threshold=2.0
                )
                
                if zscore_result.get("success") and zscore_result.get("anomalies"):
                    all_anomalies.extend(zscore_result["anomalies"])
                
                # CUSUM detection
                cusum_result = anomaly_service.detect_anomalies_cusum(
                    property_id=property_id,
                    metric_name=metric,
                    lookback_periods=12
                )
                
                if cusum_result.get("success") and cusum_result.get("anomalies"):
                    all_anomalies.extend(cusum_result["anomalies"])
                    
            except Exception as e:
                logger.error(f"Error checking {metric} for property {property_id}: {e}")
                continue
        
        return {
            "success": True,
            "property_id": property_id,
            "property_name": property_obj.property_name,
            "anomalies": all_anomalies,
            "total_anomalies": len(all_anomalies)
        }
        
    except Exception as e:
        logger.error(f"Anomaly detection failed for property {property_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

