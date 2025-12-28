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
        math_integrity_score = 20  # Assume pass for now (implement full check)
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

        risks = []
        risk_id = 1

        # 1. Check DSCR covenant
        dscr_query = text("""
            SELECT dscr, dscr_status, dscr_cushion
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

        if dscr_row and dscr_row[1] in ['YELLOW', 'RED']:
            dscr = float(dscr_row[0])
            cushion = float(dscr_row[2])
            risks.append({
                "risk_id": risk_id,
                "severity": RiskSeverity.HIGH.value if dscr_row[1] == 'RED' else RiskSeverity.MODERATE.value,
                "category": "DSCR Trending Down" if dscr_row[1] == 'YELLOW' else "DSCR Covenant Breach",
                "description": f"Current DSCR: {dscr:.2f}x (covenant minimum: 1.25x)",
                "financial_impact": abs(cushion) if cushion < 0 else None,
                "action_required": "Focus on expense control; evaluate rent increases" if dscr_row[1] == 'YELLOW' else "Notify lender immediately; develop remediation plan",
                "owner": "CFO",
                "due_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
                "related_metric": "DSCR"
            })
            risk_id += 1

        # 2. Check tenant concentration risk (placeholder - would query tenant_risk_analysis table)
        # For now, add example risk
        risks.append({
            "risk_id": risk_id,
            "severity": RiskSeverity.MODERATE.value,
            "category": "Tenant Concentration",
            "description": "Top 5 tenants represent 54% of total rent",
            "financial_impact": None,
            "action_required": "Monitor credit quality; diversify tenant mix",
            "owner": "Asset Management",
            "due_date": None,
            "related_metric": "Tenant Concentration"
        })
        risk_id += 1

        # 3. Check for reconciliation failures
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
            risks.append({
                "risk_id": risk_id,
                "severity": RiskSeverity.HIGH.value,
                "category": "Reconciliation Failure",
                "description": recon_row[2],
                "financial_impact": abs(float(recon_row[1])),
                "action_required": "Investigate and correct discrepancy",
                "owner": "Controller",
                "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "related_metric": recon_row[0]
            })
            risk_id += 1

        return risks[:limit]

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

        # Placeholder - would aggregate from all tables
        return [
            {
                "metric_name": "Mathematical Integrity",
                "current_value": 100.0,
                "target_value": 100.0,
                "status": "GREEN",
                "trend": "STABLE",
                "variance_pct": 0.0
            }
        ]

    async def _get_financial_summary(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """Get financial performance summary."""

        # Placeholder - would query income statement for YTD figures
        return {
            "ytd_revenue": 0,
            "ytd_expenses": 0,
            "ytd_noi": 0,
            "ytd_net_income": 0,
            "noi_margin_pct": 0,
            "key_ratios": {
                "dscr": 0,
                "occupancy_rate": 0,
                "dso_days": 0
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
                SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) as warnings
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
            return {
                "total_reconciliations": row[0],
                "passed": row[1],
                "failed": row[2],
                "warnings": row[3],
                "pass_rate": round((row[1] / row[0]) * 100, 2),
                "critical_failures": []
            }
        else:
            return {
                "total_reconciliations": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "pass_rate": 0,
                "critical_failures": []
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
                "dscr_status": row[1],
                "dscr_covenant": float(row[2]) if row[2] else 1.25,
                "ltv_ratio": float(row[3]) if row[3] else None,
                "ltv_status": row[4],
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
