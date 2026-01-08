"""
Audit Scorecard Generator Service

Aggregates all forensic audit results and generates executive-level scorecard:
- Overall health score (0-100)
- Traffic light status (GREEN/YELLOW/RED)
- Audit opinion (UNQUALIFIED/QUALIFIED/ADVERSE)
- Priority risks (Top 5)
- Action items with ownership
- Financial performance summary
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from enum import Enum


class TrafficLightStatus(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class AuditOpinion(str, Enum):
    UNQUALIFIED = "UNQUALIFIED"  # Clean opinion - all critical tests passed
    QUALIFIED = "QUALIFIED"  # Some issues but manageable
    ADVERSE = "ADVERSE"  # Significant issues requiring immediate attention


class RiskSeverity(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class AuditScorecardGeneratorService:
    """
    Generates executive-level audit scorecard by aggregating results from:
    - Cross-document reconciliations
    - Fraud detection tests
    - Covenant compliance monitoring
    - Tenant risk analysis
    - Collections quality metrics
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _status_from_thresholds(
        value: Optional[float],
        green_threshold: float,
        yellow_threshold: float,
        higher_is_better: bool = True
    ) -> TrafficLightStatus:
        if value is None:
            return TrafficLightStatus.YELLOW
        if higher_is_better:
            if value >= green_threshold:
                return TrafficLightStatus.GREEN
            if value >= yellow_threshold:
                return TrafficLightStatus.YELLOW
            return TrafficLightStatus.RED
        if value <= green_threshold:
            return TrafficLightStatus.GREEN
        if value <= yellow_threshold:
            return TrafficLightStatus.YELLOW
        return TrafficLightStatus.RED

    async def generate_complete_scorecard(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate complete executive audit scorecard.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Complete scorecard for CEO dashboard
        """

        # Get property and period info
        property_info = await self._get_property_info(property_id, period_id)

        # Calculate overall health score (0-100)
        health_score = await self.calculate_overall_health_score(property_id, period_id)

        # Determine traffic light status
        traffic_light = await self.determine_traffic_light_status(property_id, period_id)

        # Generate audit opinion
        audit_opinion = await self.generate_audit_opinion(property_id, period_id)

        # Get traffic light metrics
        metrics = await self._get_traffic_light_metrics(property_id, period_id)

        # Identify priority risks
        priority_risks = await self.identify_priority_risks(property_id, period_id)

        # Get financial performance summary
        financial_summary = await self._get_financial_summary(property_id, period_id)

        # Create action items
        action_items = await self.create_action_items(property_id, period_id, priority_risks)

        # Get reconciliation summary
        reconciliation_summary = await self._get_reconciliation_summary(property_id, period_id)

        # Get fraud detection summary
        fraud_summary = await self._get_fraud_detection_summary(property_id, period_id)

        # Get covenant summary
        covenant_summary = await self._get_covenant_summary(property_id, period_id)

        scorecard = {
            "overall_health_score": health_score,
            "traffic_light_status": traffic_light.value,
            "audit_opinion": audit_opinion.value,
            "property_id": str(property_id),
            "property_name": property_info['property_name'],
            "period_id": str(period_id),
            "period_label": property_info['period_label'],
            "metrics": metrics,
            "priority_risks": priority_risks,
            "financial_summary": financial_summary,
            "action_items": action_items,
            "reconciliation_summary": reconciliation_summary,
            "fraud_detection_summary": fraud_summary,
            "covenant_summary": covenant_summary,
            "generated_at": datetime.now().isoformat(),
            "generated_by": "REIMS Forensic Audit Engine v1.0"
        }

        # Save scorecard to database
        await self.save_scorecard(property_id, period_id, scorecard)

        return scorecard

    async def calculate_overall_health_score(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> int:
        """
        Calculate overall property health score (0-100).

        Scoring components:
        - Mathematical Integrity: 20 points
        - Cross-Doc Reconciliation: 25 points
        - Fraud Detection: 20 points
        - Covenant Compliance: 20 points
        - Collections Quality: 15 points

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Score from 0-100
        """

        total_score = 0

        # 1. Mathematical Integrity (20 points)
        # All balance sheet equations, IS calculations, CF integrity must pass
        validation_query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN vr.passed THEN 1 ELSE 0 END) as passed
            FROM validation_results vr
            JOIN document_uploads du ON du.id = vr.upload_id
            WHERE du.property_id = :property_id
            AND du.period_id = :period_id
            AND du.is_active = true
        """)

        validation_result = await self.db.execute(
            validation_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        validation_row = validation_result.fetchone()

        if validation_row and validation_row[0] > 0:
            pass_rate = (validation_row[1] or 0) / validation_row[0]
            math_integrity_score = int(round(pass_rate * 20))
        else:
            math_integrity_score = 20  # No data, assume pass
        total_score += math_integrity_score

        # 2. Cross-Document Reconciliation (25 points)
        recon_query = text("""
            SELECT
                COUNT(*) as total_reconciliations,
                SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)

        recon_result = await self.db.execute(
            recon_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        recon_row = recon_result.fetchone()

        if recon_row and recon_row[0] > 0:
            recon_pass_rate = recon_row[1] / recon_row[0]
            recon_score = int(recon_pass_rate * 25)
        else:
            recon_score = 25  # No data, assume pass

        total_score += recon_score

        # 3. Fraud Detection (20 points)
        fraud_query = text("""
            SELECT overall_fraud_risk_level
            FROM fraud_detection_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        fraud_result = await self.db.execute(
            fraud_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        fraud_row = fraud_result.fetchone()

        if fraud_row:
            if fraud_row[0] == 'GREEN':
                fraud_score = 20
            elif fraud_row[0] == 'YELLOW':
                fraud_score = 15
            else:  # RED
                fraud_score = 5
        else:
            fraud_score = 20  # No data, assume pass

        total_score += fraud_score

        # 4. Covenant Compliance (20 points)
        covenant_query = text("""
            SELECT overall_compliance_status
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        covenant_result = await self.db.execute(
            covenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        covenant_row = covenant_result.fetchone()

        if covenant_row:
            if covenant_row[0] == 'GREEN':
                covenant_score = 20
            elif covenant_row[0] == 'YELLOW':
                covenant_score = 12
            else:  # RED
                covenant_score = 0
        else:
            covenant_score = 20  # No data, assume pass

        total_score += covenant_score

        # 5. Collections Quality (15 points)
        collections_query = text("""
            SELECT revenue_quality_score
            FROM collections_revenue_quality
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        collections_result = await self.db.execute(
            collections_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        collections_row = collections_result.fetchone()

        if collections_row:
            # Revenue quality score is 0-100, convert to 0-15
            collections_score = int(collections_row[0] * 0.15)
        else:
            collections_score = 15  # No data, assume pass

        total_score += collections_score

        return min(total_score, 100)  # Cap at 100

    async def determine_traffic_light_status(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> TrafficLightStatus:
        """
        Determine overall traffic light status based on all tests.

        Logic:
        - Any critical failure → RED
        - Any covenant breach → RED
        - Multiple warnings → YELLOW
        - All pass → GREEN

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Traffic light status
        """

        # Check for critical reconciliation failures
        recon_query = text("""
            SELECT COUNT(*)
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND status = 'FAIL'
            AND is_material = true
        """)

        recon_result = await self.db.execute(
            recon_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        critical_failures = recon_result.scalar()

        if critical_failures > 0:
            return TrafficLightStatus.RED

        # Check covenant breaches
        covenant_query = text("""
            SELECT overall_compliance_status
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        covenant_result = await self.db.execute(
            covenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        covenant_row = covenant_result.fetchone()

        if covenant_row and covenant_row[0] == 'RED':
            return TrafficLightStatus.RED

        # Check fraud indicators
        fraud_query = text("""
            SELECT overall_fraud_risk_level
            FROM fraud_detection_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        fraud_result = await self.db.execute(
            fraud_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        fraud_row = fraud_result.fetchone()

        if fraud_row and fraud_row[0] == 'RED':
            return TrafficLightStatus.RED

        # Check for warnings
        if (covenant_row and covenant_row[0] == 'YELLOW') or (fraud_row and fraud_row[0] == 'YELLOW'):
            return TrafficLightStatus.YELLOW

        return TrafficLightStatus.GREEN

    async def generate_audit_opinion(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> AuditOpinion:
        """
        Generate audit opinion based on test results.

        Opinions:
        - UNQUALIFIED: Clean opinion - all critical tests passed
        - QUALIFIED: Some issues but financial statements are fairly presented
        - ADVERSE: Significant issues - financial statements may be materially misstated

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Audit opinion
        """

        # Count critical failures
        critical_query = text("""
            SELECT COUNT(*)
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND status = 'FAIL'
            AND rule_code IN ('A-3.1', 'A-3.4', 'A-3.5')  -- Critical reconciliations
        """)

        critical_result = await self.db.execute(
            critical_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        critical_failures = critical_result.scalar()

        # Check covenant breaches
        covenant_query = text("""
            SELECT overall_compliance_status
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        covenant_result = await self.db.execute(
            covenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        covenant_row = covenant_result.fetchone()
        covenant_breach = covenant_row and covenant_row[0] == 'RED'

        # Determine opinion
        if critical_failures >= 2 or covenant_breach:
            return AuditOpinion.ADVERSE
        elif critical_failures == 1:
            return AuditOpinion.QUALIFIED
        else:
            return AuditOpinion.UNQUALIFIED

    async def identify_priority_risks(
        self,
        property_id: UUID,
        period_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Identify top priority risks requiring management attention.

        Prioritization criteria:
        1. Covenant breaches (HIGH)
        2. Critical reconciliation failures (HIGH)
        3. Fraud indicators (HIGH/MODERATE)
        4. Tenant concentration risk (MODERATE)
        5. Lease rollover risk (MODERATE)
        6. Collections issues (LOW)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            limit: Maximum number of risks to return

        Returns:
            List of priority risks
        """

        risks: List[Dict[str, Any]] = []
        severity_rank = {
            RiskSeverity.HIGH.value: 3,
            RiskSeverity.MODERATE.value: 2,
            RiskSeverity.LOW.value: 1
        }

        def add_risk(
            severity: str,
            category: str,
            description: str,
            action_required: str,
            owner: str,
            due_days: Optional[int],
            related_metric: Optional[str],
            financial_impact: Optional[float] = None,
            sort_order: int = 0
        ) -> None:
            risks.append({
                "severity": severity,
                "category": category,
                "description": description,
                "financial_impact": financial_impact,
                "action_required": action_required,
                "owner": owner,
                "due_date": (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d") if due_days else None,
                "related_metric": related_metric,
                "_rank": severity_rank.get(severity, 1),
                "_sort": sort_order
            })

        covenant_query = text("""
            SELECT
                dscr,
                dscr_status,
                dscr_covenant_threshold,
                dscr_cushion,
                ltv_ratio,
                ltv_status,
                ltv_covenant_threshold,
                ltv_cushion
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        covenant_result = await self.db.execute(
            covenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        covenant_row = covenant_result.fetchone()

        if covenant_row:
            dscr_value = float(covenant_row[0]) if covenant_row[0] is not None else None
            dscr_status = covenant_row[1]
            dscr_covenant = float(covenant_row[2]) if covenant_row[2] is not None else 1.25

            if dscr_value is not None and dscr_status in ['YELLOW', 'RED']:
                add_risk(
                    RiskSeverity.HIGH.value if dscr_status == 'RED' else RiskSeverity.MODERATE.value,
                    "DSCR Covenant Breach" if dscr_status == 'RED' else "DSCR Trending Down",
                    f"Current DSCR: {dscr_value:.2f}x (covenant minimum: {dscr_covenant:.2f}x)",
                    "Notify lender immediately; develop remediation plan" if dscr_status == 'RED'
                    else "Focus on expense control; evaluate rent increases",
                    "CFO",
                    30 if dscr_status == 'RED' else 90,
                    "DSCR",
                    sort_order=10
                )

            ltv_value = float(covenant_row[4]) if covenant_row[4] is not None else None
            ltv_status = covenant_row[5]
            ltv_covenant = float(covenant_row[6]) if covenant_row[6] is not None else 75.0

            if ltv_value is not None and ltv_status in ['YELLOW', 'RED']:
                add_risk(
                    RiskSeverity.HIGH.value if ltv_status == 'RED' else RiskSeverity.MODERATE.value,
                    "LTV Covenant Breach" if ltv_status == 'RED' else "LTV Approaching Covenant",
                    f"Current LTV: {ltv_value:.1f}% (covenant maximum: {ltv_covenant:.0f}%)",
                    "Review refinancing or paydown options" if ltv_status == 'RED'
                    else "Monitor leverage; evaluate valuation updates",
                    "Treasury",
                    45 if ltv_status == 'RED' else 90,
                    "LTV",
                    sort_order=20
                )

        tenant_query = text("""
            SELECT
                top_1_tenant_pct,
                top_3_tenant_pct,
                top_5_tenant_pct,
                lease_rollover_12mo_pct,
                occupancy_rate
            FROM tenant_risk_analysis
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        tenant_result = await self.db.execute(
            tenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        tenant_row = tenant_result.fetchone()

        if tenant_row:
            top_1 = float(tenant_row[0]) if tenant_row[0] is not None else None
            top_3 = float(tenant_row[1]) if tenant_row[1] is not None else None
            top_5 = float(tenant_row[2]) if tenant_row[2] is not None else None
            rollover_12 = float(tenant_row[3]) if tenant_row[3] is not None else None

            if rollover_12 is not None and rollover_12 >= 15.0:
                severity = RiskSeverity.HIGH.value if rollover_12 >= 25.0 else RiskSeverity.MODERATE.value
                add_risk(
                    severity,
                    "Lease Rollover Risk",
                    f"{rollover_12:.0f}% of annual rent expires in next 12 months",
                    "Begin renewal negotiations; build TI reserve",
                    "Leasing Director",
                    60,
                    "Lease Rollover (12mo)",
                    sort_order=30
                )

            if top_1 is not None or top_3 is not None or top_5 is not None:
                concentration_pct = top_1 if top_1 is not None else (top_3 or top_5 or 0)
                severity = None
                if top_1 is not None and top_1 >= 20.0:
                    severity = RiskSeverity.HIGH.value
                elif (top_3 is not None and top_3 >= 50.0) or (top_5 is not None and top_5 >= 60.0):
                    severity = RiskSeverity.MODERATE.value

                if severity:
                    label_pct = top_5 if top_5 is not None else concentration_pct
                    add_risk(
                        severity,
                        "Tenant Concentration",
                        f"Top tenants represent {label_pct:.0f}% of total rent",
                        "Monitor credit quality; diversify tenant mix",
                        "Asset Management",
                        None,
                        "Tenant Concentration",
                        sort_order=40
                    )

        recon_query = text("""
            SELECT reconciliation_type, difference, explanation
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND status = 'FAIL'
            ORDER BY ABS(difference) DESC
            LIMIT 1
        """)

        recon_result = await self.db.execute(
            recon_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        recon_row = recon_result.fetchone()

        if recon_row:
            add_risk(
                RiskSeverity.HIGH.value,
                "Reconciliation Failure",
                recon_row[2] or "Material reconciliation failure detected",
                "Investigate and correct discrepancy",
                "Controller",
                7,
                recon_row[0],
                financial_impact=abs(float(recon_row[1])) if recon_row[1] is not None else None,
                sort_order=15
            )

        fraud_query = text("""
            SELECT overall_fraud_risk_level, red_flags_found
            FROM fraud_detection_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        fraud_result = await self.db.execute(
            fraud_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        fraud_row = fraud_result.fetchone()

        if fraud_row and fraud_row[0] in ['YELLOW', 'RED']:
            severity = RiskSeverity.HIGH.value if fraud_row[0] == 'RED' else RiskSeverity.MODERATE.value
            red_flags = int(fraud_row[1]) if fraud_row[1] is not None else 0
            add_risk(
                severity,
                "Fraud Risk Indicators",
                f"{red_flags} red flags detected in forensic tests",
                "Review flagged transactions; expand testing scope",
                "Internal Audit",
                30,
                "Fraud Detection",
                sort_order=25
            )

        collections_query = text("""
            SELECT days_sales_outstanding, revenue_quality_score
            FROM collections_revenue_quality
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        collections_result = await self.db.execute(
            collections_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        collections_row = collections_result.fetchone()

        if collections_row:
            dso = float(collections_row[0]) if collections_row[0] is not None else None
            quality_score = float(collections_row[1]) if collections_row[1] is not None else None

            if dso is not None and dso >= 45.0:
                severity = RiskSeverity.HIGH.value if dso >= 60.0 else RiskSeverity.MODERATE.value
                add_risk(
                    severity,
                    "Collections Timing",
                    f"DSO at {dso:.0f} days exceeds target",
                    "Tighten collections; review tenant payment terms",
                    "Controller",
                    45,
                    "DSO",
                    sort_order=50
                )
            elif quality_score is not None and quality_score < 70.0:
                add_risk(
                    RiskSeverity.MODERATE.value,
                    "Revenue Quality",
                    f"Revenue quality score at {quality_score:.0f} is below target",
                    "Review collection procedures; monitor bad debt risk",
                    "Asset Management",
                    60,
                    "Revenue Quality",
                    sort_order=55
                )

        completeness_query = text("""
            SELECT completeness_percentage
            FROM document_completeness_matrix
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        completeness_result = await self.db.execute(
            completeness_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        completeness_row = completeness_result.fetchone()

        if completeness_row and completeness_row[0] is not None:
            completeness_pct = float(completeness_row[0])
            if completeness_pct < 95.0:
                severity = RiskSeverity.HIGH.value if completeness_pct < 80.0 else RiskSeverity.MODERATE.value
                add_risk(
                    severity,
                    "Document Completeness",
                    f"Completeness at {completeness_pct:.0f}% - missing audit inputs",
                    "Request missing documents; validate data sources",
                    "Controller",
                    14,
                    "Document Completeness",
                    sort_order=60
                )

        risks.sort(key=lambda r: (-r["_rank"], r["_sort"]))
        trimmed = risks[:limit]
        formatted = []
        for idx, risk in enumerate(trimmed, start=1):
            formatted.append({
                "risk_id": idx,
                "severity": risk["severity"],
                "category": risk["category"],
                "description": risk["description"],
                "financial_impact": risk["financial_impact"],
                "action_required": risk["action_required"],
                "owner": risk["owner"],
                "due_date": risk["due_date"],
                "related_metric": risk["related_metric"]
            })

        return formatted

    async def create_action_items(
        self,
        property_id: UUID,
        period_id: UUID,
        priority_risks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create action items from priority risks.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            priority_risks: List of identified risks

        Returns:
            List of action items
        """

        action_items = []
        action_id = 1

        for risk in priority_risks:
            if risk['severity'] == RiskSeverity.HIGH.value:
                priority = "URGENT"
            elif risk['severity'] == RiskSeverity.MODERATE.value:
                priority = "HIGH"
            else:
                priority = "MEDIUM"

            action_items.append({
                "action_id": action_id,
                "priority": priority,
                "description": risk['action_required'],
                "assigned_to": risk['owner'],
                "due_date": risk['due_date'] or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "status": "PENDING",
                "related_risk_id": risk['risk_id']
            })
            action_id += 1

        return action_items

    async def _get_property_info(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get property and period information."""

        query = text("""
            SELECT
                p.property_code,
                p.property_name,
                fp.period_year,
                fp.period_month
            FROM properties p
            JOIN financial_periods fp ON fp.property_id = p.id
            WHERE p.id = :property_id
            AND fp.id = :period_id
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if row:
            return {
                "property_code": row[0],
                "property_name": row[1],
                "period_label": f"{row[2]}-{row[3]:02d}"
            }
        else:
            return {
                "property_code": "UNKNOWN",
                "property_name": "Unknown Property",
                "period_label": "Unknown Period"
            }

    async def _get_traffic_light_metrics(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all traffic light metrics."""

        metrics: List[Dict[str, Any]] = []

        def add_metric(
            name: str,
            current_value: Optional[float],
            target_value: Optional[float],
            status: TrafficLightStatus,
            trend: str = "STABLE"
        ) -> None:
            variance_pct = None
            if current_value is not None and target_value not in (None, 0):
                variance_pct = round(((current_value - target_value) / target_value) * 100, 2)
            metrics.append({
                "metric_name": name,
                "current_value": current_value,
                "target_value": target_value,
                "status": status.value if isinstance(status, TrafficLightStatus) else status,
                "trend": trend,
                "variance_pct": variance_pct
            })

        validation_query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN vr.passed THEN 1 ELSE 0 END) as passed
            FROM validation_results vr
            JOIN document_uploads du ON du.id = vr.upload_id
            WHERE du.property_id = :property_id
            AND du.period_id = :period_id
            AND du.is_active = true
        """)

        validation_result = await self.db.execute(
            validation_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        validation_row = validation_result.fetchone()

        if validation_row and validation_row[0] > 0:
            pass_rate_pct = round(((validation_row[1] or 0) / validation_row[0]) * 100, 1)
            status = self._status_from_thresholds(pass_rate_pct, 100.0, 95.0, higher_is_better=True)
            add_metric("Mathematical Integrity", pass_rate_pct, 100.0, status)

        completeness_query = text("""
            SELECT completeness_percentage
            FROM document_completeness_matrix
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        completeness_result = await self.db.execute(
            completeness_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        completeness_row = completeness_result.fetchone()

        if completeness_row and completeness_row[0] is not None:
            completeness_pct = float(completeness_row[0])
            status = self._status_from_thresholds(completeness_pct, 100.0, 95.0, higher_is_better=True)
            add_metric("Document Completeness", completeness_pct, 100.0, status)

        recon_summary = await self._get_reconciliation_summary(property_id, period_id)
        if recon_summary.get("total_reconciliations", 0) > 0:
            pass_rate = recon_summary.get("pass_rate_pct", recon_summary.get("pass_rate", 0))
            status = self._status_from_thresholds(pass_rate, 100.0, 90.0, higher_is_better=True)
            add_metric("Cross-Doc Reconciliation", pass_rate, 100.0, status)

        covenant_summary = await self._get_covenant_summary(property_id, period_id)
        dscr_value = covenant_summary.get("dscr")
        if dscr_value is not None:
            dscr_status = covenant_summary.get("dscr_status") or TrafficLightStatus.YELLOW.value
            if dscr_status not in ["GREEN", "YELLOW", "RED"]:
                dscr_status = TrafficLightStatus.YELLOW.value
            add_metric(
                "DSCR",
                dscr_value,
                covenant_summary.get("dscr_covenant", 1.25),
                dscr_status
            )

        ltv_value = covenant_summary.get("ltv_ratio") or covenant_summary.get("ltv")
        if ltv_value is not None:
            ltv_status = covenant_summary.get("ltv_status") or TrafficLightStatus.YELLOW.value
            if ltv_status not in ["GREEN", "YELLOW", "RED"]:
                ltv_status = TrafficLightStatus.YELLOW.value
            add_metric(
                "LTV Ratio",
                ltv_value,
                covenant_summary.get("ltv_covenant", 75.0),
                ltv_status
            )

        metrics_query = text("""
            SELECT
                total_revenue,
                net_operating_income,
                operating_margin,
                occupancy_rate
            FROM financial_metrics
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY updated_at DESC NULLS LAST, calculated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """)

        metrics_result = await self.db.execute(
            metrics_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        metrics_row = metrics_result.fetchone()

        occupancy_rate = None
        noi_margin_pct = None
        if metrics_row:
            if metrics_row[3] is not None:
                occupancy_rate = float(metrics_row[3])
            if metrics_row[2] is not None:
                noi_margin_pct = float(metrics_row[2]) * 100
            elif metrics_row[0] and metrics_row[1]:
                noi_margin_pct = float(metrics_row[1]) / float(metrics_row[0]) * 100

        tenant_query = text("""
            SELECT lease_rollover_12mo_pct, occupancy_rate
            FROM tenant_risk_analysis
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        tenant_result = await self.db.execute(
            tenant_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        tenant_row = tenant_result.fetchone()

        if tenant_row:
            lease_rollover_pct = float(tenant_row[0]) if tenant_row[0] is not None else None
            if occupancy_rate is None and tenant_row[1] is not None:
                occupancy_rate = float(tenant_row[1])
            if lease_rollover_pct is not None:
                status = self._status_from_thresholds(lease_rollover_pct, 15.0, 25.0, higher_is_better=False)
                add_metric("Lease Rollover (12mo)", lease_rollover_pct, 25.0, status)

        if occupancy_rate is not None:
            status = self._status_from_thresholds(occupancy_rate, 90.0, 85.0, higher_is_better=True)
            add_metric("Occupancy Rate", occupancy_rate, 90.0, status)

        if noi_margin_pct is not None:
            status = self._status_from_thresholds(noi_margin_pct, 55.0, 50.0, higher_is_better=True)
            add_metric("NOI Margin", noi_margin_pct, 55.0, status)

        collections_query = text("""
            SELECT
                days_sales_outstanding,
                revenue_quality_score,
                cash_conversion_ratio,
                dso_status
            FROM collections_revenue_quality
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        collections_result = await self.db.execute(
            collections_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        collections_row = collections_result.fetchone()

        if collections_row:
            dso = float(collections_row[0]) if collections_row[0] is not None else None
            quality_score = float(collections_row[1]) if collections_row[1] is not None else None
            cash_conversion = float(collections_row[2]) if collections_row[2] is not None else None
            dso_status = collections_row[3] if collections_row[3] else None

            if dso is not None:
                status = self._status_from_thresholds(dso, 30.0, 45.0, higher_is_better=False)
                if dso_status in ['GREEN', 'YELLOW', 'RED']:
                    status = TrafficLightStatus(dso_status)
                add_metric("DSO (Days)", dso, 30.0, status)

            if quality_score is not None:
                status = self._status_from_thresholds(quality_score, 80.0, 70.0, higher_is_better=True)
                add_metric("Revenue Quality Score", quality_score, 80.0, status)

            if cash_conversion is not None:
                status = self._status_from_thresholds(cash_conversion, 0.9, 0.8, higher_is_better=True)
                add_metric("Cash Conversion Ratio", cash_conversion, 0.9, status)

        return metrics

    async def _get_financial_summary(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get financial performance summary."""

        metrics_query = text("""
            SELECT
                total_revenue,
                total_expenses,
                net_operating_income,
                net_income,
                ending_cash_balance,
                total_cash_position,
                operating_margin,
                occupancy_rate
            FROM financial_metrics
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY updated_at DESC NULLS LAST, calculated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """)

        metrics_result = await self.db.execute(
            metrics_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        metrics_row = metrics_result.fetchone()

        total_revenue = float(metrics_row[0]) if metrics_row and metrics_row[0] is not None else 0.0
        total_expenses = float(metrics_row[1]) if metrics_row and metrics_row[1] is not None else 0.0
        noi = float(metrics_row[2]) if metrics_row and metrics_row[2] is not None else 0.0
        net_income = float(metrics_row[3]) if metrics_row and metrics_row[3] is not None else 0.0
        cash_balance = 0.0
        if metrics_row and metrics_row[4] is not None:
            cash_balance = float(metrics_row[4])
        elif metrics_row and metrics_row[5] is not None:
            cash_balance = float(metrics_row[5])

        noi_margin_pct = 0.0
        if metrics_row and metrics_row[6] is not None:
            noi_margin_pct = float(metrics_row[6]) * 100
        elif total_revenue:
            noi_margin_pct = (noi / total_revenue) * 100

        occupancy_rate = float(metrics_row[7]) if metrics_row and metrics_row[7] is not None else None
        if occupancy_rate is None:
            occupancy_query = text("""
                SELECT occupancy_rate
                FROM tenant_risk_analysis
                WHERE property_id = :property_id
                AND period_id = :period_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            occupancy_result = await self.db.execute(
                occupancy_query,
                {"property_id": str(property_id), "period_id": str(period_id)}
            )
            occupancy_row = occupancy_result.fetchone()
            if occupancy_row and occupancy_row[0] is not None:
                occupancy_rate = float(occupancy_row[0])

        dscr_query = text("""
            SELECT dscr
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        dscr_result = await self.db.execute(
            dscr_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        dscr_row = dscr_result.fetchone()
        dscr = float(dscr_row[0]) if dscr_row and dscr_row[0] is not None else None

        dso_query = text("""
            SELECT days_sales_outstanding
            FROM collections_revenue_quality
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        dso_result = await self.db.execute(
            dso_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        dso_row = dso_result.fetchone()
        dso = float(dso_row[0]) if dso_row and dso_row[0] is not None else None

        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "noi": noi,
            "net_income": net_income,
            "cash_balance": cash_balance,
            "noi_margin_pct": round(noi_margin_pct, 2),
            "key_ratios": {
                "dscr": dscr,
                "occupancy_rate": occupancy_rate,
                "dso_days": dso
            }
        }

    async def _get_reconciliation_summary(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get reconciliation summary."""

        query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) as warnings,
                SUM(CASE WHEN status = 'FAIL' AND is_material = true THEN 1 ELSE 0 END) as critical_failures
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if row and row[0] > 0:
            pass_rate = round((row[1] / row[0]) * 100, 2)
            return {
                "total_reconciliations": row[0],
                "passed": row[1],
                "failed": row[2],
                "warnings": row[3],
                "pass_rate": pass_rate,
                "pass_rate_pct": pass_rate,
                "critical_failures": row[4] or 0
            }
        else:
            return {
                "total_reconciliations": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "pass_rate": 0,
                "pass_rate_pct": 0,
                "critical_failures": 0
            }

    async def _get_fraud_detection_summary(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get fraud detection summary."""

        query = text("""
            SELECT
                benfords_law_chi_square,
                round_number_pct,
                duplicate_payment_count,
                cash_conversion_ratio,
                overall_fraud_risk_level
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

        if row:
            return {
                "overall_risk_level": row[4],
                "benfords_law_chi_square": float(row[0]) if row[0] else None,
                "benfords_law_threshold": 15.51,
                "round_number_pct": float(row[1]) if row[1] else None,
                "duplicate_payments_found": row[2],
                "cash_conversion_ratio": float(row[3]) if row[3] else None
            }
        else:
            return {
                "overall_risk_level": "GREEN",
                "benfords_law_chi_square": None,
                "round_number_pct": None,
                "duplicate_payments_found": 0,
                "cash_conversion_ratio": None
            }

    async def _get_covenant_summary(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get covenant compliance summary."""

        query = text("""
            SELECT
                dscr,
                dscr_status,
                dscr_covenant_threshold,
                ltv_ratio,
                ltv_status,
                ltv_covenant_threshold,
                current_ratio,
                quick_ratio
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

        if row:
            return {
                "dscr": float(row[0]) if row[0] else None,
                "dscr_status": row[1] or "UNKNOWN",
                "dscr_covenant": float(row[2]) if row[2] else 1.25,
                "ltv_ratio": float(row[3]) if row[3] else None,
                "ltv": float(row[3]) if row[3] else None,
                "ltv_status": row[4] or "UNKNOWN",
                "ltv_covenant": float(row[5]) if row[5] else 75.0,
                "current_ratio": float(row[6]) if row[6] else None,
                "quick_ratio": float(row[7]) if row[7] else None
            }
        else:
            return {
                "dscr": None,
                "dscr_status": "UNKNOWN",
                "dscr_covenant": 1.25,
                "ltv_ratio": None,
                "ltv": None,
                "ltv_status": "UNKNOWN",
                "ltv_covenant": 75.0,
                "current_ratio": None,
                "quick_ratio": None
            }

    async def save_scorecard(
        self,
        property_id: UUID,
        period_id: UUID,
        scorecard: Dict[str, Any]
    ) -> None:
        """
        Save scorecard to database.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            scorecard: Complete scorecard data
        """

        insert_query = text("""
            INSERT INTO audit_scorecard_summary (
                property_id,
                period_id,
                overall_health_score,
                traffic_light_status,
                audit_opinion,
                priority_risks,
                action_items,
                critical_issues_count,
                scorecard_data,
                created_at
            ) VALUES (
                :property_id,
                :period_id,
                :health_score,
                :traffic_light,
                :audit_opinion,
                :priority_risks,
                :action_items,
                :critical_count,
                :scorecard_data,
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                overall_health_score = EXCLUDED.overall_health_score,
                traffic_light_status = EXCLUDED.traffic_light_status,
                audit_opinion = EXCLUDED.audit_opinion,
                priority_risks = EXCLUDED.priority_risks,
                action_items = EXCLUDED.action_items,
                scorecard_data = EXCLUDED.scorecard_data,
                updated_at = NOW()
        """)

        critical_issues = len([r for r in scorecard['priority_risks'] if r['severity'] == 'HIGH'])

        await self.db.execute(
            insert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "health_score": scorecard['overall_health_score'],
                "traffic_light": scorecard['traffic_light_status'],
                "audit_opinion": scorecard['audit_opinion'],
                "priority_risks": scorecard['priority_risks'],
                "action_items": scorecard['action_items'],
                "critical_count": critical_issues,
                "scorecard_data": scorecard
            }
        )

        await self.db.commit()
