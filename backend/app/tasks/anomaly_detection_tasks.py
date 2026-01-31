"""
Anomaly Detection Periodic Tasks

BR-008: Nightly batch job for statistical anomaly detection
Runs z-score and CUSUM anomaly detection on all properties/metrics
"""
from celery import Task, group
from app.core.celery_config import celery_app
from app.db.database import SessionLocal
from app.services.statistical_anomaly_service import StatisticalAnomalyService
from app.models.property import Property
from app.models.financial_metrics import FinancialMetrics
from app.core.config import settings
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Maximum number of parallel workers for anomaly detection
MAX_PARALLEL_WORKERS = getattr(settings, 'BATCH_PROCESSING_MAX_CONCURRENT', 4)


def _get_metrics_to_check() -> list:
    base_metrics = [
        "total_revenue",
        "net_operating_income",
        "occupancy_rate",
        "dscr",
        "total_expenses",
        "net_income"
    ]
    skip_cols = {"id", "property_id", "period_id", "created_at", "updated_at", "calculated_at"}
    for column in FinancialMetrics.__table__.columns:
        if column.name in skip_cols:
            continue
        col_type = str(column.type).upper()
        if "DECIMAL" in col_type or "NUMERIC" in col_type or "INTEGER" in col_type:
            base_metrics.append(column.name)
    # Deduplicate while preserving order
    seen = set()
    metrics = []
    for name in base_metrics:
        if name not in seen:
            metrics.append(name)
            seen.add(name)
    return metrics


