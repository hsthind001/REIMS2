"""
Statistical Anomaly Detection Service - Enhanced

Implements Z-score and CUSUM (Cumulative Sum) anomaly detection
for financial data anomaly identification (BR-008).

Z-score: Identifies outliers based on standard deviations from mean
CUSUM: Detects sustained shifts in mean values over time

Use cases:
- Revenue volatility detection
- Expense spike identification
- Occupancy rate anomalies
- NOI fluctuation detection
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import json
import logging
import numpy as np
from scipy import stats

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.financial_metrics import FinancialMetrics
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity, AlertStatus, CommitteeType

logger = logging.getLogger(__name__)


class StatisticalAnomalyService:
    """
    Statistical Anomaly Detection Service (BR-008)

    Implements:
    - Z-score anomaly detection
    - CUSUM change point detection
    - Volatility spike detection
    - Multi-metric analysis
    """

    # Z-score thresholds
    Z_SCORE_THRESHOLD_WARNING = 2.0    # 2 standard deviations
    Z_SCORE_THRESHOLD_CRITICAL = 3.0   # 3 standard deviations

    # CUSUM thresholds
    CUSUM_THRESHOLD_WARNING = 3.0
    CUSUM_THRESHOLD_CRITICAL = 5.0

    def __init__(self, db: Session):
        self.db = db

    def detect_anomalies_zscore(
        self,
        property_id: int,
        metric_name: str,
        lookback_periods: int = 12,
        threshold: float = 2.0
    ) -> Dict:
        """
        Detect anomalies using Z-score method

        Z-score = (X - μ) / σ
        where:
        - X = current value
        - μ = mean of historical values
        - σ = standard deviation

        Parameters:
        - property_id: Property ID
        - metric_name: Name of metric to analyze (e.g., "total_revenue", "noi", "occupancy_rate")
        - lookback_periods: Number of historical periods to analyze
        - threshold: Z-score threshold (default 2.0 = 2 standard deviations)

        Returns:
        - Anomalies detected with Z-scores
        - Statistical summary
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get historical data
            time_series = self._get_metric_time_series(
                property_id,
                metric_name,
                lookback_periods
            )
            logger.debug(
                "Z-score time series length=%s property=%s metric=%s",
                len(time_series),
                property_id,
                metric_name
            )

            if len(time_series) < 3:
                logger.debug(
                    "Insufficient time series for Z-score property=%s metric=%s count=%s",
                    property_id,
                    metric_name,
                    len(time_series)
                )
                return {
                    "success": False,
                    "error": f"Insufficient data: need at least 3 periods, got {len(time_series)}"
                }

            # Extract values
            values = np.array([item["value"] for item in time_series])
            periods = [item["period"] for item in time_series]

            # Calculate statistics
            mean = np.mean(values)
            std_dev = np.std(values, ddof=1)  # Sample standard deviation

            if std_dev == 0:
                logger.debug(
                    "Z-score std_dev=0 property=%s metric=%s",
                    property_id,
                    metric_name
                )
                return {
                    "success": False,
                    "error": "Standard deviation is zero - no variation in data"
                }

            # Calculate Z-scores
            z_scores = (values - mean) / std_dev

            # Identify anomalies
            anomalies = []
            for i, (period, value, z_score) in enumerate(zip(periods, values, z_scores)):
                abs_z = abs(z_score)

                if abs_z >= threshold:
                    severity = self._determine_severity_zscore(abs_z)

                    anomalies.append({
                        "period_id": period["period_id"],
                        "period_date": period["period_date"],
                        "value": float(value),
                        "z_score": float(z_score),
                        "abs_z_score": float(abs_z),
                        "severity": severity,
                        "deviation_from_mean": float(value - mean),
                        "deviation_percentage": float((value - mean) / mean * 100) if mean != 0 else 0,
                        "direction": "above" if z_score > 0 else "below",
                    })

            # Create alerts for critical anomalies
            alerts_created = []
            for anomaly in anomalies:
                if anomaly["severity"] in ["CRITICAL", "URGENT"]:
                    alert = self._create_anomaly_alert(
                        property_id=property_id,
                        metric_name=metric_name,
                        anomaly_data=anomaly,
                        detection_method="Z-score"
                    )
                    if alert:
                        alerts_created.append(alert.id)

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "metric_name": metric_name,
                "detection_method": "Z-score",
                "lookback_periods": lookback_periods,
                "threshold": threshold,
                "statistics": {
                    "mean": float(mean),
                    "std_dev": float(std_dev),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "median": float(np.median(values)),
                    "coefficient_of_variation": float(std_dev / mean) if mean != 0 else 0,
                },
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "alerts_created": alerts_created,
                "time_series": [
                    {
                        "period_date": periods[i]["period_date"],
                        "value": float(values[i]),
                        "z_score": float(z_scores[i]),
                    }
                    for i in range(len(values))
                ],
            }

        except Exception as e:
            logger.error(f"Z-score anomaly detection failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def detect_anomalies_cusum(
        self,
        property_id: int,
        metric_name: str,
        lookback_periods: int = 12,
        threshold: float = 3.0,
        drift: float = 0.5
    ) -> Dict:
        """
        Detect anomalies using CUSUM (Cumulative Sum) method

        CUSUM detects sustained shifts in the mean value over time.
        More sensitive to gradual changes than Z-score.

        Parameters:
        - property_id: Property ID
        - metric_name: Metric to analyze
        - lookback_periods: Number of historical periods
        - threshold: CUSUM threshold (default 3.0)
        - drift: Allowable drift (default 0.5 standard deviations)

        Returns:
        - Change points detected
        - CUSUM statistics
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get historical data
            time_series = self._get_metric_time_series(
                property_id,
                metric_name,
                lookback_periods
            )
            logger.debug(
                "CUSUM time series length=%s property=%s metric=%s",
                len(time_series),
                property_id,
                metric_name
            )

            if len(time_series) < 5:
                logger.debug(
                    "Insufficient time series for CUSUM property=%s metric=%s count=%s",
                    property_id,
                    metric_name,
                    len(time_series)
                )
                return {
                    "success": False,
                    "error": f"Insufficient data: need at least 5 periods, got {len(time_series)}"
                }

            # Extract values
            values = np.array([item["value"] for item in time_series])
            periods = [item["period"] for item in time_series]

            # Calculate statistics
            mean = np.mean(values)
            std_dev = np.std(values, ddof=1)

            if std_dev == 0:
                logger.debug(
                    "CUSUM std_dev=0 property=%s metric=%s",
                    property_id,
                    metric_name
                )
                return {
                    "success": False,
                    "error": "Standard deviation is zero - no variation in data"
                }

            # Normalize data
            normalized = (values - mean) / std_dev

            # Calculate CUSUM
            cusum_high = np.zeros(len(normalized))
            cusum_low = np.zeros(len(normalized))

            for i in range(1, len(normalized)):
                cusum_high[i] = max(0, cusum_high[i-1] + normalized[i] - drift)
                cusum_low[i] = min(0, cusum_low[i-1] + normalized[i] + drift)

            # Detect change points
            change_points = []
            anomalies = []

            for i, (period, value, ch, cl) in enumerate(zip(periods, values, cusum_high, cusum_low)):
                abs_cusum = max(abs(ch), abs(cl))

                if abs_cusum >= threshold:
                    severity = self._determine_severity_cusum(abs_cusum)
                    direction = "upward_shift" if ch > abs(cl) else "downward_shift"

                    change_point = {
                        "period_id": period["period_id"],
                        "period_date": period["period_date"],
                        "value": float(value),
                        "cusum_high": float(ch),
                        "cusum_low": float(cl),
                        "cusum_magnitude": float(abs_cusum),
                        "severity": severity,
                        "direction": direction,
                        "is_change_point": True,
                    }

                    change_points.append(change_point)
                    anomalies.append(change_point)

            # Create alerts for critical changes
            alerts_created = []
            for anomaly in anomalies:
                if anomaly["severity"] in ["CRITICAL", "URGENT"]:
                    alert = self._create_anomaly_alert(
                        property_id=property_id,
                        metric_name=metric_name,
                        anomaly_data=anomaly,
                        detection_method="CUSUM"
                    )
                    if alert:
                        alerts_created.append(alert.id)

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "metric_name": metric_name,
                "detection_method": "CUSUM",
                "lookback_periods": lookback_periods,
                "threshold": threshold,
                "drift": drift,
                "statistics": {
                    "mean": float(mean),
                    "std_dev": float(std_dev),
                },
                "change_points_detected": len(change_points),
                "change_points": change_points,
                "alerts_created": alerts_created,
                "time_series": [
                    {
                        "period_date": periods[i]["period_date"],
                        "value": float(values[i]),
                        "cusum_high": float(cusum_high[i]),
                        "cusum_low": float(cusum_low[i]),
                    }
                    for i in range(len(values))
                ],
            }

        except Exception as e:
            logger.error(f"CUSUM anomaly detection failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def detect_volatility_spikes(
        self,
        property_id: int,
        metric_name: str,
        lookback_periods: int = 12,
        window_size: int = 3
    ) -> Dict:
        """
        Detect volatility spikes using rolling standard deviation

        Identifies periods where volatility suddenly increases
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get historical data
            time_series = self._get_metric_time_series(
                property_id,
                metric_name,
                lookback_periods
            )

            if len(time_series) < window_size * 2:
                return {
                    "success": False,
                    "error": f"Insufficient data for volatility analysis"
                }

            # Extract values
            values = np.array([item["value"] for item in time_series])
            periods = [item["period"] for item in time_series]

            # Calculate rolling standard deviation
            rolling_std = []
            for i in range(len(values) - window_size + 1):
                window = values[i:i + window_size]
                rolling_std.append(np.std(window, ddof=1))

            rolling_std = np.array(rolling_std)

            # Detect spikes (volatility > 2x average volatility)
            avg_volatility = np.mean(rolling_std)
            volatility_spikes = []

            for i, vol in enumerate(rolling_std):
                if vol > avg_volatility * 2:
                    period_idx = i + window_size - 1
                    volatility_spikes.append({
                        "period_date": periods[period_idx]["period_date"],
                        "volatility": float(vol),
                        "avg_volatility": float(avg_volatility),
                        "spike_multiplier": float(vol / avg_volatility),
                        "severity": "WARNING" if vol < avg_volatility * 3 else "CRITICAL",
                    })

            return {
                "success": True,
                "property_id": property_id,
                "metric_name": metric_name,
                "detection_method": "Volatility Analysis",
                "volatility_spikes_detected": len(volatility_spikes),
                "average_volatility": float(avg_volatility),
                "max_volatility": float(np.max(rolling_std)),
                "volatility_spikes": volatility_spikes,
            }

        except Exception as e:
            logger.error(f"Volatility spike detection failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def comprehensive_anomaly_scan(
        self,
        property_id: int,
        metrics: Optional[List[str]] = None
    ) -> Dict:
        """
        Comprehensive anomaly scan across multiple metrics

        Runs Z-score, CUSUM, and volatility detection on all key metrics
        """
        if metrics is None:
            metrics = [
                "total_revenue",
                "noi",
                "occupancy_rate",
                "operating_expenses",
                "net_income"
            ]

        results = {
            "property_id": property_id,
            "scan_date": datetime.utcnow().isoformat(),
            "metrics_scanned": len(metrics),
            "total_anomalies": 0,
            "total_alerts_created": 0,
            "results_by_metric": {}
        }

        for metric in metrics:
            metric_results = {
                "zscore": self.detect_anomalies_zscore(property_id, metric),
                "cusum": self.detect_anomalies_cusum(property_id, metric),
                "volatility": self.detect_volatility_spikes(property_id, metric),
            }

            # Count anomalies
            zscore_anomalies = metric_results["zscore"].get("anomalies_detected", 0) if metric_results["zscore"].get("success") else 0
            cusum_anomalies = metric_results["cusum"].get("change_points_detected", 0) if metric_results["cusum"].get("success") else 0
            volatility_anomalies = metric_results["volatility"].get("volatility_spikes_detected", 0) if metric_results["volatility"].get("success") else 0

            total_metric_anomalies = zscore_anomalies + cusum_anomalies + volatility_anomalies
            results["total_anomalies"] += total_metric_anomalies

            # Count alerts
            zscore_alerts = len(metric_results["zscore"].get("alerts_created", [])) if metric_results["zscore"].get("success") else 0
            cusum_alerts = len(metric_results["cusum"].get("alerts_created", [])) if metric_results["cusum"].get("success") else 0
            results["total_alerts_created"] += (zscore_alerts + cusum_alerts)

            results["results_by_metric"][metric] = {
                "total_anomalies": total_metric_anomalies,
                "zscore_anomalies": zscore_anomalies,
                "cusum_anomalies": cusum_anomalies,
                "volatility_spikes": volatility_anomalies,
                "details": metric_results
            }

        return results

    def _get_metric_time_series(
        self,
        property_id: int,
        metric_name: str,
        lookback_periods: int
    ) -> List[Dict]:
        """
        Get time series data for a specific metric
        """
        # Get financial periods
        periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(lookback_periods).all()

        time_series = []

        for period in reversed(periods):
            # Get metric value based on metric name
            if metric_name == "total_revenue":
                value = self._get_total_revenue(property_id, period.id)
            elif metric_name == "noi":
                value = self._get_noi(property_id, period.id)
            elif metric_name == "operating_expenses":
                value = self._get_operating_expenses(property_id, period.id)
            elif metric_name == "net_income":
                value = self._get_net_income(property_id, period.id)
            elif metric_name == "occupancy_rate":
                value = self._get_occupancy_rate(property_id, period.id)
            else:
                # Try to get from financial metrics table
                metric = self.db.query(FinancialMetrics).filter(
                    FinancialMetrics.property_id == property_id,
                    FinancialMetrics.period_id == period.id
                ).first()

                value = getattr(metric, metric_name, None) if metric else None

            if value is None:
                logger.debug(
                    "No metric value for property=%s period=%s metric=%s",
                    property_id,
                    period.id,
                    metric_name
                )

            if value is not None:
                period_payload = {
                    "period_id": period.id,
                    "period_date": period.period_end_date.isoformat()
                }
                time_series.append({
                    "period": period_payload,
                    "period_id": period.id,
                    "period_date": period.period_end_date.isoformat(),
                    "value": float(value)
                })

        return time_series

    def persist_statistical_anomalies(
        self,
        property_id: int,
        metric_name: str,
        anomalies: List[Dict],
        detection_method: str,
        statistics: Optional[Dict] = None
    ) -> int:
        """
        Persist statistical anomalies into anomaly_detections, linking to the latest
        document for each period/property.
        """
        if not anomalies:
            return 0

        period_ids = {item.get("period_id") for item in anomalies if item.get("period_id")}
        if not period_ids:
            logger.debug("No period IDs found for anomalies property=%s metric=%s", property_id, metric_name)
            return 0

        preferred_document_type = self._preferred_document_type(metric_name)
        documents_by_period = self._get_latest_documents_for_periods(
            property_id,
            period_ids,
            preferred_document_type
        )
        if not documents_by_period:
            logger.debug("No documents found for property=%s periods=%s", property_id, sorted(period_ids))
            return 0

        mean_value = statistics.get("mean") if statistics else None
        inserted = 0

        delete_sql = text("""
            DELETE FROM anomaly_detections
            WHERE document_id = :document_id
              AND field_name = :field_name
              AND anomaly_type = :anomaly_type
              AND metadata->>'period_id' = :period_id
        """)

        insert_sql = text("""
            INSERT INTO anomaly_detections
            (document_id, field_name, field_value, expected_value,
             anomaly_type, severity, confidence, z_score, percentage_change, metadata, detected_at)
            VALUES (:document_id, :field_name, :field_value, :expected_value,
                    :anomaly_type, :severity, :confidence, :z_score, :percentage_change, :metadata, NOW())
            RETURNING id
        """)

        for anomaly in anomalies:
            period_id = anomaly.get("period_id")
            if not period_id:
                continue

            document = documents_by_period.get(period_id)
            if not document:
                logger.debug(
                    "No document for property=%s period=%s metric=%s",
                    property_id,
                    period_id,
                    metric_name
                )
                continue

            value = anomaly.get("value")
            severity = self._normalize_severity(anomaly.get("severity"))
            anomaly_type = f"statistical_{detection_method}"
            confidence = self._confidence_from_magnitude(
                anomaly.get("abs_z_score") or anomaly.get("cusum_magnitude") or anomaly.get("z_score"),
                4.0 if detection_method == "zscore" else 6.0
            )

            percentage_change = anomaly.get("deviation_percentage")
            if percentage_change is None and mean_value not in (None, 0) and value is not None:
                percentage_change = (float(value) - float(mean_value)) / float(mean_value) * 100

            metadata = {
                "property_id": property_id,
                "metric_name": metric_name,
                "detection_method": detection_method,
                "period_id": str(period_id),
                "period_date": anomaly.get("period_date"),
                "direction": anomaly.get("direction"),
                "document_type": document.document_type,
                "preferred_document_type": preferred_document_type,
            }

            if mean_value is not None:
                metadata["mean"] = float(mean_value)
            if anomaly.get("cusum_magnitude") is not None:
                metadata["cusum_magnitude"] = float(anomaly.get("cusum_magnitude"))

            try:
                self.db.execute(delete_sql, {
                    "document_id": document.id,
                    "field_name": metric_name,
                    "anomaly_type": anomaly_type,
                    "period_id": str(period_id)
                })

                result = self.db.execute(insert_sql, {
                    "document_id": document.id,
                    "field_name": metric_name,
                    "field_value": str(value) if value is not None else None,
                    "expected_value": str(mean_value) if mean_value is not None else None,
                    "anomaly_type": anomaly_type,
                    "severity": severity,
                    "confidence": confidence,
                    "z_score": anomaly.get("z_score"),
                    "percentage_change": percentage_change,
                    "metadata": json.dumps(metadata) if metadata else None
                })
                if result.scalar():
                    inserted += 1
            except Exception as exc:
                logger.error(
                    "Failed to persist anomaly property=%s metric=%s period=%s: %s",
                    property_id,
                    metric_name,
                    period_id,
                    exc
                )
                self.db.rollback()
                continue

        if inserted:
            self.db.commit()
        return inserted

    def _get_latest_documents_for_periods(
        self,
        property_id: int,
        period_ids: set,
        document_type: Optional[str] = None
    ) -> Dict[int, DocumentUpload]:
        base_query = self.db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id.in_(list(period_ids)),
            DocumentUpload.is_active == True,
            DocumentUpload.extraction_status == "completed"
        )

        if document_type:
            base_query = base_query.filter(DocumentUpload.document_type == document_type)

        documents = base_query.order_by(
            DocumentUpload.period_id,
            DocumentUpload.upload_date.desc(),
            DocumentUpload.id.desc()
        ).all()

        document_map = {}
        for doc in documents:
            if doc.period_id not in document_map:
                document_map[doc.period_id] = doc

        missing = [pid for pid in period_ids if pid not in document_map]
        if missing:
            fallback_docs = self.db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id.in_(missing),
                DocumentUpload.is_active == True
            ).order_by(
                DocumentUpload.period_id,
                DocumentUpload.upload_date.desc(),
                DocumentUpload.id.desc()
            ).all()
            for doc in fallback_docs:
                if doc.period_id not in document_map:
                    document_map[doc.period_id] = doc

        return document_map

    @staticmethod
    def _normalize_severity(severity: Optional[str]) -> str:
        if not severity:
            return "medium"
        severity_key = severity.lower()
        mapping = {
            "urgent": "critical",
            "critical": "critical",
            "warning": "high",
            "info": "low"
        }
        return mapping.get(severity_key, severity_key)

    @staticmethod
    def _confidence_from_magnitude(magnitude: Optional[float], max_value: float) -> float:
        try:
            if magnitude is None or max_value <= 0:
                return 0.6
            ratio = min(abs(float(magnitude)) / max_value, 1.0)
            return round(0.6 + (0.95 - 0.6) * ratio, 4)
        except (TypeError, ValueError):
            return 0.6

    @staticmethod
    def _preferred_document_type(metric_name: str) -> str:
        return "income_statement"

    def _get_total_revenue(self, property_id: int, period_id: int) -> Optional[Decimal]:
        """Get total revenue for a period"""
        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like("4%")
        ).all()

        total = sum(Decimal(str(item.period_amount or 0)) for item in income_data)
        return total if total > 0 else None

    def _get_noi(self, property_id: int, period_id: int) -> Optional[Decimal]:
        """Get NOI for a period"""
        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id
        ).all()

        revenue = sum(
            Decimal(str(item.period_amount or 0))
            for item in income_data
            if item.account_code and item.account_code.startswith("4")
        )

        expenses = sum(
            Decimal(str(item.period_amount or 0))
            for item in income_data
            if item.account_code and (
                item.account_code.startswith("5") or
                item.account_code.startswith("6")
            )
        )

        noi = revenue - expenses
        return noi if noi != 0 else None

    def _get_operating_expenses(self, property_id: int, period_id: int) -> Optional[Decimal]:
        """Get operating expenses for a period"""
        from sqlalchemy import or_

        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            or_(
                IncomeStatementData.account_code.like("5%"),
                IncomeStatementData.account_code.like("6%")
            )
        ).all()

        total = sum(Decimal(str(item.period_amount or 0)) for item in income_data)
        return total if total > 0 else None

    def _get_net_income(self, property_id: int, period_id: int) -> Optional[Decimal]:
        """Get net income for a period"""
        # Simplified - in production, calculate properly from all income/expense accounts
        return self._get_noi(property_id, period_id)

    def _get_occupancy_rate(self, property_id: int, period_id: int) -> Optional[Decimal]:
        """Get occupancy rate for a period"""
        metric = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()

        return Decimal(str(metric.occupancy_rate)) if metric and metric.occupancy_rate else None

    def _determine_severity_zscore(self, abs_z_score: float) -> str:
        """Determine severity based on Z-score magnitude"""
        if abs_z_score >= 3.5:
            return "URGENT"
        elif abs_z_score >= 3.0:
            return "CRITICAL"
        elif abs_z_score >= 2.0:
            return "WARNING"
        else:
            return "INFO"

    def _determine_severity_cusum(self, cusum_magnitude: float) -> str:
        """Determine severity based on CUSUM magnitude"""
        if cusum_magnitude >= 6.0:
            return "URGENT"
        elif cusum_magnitude >= 5.0:
            return "CRITICAL"
        elif cusum_magnitude >= 3.0:
            return "WARNING"
        else:
            return "INFO"

    def _create_anomaly_alert(
        self,
        property_id: int,
        metric_name: str,
        anomaly_data: Dict,
        detection_method: str
    ) -> Optional[CommitteeAlert]:
        """Create alert for detected anomaly"""
        try:
            # Check if alert already exists
            existing_alert = self.db.query(CommitteeAlert).filter(
                CommitteeAlert.property_id == property_id,
                CommitteeAlert.alert_type == AlertType.ANOMALY_DETECTED,
                CommitteeAlert.status == AlertStatus.ACTIVE,
                CommitteeAlert.related_metric == metric_name
            ).first()

            if existing_alert:
                return None  # Don't create duplicate

            severity_map = {
                "URGENT": AlertSeverity.URGENT,
                "CRITICAL": AlertSeverity.CRITICAL,
                "WARNING": AlertSeverity.WARNING,
                "INFO": AlertSeverity.INFO,
            }

            severity = severity_map.get(anomaly_data["severity"], AlertSeverity.WARNING)

            # Build description
            if detection_method == "Z-score":
                description = (
                    f"Statistical anomaly detected in {metric_name} using Z-score analysis.\n\n"
                    f"Value: ${anomaly_data['value']:,.2f}\n"
                    f"Z-score: {anomaly_data['z_score']:.2f}\n"
                    f"Deviation: {anomaly_data['deviation_percentage']:.1f}% {anomaly_data['direction']} mean\n\n"
                    f"This value is {abs(anomaly_data['z_score']):.1f} standard deviations from the historical mean, "
                    f"indicating an unusual pattern that requires review."
                )
            else:  # CUSUM
                description = (
                    f"Sustained shift detected in {metric_name} using CUSUM analysis.\n\n"
                    f"Value: ${anomaly_data['value']:,.2f}\n"
                    f"CUSUM Magnitude: {anomaly_data['cusum_magnitude']:.2f}\n"
                    f"Direction: {anomaly_data['direction']}\n\n"
                    f"A sustained change in the mean value has been detected, "
                    f"indicating a structural shift in performance."
                )

            alert = CommitteeAlert(
                property_id=property_id,
                alert_type=AlertType.ANOMALY_DETECTED,
                severity=severity,
                status=AlertStatus.ACTIVE,
                title=f"Anomaly Detected: {metric_name.replace('_', ' ').title()}",
                description=description,
                assigned_committee=CommitteeType.RISK_COMMITTEE,
                requires_approval=severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT],
                related_metric=metric_name,
                br_id="BR-008",
                metadata={
                    "detection_method": detection_method,
                    "anomaly_data": anomaly_data,
                }
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            logger.info(f"Anomaly alert created: {alert.id} for property {property_id}, metric {metric_name}")
            return alert

        except Exception as e:
            logger.error(f"Failed to create anomaly alert: {str(e)}")
            self.db.rollback()
            return None
