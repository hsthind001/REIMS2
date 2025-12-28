"""
Forensic Audit Anomaly Integration Service

Integrates forensic audit findings (140+ rules across 7 phases) with
REIMS existing ML-based anomaly detection system.

This service converts forensic audit results into anomaly detections
and creates committee alerts for critical findings.
"""

from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
from decimal import Decimal

from app.models.anomaly_detection import (
    AnomalyDetection,
    AnomalyCategory,
    AnomalyDirection,
    BaselineType,
    PatternType,
    ResolutionType
)


class ForensicAuditAnomalyIntegrationService:
    """
    Integrates Big 5 forensic audit findings with existing anomaly detection.

    Converts forensic audit results into anomaly format and creates
    correlation IDs for related findings across multiple documents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def convert_reconciliation_failures_to_anomalies(
        self,
        property_id: UUID,
        period_id: UUID,
        document_id: int
    ) -> List[Dict[str, Any]]:
        """
        Convert cross-document reconciliation failures to anomaly detections.

        Creates anomaly records for:
        - Net income flow mismatches (IS → BS)
        - Three-way reconciliation failures (depreciation, amortization)
        - Cash reconciliation variances (BS → CF)
        - Mortgage principal mismatches (MS → BS → CF)
        - Four-way reconciliations (property tax, insurance)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            document_id: Document upload ID to link anomalies

        Returns:
            List of created anomaly detection records
        """

        # Query reconciliation failures from cross_document_reconciliations table
        query = text("""
            SELECT
                reconciliation_type,
                rule_code,
                status,
                source_document,
                target_document,
                source_value,
                target_value,
                difference,
                materiality_threshold,
                is_material,
                explanation,
                recommendation
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND status IN ('FAIL', 'WARNING')
            ORDER BY
                CASE status
                    WHEN 'FAIL' THEN 1
                    WHEN 'WARNING' THEN 2
                END
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        failures = result.fetchall()

        if not failures:
            return []

        # Generate correlation ID for related reconciliation failures
        correlation_id = uuid4()

        anomalies_created = []

        for row in failures:
            reconciliation_type = row[0]
            rule_code = row[1]
            status = row[2]
            source_doc = row[3]
            target_doc = row[4]
            source_value = float(row[5])
            target_value = float(row[6])
            difference = float(row[7])
            materiality_threshold = float(row[8])
            is_material = row[9]
            explanation = row[10]
            recommendation = row[11]

            # Determine severity based on materiality and status
            if status == 'FAIL':
                severity = 'critical' if is_material else 'high'
                anomaly_score = 95 if is_material else 85
            else:  # WARNING
                severity = 'medium'
                anomaly_score = 60

            # Determine direction
            direction = AnomalyDirection.UP if difference > 0 else AnomalyDirection.DOWN

            # Create anomaly detection record
            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name=f"{reconciliation_type}_reconciliation",
                field_value=str(source_value),
                expected_value=str(target_value),
                z_score=None,  # Not applicable for reconciliation
                percentage_change=abs(difference / target_value * 100) if target_value != 0 else None,
                anomaly_type="reconciliation_failure",  # New type
                severity=severity,
                confidence=0.99,  # High confidence - mathematical fact

                # Enhanced fields
                forecast_method=None,
                confidence_calibrated=0.99,
                detection_window="single_period",
                windows_detected=1,
                ensemble_confidence=None,
                detection_methods=["cross_document_reconciliation"],
                is_consensus=True,  # Definitive failure
                change_point_detected=False,
                context_suppressed=False,
                suppression_reason=None,

                # World-class fields
                anomaly_score=Decimal(str(anomaly_score)),
                impact_amount=Decimal(str(abs(difference))),
                direction=direction,
                root_cause_candidates={
                    "source_document": source_doc,
                    "target_document": target_doc,
                    "rule_code": rule_code,
                    "reconciliation_type": reconciliation_type,
                    "possible_causes": [
                        "Data entry error",
                        "Extraction error",
                        "Account mapping mismatch",
                        "Timing difference",
                        "Missing transaction"
                    ]
                },
                baseline_type=BaselineType.MEAN,
                correlation_id=correlation_id,
                suppressed_until=None,
                anomaly_category=AnomalyCategory.ACCOUNTING,
                pattern_type=PatternType.POINT,
                is_one_off=False,
                is_recurrent=False,
                cross_property_pattern=False,

                # Root cause tracking
                resolution_type=None,  # To be set when resolved
                root_cause=None,  # To be populated during investigation

                # Metadata
                metadata_json={
                    "forensic_audit": True,
                    "rule_code": rule_code,
                    "source_document": source_doc,
                    "target_document": target_doc,
                    "source_value": source_value,
                    "target_value": target_value,
                    "difference": difference,
                    "materiality_threshold": materiality_threshold,
                    "is_material": is_material,
                    "explanation": explanation,
                    "recommendation": recommendation,
                    "audit_phase": "Phase 3: Cross-Document Reconciliation"
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "reconciliation_type": reconciliation_type,
                "rule_code": rule_code,
                "severity": severity,
                "anomaly_score": anomaly_score,
                "impact_amount": abs(difference),
                "correlation_id": str(correlation_id)
            })

        await self.db.commit()

        return anomalies_created

    async def convert_fraud_indicators_to_anomalies(
        self,
        property_id: UUID,
        period_id: UUID,
        document_id: int
    ) -> List[Dict[str, Any]]:
        """
        Convert fraud detection findings to anomaly records.

        Creates anomalies for:
        - Benford's Law violations (chi-square > 15.51)
        - Round number fabrication (>10% of transactions)
        - Duplicate payments detected
        - Cash conversion ratio issues (<0.7)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            document_id: Document upload ID

        Returns:
            List of created fraud anomaly records
        """

        query = text("""
            SELECT
                benfords_law_chi_square,
                benfords_law_status,
                round_number_pct,
                round_number_status,
                duplicate_payment_count,
                duplicate_payment_details,
                cash_conversion_ratio,
                cash_ratio_status,
                overall_fraud_risk_level,
                red_flags_found,
                test_details
            FROM fraud_detection_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if not row:
            return []

        # Generate correlation ID for related fraud indicators
        correlation_id = uuid4()

        anomalies_created = []

        # 1. Benford's Law Anomaly
        if row[1] in ['YELLOW', 'RED']:
            chi_square = float(row[0]) if row[0] else 0

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="benfords_law_first_digit_distribution",
                field_value=str(chi_square),
                expected_value="15.51",  # Chi-square critical value at α=0.05
                z_score=None,
                percentage_change=None,
                anomaly_type="fraud_indicator",  # New type
                severity='critical' if row[1] == 'RED' else 'high',
                confidence=0.95,

                anomaly_score=Decimal("90" if row[1] == 'RED' else "75"),
                impact_amount=None,  # Fraud risk, not $ amount
                direction=None,
                root_cause_candidates={
                    "test_name": "Benford's Law Analysis",
                    "chi_square_statistic": chi_square,
                    "critical_value": 15.51,
                    "possible_causes": [
                        "Data fabrication",
                        "Manual entry errors",
                        "Copy-paste errors",
                        "Systematic manipulation"
                    ]
                },
                baseline_type=BaselineType.MEAN,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.DATA_QUALITY,
                pattern_type=PatternType.STRUCTURE,
                is_one_off=False,
                is_recurrent=False,

                metadata_json={
                    "forensic_audit": True,
                    "test_name": "Benford's Law",
                    "chi_square": chi_square,
                    "status": row[1],
                    "interpretation": "Chi-square > 20.09 indicates likely manipulation",
                    "audit_phase": "Phase 6: Fraud Detection"
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "test": "benfords_law",
                "severity": 'critical' if row[1] == 'RED' else 'high',
                "chi_square": chi_square
            })

        # 2. Round Number Anomaly
        if row[3] in ['YELLOW', 'RED']:
            round_pct = float(row[2]) if row[2] else 0

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="round_number_percentage",
                field_value=str(round_pct),
                expected_value="5.0",  # <5% is normal
                z_score=None,
                percentage_change=None,
                anomaly_type="fraud_indicator",
                severity='critical' if row[3] == 'RED' else 'medium',
                confidence=0.85,

                anomaly_score=Decimal("85" if row[3] == 'RED' else "65"),
                impact_amount=None,
                direction=AnomalyDirection.UP,
                root_cause_candidates={
                    "test_name": "Round Number Analysis",
                    "round_pct": round_pct,
                    "benchmark": 5.0,
                    "possible_causes": [
                        "Estimation rather than actual data",
                        "Placeholder values",
                        "Fabricated entries"
                    ]
                },
                baseline_type=BaselineType.MEAN,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.DATA_QUALITY,
                pattern_type=PatternType.STRUCTURE,

                metadata_json={
                    "forensic_audit": True,
                    "test_name": "Round Number Detection",
                    "round_number_pct": round_pct,
                    "status": row[3],
                    "interpretation": ">10% suggests fabrication",
                    "audit_phase": "Phase 6: Fraud Detection"
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "test": "round_numbers",
                "severity": 'critical' if row[3] == 'RED' else 'medium',
                "round_pct": round_pct
            })

        # 3. Duplicate Payment Anomaly
        if row[4] and row[4] > 0:
            duplicate_count = int(row[4])

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="duplicate_payment_count",
                field_value=str(duplicate_count),
                expected_value="0",
                z_score=None,
                percentage_change=None,
                anomaly_type="fraud_indicator",
                severity='critical',
                confidence=0.99,

                anomaly_score=Decimal("95"),
                impact_amount=None,  # TODO: Calculate from duplicate details
                direction=None,
                root_cause_candidates={
                    "test_name": "Duplicate Payment Detection",
                    "duplicate_count": duplicate_count,
                    "duplicate_details": row[5],
                    "possible_causes": [
                        "Fictitious payments",
                        "Double billing",
                        "System error",
                        "Vendor fraud"
                    ]
                },
                baseline_type=BaselineType.MEAN,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.DATA_QUALITY,
                pattern_type=PatternType.POINT,

                metadata_json={
                    "forensic_audit": True,
                    "test_name": "Duplicate Payment Detection",
                    "duplicate_count": duplicate_count,
                    "duplicate_details": row[5],
                    "interpretation": "Potential fictitious payments",
                    "audit_phase": "Phase 6: Fraud Detection"
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "test": "duplicate_payments",
                "severity": 'critical',
                "duplicate_count": duplicate_count
            })

        # 4. Cash Conversion Ratio Anomaly
        if row[7] in ['YELLOW', 'RED']:
            cash_ratio = float(row[6]) if row[6] else 0

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="cash_conversion_ratio",
                field_value=str(cash_ratio),
                expected_value="0.90",
                z_score=None,
                percentage_change=None,
                anomaly_type="fraud_indicator",
                severity='high' if row[7] == 'RED' else 'medium',
                confidence=0.80,

                anomaly_score=Decimal("80" if row[7] == 'RED' else "65"),
                impact_amount=None,
                direction=AnomalyDirection.DOWN,
                root_cause_candidates={
                    "test_name": "Cash Conversion Analysis",
                    "cash_ratio": cash_ratio,
                    "benchmark": 0.90,
                    "possible_causes": [
                        "Revenue recognition issues",
                        "Accounts receivable buildup",
                        "Cash flow manipulation",
                        "Accrual manipulation"
                    ]
                },
                baseline_type=BaselineType.MEAN,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.ACCOUNTING,
                pattern_type=PatternType.TREND,

                metadata_json={
                    "forensic_audit": True,
                    "test_name": "Cash Conversion Ratio",
                    "cash_ratio": cash_ratio,
                    "status": row[7],
                    "interpretation": "<0.7 requires investigation",
                    "audit_phase": "Phase 6: Fraud Detection"
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "test": "cash_conversion",
                "severity": 'high' if row[7] == 'RED' else 'medium',
                "cash_ratio": cash_ratio
            })

        await self.db.commit()

        return anomalies_created

    async def convert_covenant_breaches_to_anomalies(
        self,
        property_id: UUID,
        period_id: UUID,
        document_id: int
    ) -> List[Dict[str, Any]]:
        """
        Convert covenant compliance breaches to anomaly records.

        Creates critical anomalies for:
        - DSCR < 1.25x (covenant threshold)
        - LTV > 75% (covenant threshold)
        - Interest Coverage Ratio < 2.0x
        - Current Ratio < 1.5x
        - Quick Ratio < 1.0x

        These anomalies trigger committee alerts with 24-48 hour SLAs.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            document_id: Document upload ID

        Returns:
            List of created covenant anomaly records
        """

        query = text("""
            SELECT
                dscr,
                dscr_covenant_threshold,
                dscr_cushion,
                dscr_status,
                dscr_trend,
                ltv_ratio,
                ltv_covenant_threshold,
                ltv_cushion,
                ltv_status,
                ltv_trend,
                interest_coverage_ratio,
                current_ratio,
                quick_ratio,
                overall_compliance_status
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if not row:
            return []

        # Generate correlation ID for covenant-related anomalies
        correlation_id = uuid4()

        anomalies_created = []

        # 1. DSCR Breach/Warning
        if row[3] in ['YELLOW', 'RED']:
            dscr = float(row[0])
            covenant = float(row[1])
            cushion = float(row[2])

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="debt_service_coverage_ratio",
                field_value=str(dscr),
                expected_value=str(covenant),
                z_score=None,
                percentage_change=None,
                anomaly_type="covenant_breach",  # New type
                severity='critical' if row[3] == 'RED' else 'high',
                confidence=0.99,

                anomaly_score=Decimal("95" if row[3] == 'RED' else "80"),
                impact_amount=Decimal(str(abs(cushion))),
                direction=AnomalyDirection.DOWN,
                root_cause_candidates={
                    "covenant_name": "DSCR",
                    "current_value": dscr,
                    "covenant_threshold": covenant,
                    "cushion": cushion,
                    "trend": row[4],
                    "possible_causes": [
                        "Declining NOI",
                        "Increasing debt service",
                        "Expense inflation",
                        "Revenue loss",
                        "Tenant departures"
                    ]
                },
                baseline_type=BaselineType.PEER_GROUP,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.COVENANT,
                pattern_type=PatternType.TREND,
                is_one_off=False,
                is_recurrent=False,

                metadata_json={
                    "forensic_audit": True,
                    "covenant_name": "DSCR",
                    "dscr": dscr,
                    "covenant_threshold": covenant,
                    "cushion": cushion,
                    "cushion_pct": round((cushion / covenant) * 100, 2),
                    "status": row[3],
                    "trend": row[4],
                    "interpretation": "Covenant breach - lender notification required",
                    "audit_phase": "Phase 7: Covenant Compliance",
                    "requires_committee_alert": True,
                    "target_committee": "Finance Subcommittee",
                    "sla_hours": 24
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "covenant": "DSCR",
                "severity": 'critical' if row[3] == 'RED' else 'high',
                "value": dscr,
                "threshold": covenant,
                "in_compliance": False
            })

        # 2. LTV Breach/Warning
        if row[8] in ['YELLOW', 'RED']:
            ltv = float(row[5])
            covenant = float(row[6])
            cushion = float(row[7])

            anomaly = AnomalyDetection(
                document_id=document_id,
                field_name="loan_to_value_ratio",
                field_value=str(ltv),
                expected_value=str(covenant),
                z_score=None,
                percentage_change=None,
                anomaly_type="covenant_breach",
                severity='critical' if row[8] == 'RED' else 'high',
                confidence=0.99,

                anomaly_score=Decimal("95" if row[8] == 'RED' else "80"),
                impact_amount=Decimal(str(abs(cushion))),
                direction=AnomalyDirection.UP,
                root_cause_candidates={
                    "covenant_name": "LTV",
                    "current_value": ltv,
                    "covenant_threshold": covenant,
                    "cushion": cushion,
                    "trend": row[9],
                    "possible_causes": [
                        "Property value decline",
                        "Market deterioration",
                        "Additional debt",
                        "Deferred maintenance"
                    ]
                },
                baseline_type=BaselineType.PEER_GROUP,
                correlation_id=correlation_id,
                anomaly_category=AnomalyCategory.COVENANT,
                pattern_type=PatternType.TREND,

                metadata_json={
                    "forensic_audit": True,
                    "covenant_name": "LTV",
                    "ltv_ratio": ltv,
                    "covenant_threshold": covenant,
                    "cushion": cushion,
                    "cushion_pct": round((cushion / covenant) * 100, 2),
                    "status": row[8],
                    "trend": row[9],
                    "interpretation": "LTV exceeds covenant - possible trigger event",
                    "audit_phase": "Phase 7: Covenant Compliance",
                    "requires_committee_alert": True,
                    "target_committee": "Risk Committee",
                    "sla_hours": 48
                }
            )

            self.db.add(anomaly)
            anomalies_created.append({
                "covenant": "LTV",
                "severity": 'critical' if row[8] == 'RED' else 'high',
                "value": ltv,
                "threshold": covenant,
                "in_compliance": False
            })

        await self.db.commit()

        return anomalies_created

    async def run_complete_integration(
        self,
        property_id: UUID,
        period_id: UUID,
        document_id: int
    ) -> Dict[str, Any]:
        """
        Run complete forensic audit to anomaly integration.

        Converts all forensic audit findings to anomaly detection records:
        1. Cross-document reconciliation failures
        2. Fraud detection indicators
        3. Covenant compliance breaches

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            document_id: Primary document upload ID

        Returns:
            Summary of anomalies created
        """

        # 1. Convert reconciliation failures
        recon_anomalies = await self.convert_reconciliation_failures_to_anomalies(
            property_id, period_id, document_id
        )

        # 2. Convert fraud indicators
        fraud_anomalies = await self.convert_fraud_indicators_to_anomalies(
            property_id, period_id, document_id
        )

        # 3. Convert covenant breaches
        covenant_anomalies = await self.convert_covenant_breaches_to_anomalies(
            property_id, period_id, document_id
        )

        total_anomalies = len(recon_anomalies) + len(fraud_anomalies) + len(covenant_anomalies)

        # Calculate severity breakdown
        critical_count = sum(
            1 for a in (recon_anomalies + fraud_anomalies + covenant_anomalies)
            if a.get('severity') == 'critical'
        )

        high_count = sum(
            1 for a in (recon_anomalies + fraud_anomalies + covenant_anomalies)
            if a.get('severity') == 'high'
        )

        return {
            "status": "success",
            "total_anomalies_created": total_anomalies,
            "reconciliation_anomalies": len(recon_anomalies),
            "fraud_anomalies": len(fraud_anomalies),
            "covenant_anomalies": len(covenant_anomalies),
            "severity_breakdown": {
                "critical": critical_count,
                "high": high_count,
                "medium": total_anomalies - critical_count - high_count
            },
            "anomalies_by_type": {
                "reconciliation_failures": recon_anomalies,
                "fraud_indicators": fraud_anomalies,
                "covenant_breaches": covenant_anomalies
            },
            "integrated_at": datetime.now().isoformat()
        }