@celery_app.task(name="app.tasks.anomaly_detection_tasks.run_nightly_anomaly_detection", bind=True)
def run_nightly_anomaly_detection(self: Task, use_parallel: bool = True) -> dict:
    """
    Nightly batch job to detect anomalies across all properties and metrics (idempotent).
    
    BR-008: Runs z-score (≥2.0) and CUSUM trend shift detection
    Configurable sensitivity per property class
    
    Uses parallel processing when multiple properties need detection (default).
    
    Args:
        use_parallel: Whether to use parallel processing (default: True)
    
    Returns:
        dict: Summary of anomalies detected
    """
    from datetime import date
    from app.utils.task_idempotency import acquire_anomaly_nightly_lock
    task_id = self.request.id
    today = date.today().isoformat()
    if not acquire_anomaly_nightly_lock(today, task_id):
        logger.info(f"Nightly anomaly detection already running for {today}, skipping duplicate")
        return {"success": True, "skipped": True, "message": f"Already running for {today}"}

    db = SessionLocal()
    try:
        # Get all active properties
        properties = db.query(Property).filter(Property.status == "active").all()
        logger.debug("Fetched %s active properties for anomaly detection", len(properties))
        
        if not properties:
            return {
                "success": True,
                "properties_checked": 0,
                "total_anomalies": 0,
                "anomalies_by_property": {},
                "parallel_processing_used": False
            }
        
        # Metrics to check for anomalies
        metrics_to_check = _get_metrics_to_check()
        logger.debug("Anomaly detection metrics: %s", metrics_to_check)
        
        # Use parallel processing if enabled and we have multiple properties
        if use_parallel and len(properties) > 1:
            logger.info(f"Using parallel processing for {len(properties)} properties")
            property_ids = [p.id for p in properties]
            result = detect_anomalies_parallel(property_ids=property_ids, metric_names=metrics_to_check)
            result["parallel_processing_used"] = True
            result["timestamp"] = str(db.execute(text("SELECT NOW()")).scalar())
            return result
        
        # Sequential processing (fallback or single property)
        logger.info(f"Using sequential processing for {len(properties)} properties")
        anomaly_service = StatisticalAnomalyService(db)
        
        total_anomalies = 0
        properties_checked = 0
        anomalies_by_property = {}
        
        for property_obj in properties:
            try:
                property_anomalies = []
                logger.debug("Scanning property %s (%s)", property_obj.id, property_obj.property_code)
                
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
                            persisted = anomaly_service.persist_statistical_anomalies(
                                property_id=property_obj.id,
                                metric_name=metric_name,
                                anomalies=zscore_result.get("anomalies", []),
                                detection_method="zscore",
                                statistics=zscore_result.get("statistics")
                            )
                            if persisted:
                                logger.debug(
                                    "Persisted %s zscore anomalies for property %s metric %s",
                                    persisted,
                                    property_obj.id,
                                    metric_name
                                )
                        elif not zscore_result.get("success"):
                            logger.debug(
                                "Z-score failed for property %s metric %s: %s",
                                property_obj.id,
                                metric_name,
                                zscore_result.get("error")
                            )
                        
                        # CUSUM detection
                        cusum_result = anomaly_service.detect_anomalies_cusum(
                            property_id=property_obj.id,
                            metric_name=metric_name,
                            lookback_periods=12
                        )
                        
                        if cusum_result.get("success") and cusum_result.get("change_points"):
                            property_anomalies.extend(cusum_result["change_points"])
                            persisted = anomaly_service.persist_statistical_anomalies(
                                property_id=property_obj.id,
                                metric_name=metric_name,
                                anomalies=cusum_result.get("change_points", []),
                                detection_method="cusum",
                                statistics=cusum_result.get("statistics")
                            )
                            if persisted:
                                logger.debug(
                                    "Persisted %s cusum anomalies for property %s metric %s",
                                    persisted,
                                    property_obj.id,
                                    metric_name
                                )
                        elif not cusum_result.get("success"):
                            logger.debug(
                                "CUSUM failed for property %s metric %s: %s",
                                property_obj.id,
                                metric_name,
                                cusum_result.get("error")
                            )
                            
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
                logger.debug(
                    "Property %s anomalies: %s",
                    property_obj.id,
                    len(property_anomalies)
                )
                
                properties_checked += 1
                
            except Exception as e:
                logger.error(f"Error processing property {property_obj.id}: {e}")
                continue
        
        result = {
            "success": True,
            "properties_checked": properties_checked,
            "total_anomalies": total_anomalies,
            "anomalies_by_property": anomalies_by_property,
            "parallel_processing_used": False,
            "timestamp": str(db.execute(text("SELECT NOW()")).scalar())
        }
        
        logger.info(f"Nightly anomaly detection completed: {total_anomalies} anomalies found across {properties_checked} properties")
        
        return result
        
    except Exception as e:
        logger.error(f"Nightly anomaly detection failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="app.tasks.anomaly_detection_tasks.detect_anomalies_for_property", bind=True)
def detect_anomalies_for_property(self: Task, property_id: int, metric_name: str = None) -> dict:
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
        
        metrics_to_check = [metric_name] if metric_name else _get_metrics_to_check()
        logger.debug("On-demand anomaly scan property=%s metrics=%s", property_id, metrics_to_check)
        
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
                    anomaly_service.persist_statistical_anomalies(
                        property_id=property_id,
                        metric_name=metric,
                        anomalies=zscore_result.get("anomalies", []),
                        detection_method="zscore",
                        statistics=zscore_result.get("statistics")
                    )
                elif not zscore_result.get("success"):
                    logger.debug(
                        "Z-score failed for property %s metric %s: %s",
                        property_id,
                        metric,
                        zscore_result.get("error")
                    )
                
                # CUSUM detection
                cusum_result = anomaly_service.detect_anomalies_cusum(
                    property_id=property_id,
                    metric_name=metric,
                    lookback_periods=12
                )
                
                if cusum_result.get("success") and cusum_result.get("change_points"):
                    all_anomalies.extend(cusum_result["change_points"])
                    anomaly_service.persist_statistical_anomalies(
                        property_id=property_id,
                        metric_name=metric,
                        anomalies=cusum_result.get("change_points", []),
                        detection_method="cusum",
                        statistics=cusum_result.get("statistics")
                    )
                elif not cusum_result.get("success"):
                    logger.debug(
                        "CUSUM failed for property %s metric %s: %s",
                        property_id,
                        metric,
                        cusum_result.get("error")
                    )
                    
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


@celery_app.task(name="app.tasks.anomaly_detection_tasks.detect_anomalies_parallel", bind=True)
def detect_anomalies_parallel(self: Task, property_ids: list = None, metric_names: list = None) -> dict:
    """
    Detect anomalies for multiple properties in parallel using Celery groups.
    
    Supports linear scaling up to MAX_PARALLEL_WORKERS (default 4).
    
    Args:
        property_ids: List of property IDs to check (None = all active properties)
        metric_names: List of metrics to check (None = all metrics)
    
    Returns:
        dict: Aggregated results from all parallel tasks
    """
    db = SessionLocal()
    try:
        # Get properties to process
        if property_ids:
            properties = db.query(Property).filter(
                Property.id.in_(property_ids),
                Property.status == "active"
            ).all()
        else:
            properties = db.query(Property).filter(Property.status == "active").all()

        logger.debug("Prepared %s properties for parallel anomaly detection", len(properties))
        
        if not properties:
            return {
                "success": True,
                "properties_checked": 0,
                "total_anomalies": 0,
                "anomalies_by_property": {},
                "parallel_workers_used": 0
            }
        
        # Default metrics if not specified
        if metric_names is None:
            metric_names = [
                "total_revenue",
                "net_operating_income",
                "occupancy_rate",
                "dscr",
                "total_expenses",
                "net_income"
            ]
        
        # Limit parallel workers to MAX_PARALLEL_WORKERS
        num_workers = min(len(properties), MAX_PARALLEL_WORKERS)
        
        # Create Celery group for parallel execution
        # Split properties into chunks for parallel processing
        chunk_size = (len(properties) + num_workers - 1) // num_workers  # Ceiling division
        
        property_chunks = []
        for i in range(0, len(properties), chunk_size):
            chunk = properties[i:i + chunk_size]
            property_chunks.append([p.id for p in chunk])
        
        # Create group of tasks
        job = group(
            detect_anomalies_for_property.s(property_id=prop_id, metric_name=metric_name)
            for chunk in property_chunks
            for prop_id in chunk
            for metric_name in metric_names
        )
        
        # Execute in parallel
        logger.info(f"Starting parallel anomaly detection for {len(properties)} properties "
                   f"using {num_workers} workers")
        
        result_group = job.apply_async()
        
        # Wait for all tasks to complete and aggregate results
        results = result_group.get()  # This blocks until all tasks complete
        
        # Aggregate results
        total_anomalies = 0
        properties_checked = 0
        anomalies_by_property = {}
        errors = []
        
        for result in results:
            if result.get("success"):
                prop_id = result.get("property_id")
                if prop_id:
                    if prop_id not in anomalies_by_property:
                        anomalies_by_property[prop_id] = {
                            "property_name": result.get("property_name"),
                            "anomaly_count": 0,
                            "anomalies": []
                        }
                    
                    anomalies = result.get("anomalies", [])
                    anomalies_by_property[prop_id]["anomalies"].extend(anomalies)
                    anomalies_by_property[prop_id]["anomaly_count"] += len(anomalies)
                    total_anomalies += len(anomalies)
                    properties_checked += 1
            else:
                errors.append(result.get("error", "Unknown error"))
        
        logger.info(f"Parallel anomaly detection completed: {total_anomalies} anomalies found "
                   f"across {properties_checked} properties using {num_workers} workers")
        
        return {
            "success": True,
            "properties_checked": properties_checked,
            "total_anomalies": total_anomalies,
            "anomalies_by_property": anomalies_by_property,
            "parallel_workers_used": num_workers,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Parallel anomaly detection failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()
