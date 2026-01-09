"""
Collections & Revenue Quality Service

Implements Phase 5 of the Forensic Audit Framework:
- Days Sales Outstanding (DSO) calculation
- Cash conversion ratio analysis
- Revenue quality score (0-100 composite)
- A/R aging bucket analysis
- Collections efficiency metrics

Part of the Big 5 Forensic Audit Framework for REIMS2.

Author: Claude AI Forensic Audit Framework
Date: December 28, 2025
"""

from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging


logger = logging.getLogger(__name__)


class CollectionsRevenueQualityService:
    """
    Service for analyzing collections quality and revenue integrity.

    Implements rules:
    - A-5.1: Days Sales Outstanding (DSO)
    - A-5.2: Cash Conversion Ratio
    - A-5.3: Revenue Quality Score (0-100)
    - A-5.4: A/R Aging Analysis
    """

    # DSO Thresholds (days)
    DSO_EXCELLENT = 30.0  # <30 days = excellent collections
    DSO_GOOD = 60.0  # 30-60 days = acceptable
    DSO_WARNING = 90.0  # 60-90 days = warning
    # >90 days = red flag

    # Cash Conversion Ratio Thresholds
    CASH_CONVERSION_EXCELLENT = 0.95  # >95% = excellent
    CASH_CONVERSION_GOOD = 0.85  # 85-95% = good
    CASH_CONVERSION_WARNING = 0.75  # 75-85% = warning
    # <75% = poor

    # Revenue Quality Score Weights (total = 100 points)
    WEIGHT_COLLECTIONS_EFFICIENCY = 40  # DSO performance
    WEIGHT_CASH_CONVERSION = 30  # Cash collections ratio
    WEIGHT_OCCUPANCY = 20  # Physical occupancy
    WEIGHT_AR_AGING = 10  # % current A/R

    def __init__(self, db: AsyncSession):
        """
        Initialize the service.

        Args:
            db: Async database session
        """
        self.db = db

    async def calculate_days_sales_outstanding(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-5.1: Calculate Days Sales Outstanding (DSO).

        Formula:
            DSO = (Accounts Receivable Balance / Monthly Rent Revenue) × 30 days

        Lower DSO = faster collections = better revenue quality.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing:
                - dso_days: Calculated DSO
                - ar_balance: Accounts receivable balance
                - monthly_rent: Monthly rent revenue
                - status: GREEN/YELLOW/RED
                - explanation: Interpretation
        """
        logger.info(f"Calculating DSO for property {property_id}, period {period_id}")

        # Get A/R balance from Balance Sheet (asset account)
        ar_balance_query = text("""
            SELECT SUM(amount) as total_ar
            FROM balance_sheet_data
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND account_code LIKE '1200%'  -- Accounts Receivable
        """)

        ar_result = await self.db.execute(
            ar_balance_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        ar_row = ar_result.fetchone()
        ar_balance = float(ar_row.total_ar) if ar_row and ar_row.total_ar else 0.0

        # Get monthly rent from Rent Roll
        rent_query = text("""
            SELECT SUM(monthly_rent) as total_monthly_rent
            FROM rent_roll_data
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_gross_rent_row IS NOT TRUE
                AND (LOWER(lease_status) = 'active' OR LOWER(occupancy_status) = 'occupied')
        """)

        rent_result = await self.db.execute(
            rent_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        rent_row = rent_result.fetchone()
        monthly_rent = float(rent_row.total_monthly_rent) if rent_row and rent_row.total_monthly_rent else 0.0

        # Calculate DSO
        if monthly_rent > 0:
            dso_days = (ar_balance / monthly_rent) * 30.0
        else:
            dso_days = 0.0
            logger.warning(f"Monthly rent is zero for property {property_id}, DSO cannot be calculated")

        # Determine status
        if dso_days < self.DSO_EXCELLENT:
            status = "GREEN"
            explanation = f"Excellent collections efficiency. DSO of {dso_days:.1f} days is well below 30-day threshold."
        elif dso_days < self.DSO_GOOD:
            status = "GREEN"
            explanation = f"Good collections efficiency. DSO of {dso_days:.1f} days is acceptable (30-60 day range)."
        elif dso_days < self.DSO_WARNING:
            status = "YELLOW"
            explanation = f"Collections efficiency needs improvement. DSO of {dso_days:.1f} days indicates payment delays."
        else:
            status = "RED"
            explanation = f"Poor collections efficiency. DSO of {dso_days:.1f} days indicates significant collection issues."

        return {
            "rule_code": "A-5.1",
            "rule_name": "Days Sales Outstanding (DSO)",
            "dso_days": round(dso_days, 1),
            "ar_balance": ar_balance,
            "monthly_rent": monthly_rent,
            "status": status,
            "explanation": explanation,
            "recommendation": self._get_dso_recommendation(dso_days)
        }

    async def calculate_cash_conversion_ratio(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-5.2: Calculate Cash Conversion Ratio.

        Formula:
            Cash Conversion = Cash Collections / Billed Revenue

        Measures what percentage of billed revenue is actually collected in cash.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing:
                - cash_conversion_ratio: Calculated ratio (0.0 to 1.0)
                - cash_collections: Total cash collected
                - billed_revenue: Total revenue billed
                - status: GREEN/YELLOW/RED
        """
        logger.info(f"Calculating cash conversion ratio for property {property_id}")

        # Get cash collections from Cash Flow Statement (income section)
        cash_query = text("""
            SELECT SUM(period_amount) as total_cash_collections
            FROM cash_flow_data
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND (line_section = 'INCOME' OR account_code LIKE '4%')
                AND is_total IS NOT TRUE
                AND is_subtotal IS NOT TRUE
        """)

        cash_result = await self.db.execute(
            cash_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        cash_row = cash_result.fetchone()
        cash_collections = float(cash_row.total_cash_collections) if cash_row and cash_row.total_cash_collections else 0.0

        # Get billed revenue from Income Statement
        revenue_query = text("""
            SELECT COALESCE(
                (SELECT period_amount
                 FROM income_statement_data
                 WHERE property_id = :property_id
                   AND period_id = :period_id
                   AND line_category = 'INCOME'
                   AND is_total = true
                 ORDER BY line_number DESC
                 LIMIT 1),
                (SELECT SUM(period_amount)
                 FROM income_statement_data
                 WHERE property_id = :property_id
                   AND period_id = :period_id
                   AND line_category = 'INCOME'
                   AND is_total IS NOT TRUE
                   AND is_subtotal IS NOT TRUE)
            ) as total_revenue
        """)

        revenue_result = await self.db.execute(
            revenue_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        revenue_row = revenue_result.fetchone()
        billed_revenue = float(revenue_row.total_revenue) if revenue_row and revenue_row.total_revenue else 0.0

        # Calculate ratio
        if billed_revenue > 0:
            cash_conversion_ratio = cash_collections / billed_revenue
        else:
            cash_conversion_ratio = 0.0
            logger.warning(f"Billed revenue is zero for property {property_id}")

        # Determine status
        if cash_conversion_ratio >= self.CASH_CONVERSION_EXCELLENT:
            status = "GREEN"
            explanation = f"Excellent cash conversion at {cash_conversion_ratio*100:.1f}%. Nearly all revenue is collected."
        elif cash_conversion_ratio >= self.CASH_CONVERSION_GOOD:
            status = "GREEN"
            explanation = f"Good cash conversion at {cash_conversion_ratio*100:.1f}%. Collections are healthy."
        elif cash_conversion_ratio >= self.CASH_CONVERSION_WARNING:
            status = "YELLOW"
            explanation = f"Cash conversion at {cash_conversion_ratio*100:.1f}% needs improvement. Collection gap exists."
        else:
            status = "RED"
            explanation = f"Poor cash conversion at {cash_conversion_ratio*100:.1f}%. Significant collection issues."

        return {
            "rule_code": "A-5.2",
            "rule_name": "Cash Conversion Ratio",
            "cash_conversion_ratio": round(cash_conversion_ratio, 3),
            "cash_conversion_percentage": round(cash_conversion_ratio * 100, 1),
            "cash_collections": cash_collections,
            "billed_revenue": billed_revenue,
            "status": status,
            "explanation": explanation,
            "recommendation": self._get_cash_conversion_recommendation(cash_conversion_ratio)
        }

    async def analyze_ar_aging(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-5.4: Analyze Accounts Receivable Aging.

        Breaks down A/R into aging buckets:
        - Current (0-30 days)
        - 31-60 days
        - 61-90 days
        - 91+ days (red flag)

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing aging bucket analysis
        """
        logger.info(f"Analyzing A/R aging for property {property_id}")

        # Get period end date
        period_query = text("""
            SELECT period_end_date
            FROM financial_periods
            WHERE id = :period_id
        """)

        period_result = await self.db.execute(period_query, {"period_id": str(period_id)})
        period_row = period_result.fetchone()

        if not period_row:
            logger.error(f"Period {period_id} not found")
            return {"error": "Period not found"}

        # A/R aging detail is not available without tenant ledger data.
        # Use total A/R balance as current and flag limited visibility.
        ar_balance_query = text("""
            SELECT SUM(amount) as total_ar
            FROM balance_sheet_data
            WHERE property_id = :property_id
              AND period_id = :period_id
              AND account_code LIKE '1200%'
        """)

        ar_result = await self.db.execute(
            ar_balance_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        ar_row = ar_result.fetchone()

        total_ar = float(ar_row.total_ar) if ar_row and ar_row.total_ar else 0.0
        current_0_30 = total_ar
        days_31_60 = 0.0
        days_61_90 = 0.0
        days_91_plus = 0.0

        # Calculate percentages
        current_pct = (current_0_30 / total_ar * 100) if total_ar > 0 else 0
        pct_31_60 = (days_31_60 / total_ar * 100) if total_ar > 0 else 0
        pct_61_90 = (days_61_90 / total_ar * 100) if total_ar > 0 else 0
        pct_91_plus = (days_91_plus / total_ar * 100) if total_ar > 0 else 0

        if total_ar == 0:
            status = "GREEN"
            explanation = "No outstanding accounts receivable."
        else:
            status = "YELLOW"
            explanation = "A/R aging detail unavailable; treating total balance as current."

        return {
            "rule_code": "A-5.4",
            "rule_name": "A/R Aging Analysis",
            "total_ar": total_ar,
            "current_0_30": current_0_30,
            "days_31_60": days_31_60,
            "days_61_90": days_61_90,
            "days_91_plus": days_91_plus,
            "current_pct": round(current_pct, 1),
            "pct_31_60": round(pct_31_60, 1),
            "pct_61_90": round(pct_61_90, 1),
            "pct_91_plus": round(pct_91_plus, 1),
            "status": status,
            "explanation": explanation,
            "recommendation": self._get_aging_recommendation(current_pct, pct_91_plus)
        }

    async def calculate_revenue_quality_score(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-5.3: Calculate Revenue Quality Score (0-100 composite).

        Weighted components:
        - Collections efficiency (DSO): 40 points
        - Cash conversion ratio: 30 points
        - Occupancy rate: 20 points
        - A/R aging (% current): 10 points

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing composite score and breakdown
        """
        logger.info(f"Calculating revenue quality score for property {property_id}")

        # Get DSO
        dso_result = await self.calculate_days_sales_outstanding(property_id, period_id)
        dso_days = dso_result["dso_days"]

        # Get cash conversion
        cash_conv_result = await self.calculate_cash_conversion_ratio(property_id, period_id)
        cash_conv_ratio = cash_conv_result["cash_conversion_ratio"]

        # Get A/R aging
        aging_result = await self.analyze_ar_aging(property_id, period_id)
        current_pct = aging_result["current_pct"]

        # Get occupancy rate from rent roll
        occupancy_query = text("""
            SELECT
                SUM(CASE WHEN LOWER(occupancy_status) = 'occupied' OR LOWER(lease_status) = 'active'
                         THEN unit_area_sqft ELSE 0 END) as occupied_sf,
                SUM(unit_area_sqft) as total_sf
            FROM rent_roll_data
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_gross_rent_row IS NOT TRUE
        """)

        occ_result = await self.db.execute(
            occupancy_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        occ_row = occ_result.fetchone()

        if occ_row and occ_row.total_sf and occ_row.total_sf > 0:
            occupancy_rate = (float(occ_row.occupied_sf) / float(occ_row.total_sf)) * 100
        else:
            occupancy_rate = 0.0

        # Calculate component scores

        # 1. Collections Efficiency Score (40 points max)
        # Perfect DSO (<30 days) = 40 points, linear decline to 0 at >120 days
        if dso_days <= self.DSO_EXCELLENT:
            collections_score = 40
        elif dso_days >= 120:
            collections_score = 0
        else:
            collections_score = int(40 * (1 - (dso_days - 30) / 90))

        # 2. Cash Conversion Score (30 points max)
        if cash_conv_ratio >= self.CASH_CONVERSION_EXCELLENT:
            cash_conv_score = 30
        elif cash_conv_ratio <= 0.5:
            cash_conv_score = 0
        else:
            cash_conv_score = int(30 * ((cash_conv_ratio - 0.5) / 0.45))

        # 3. Occupancy Score (20 points max)
        if occupancy_rate >= 95:
            occupancy_score = 20
        elif occupancy_rate <= 70:
            occupancy_score = 0
        else:
            occupancy_score = int(20 * ((occupancy_rate - 70) / 25))

        # 4. A/R Aging Score (10 points max)
        # >90% current = 10 points, linear decline to 0 at <50% current
        if current_pct >= 90:
            aging_score = 10
        elif current_pct <= 50:
            aging_score = 0
        else:
            aging_score = int(10 * ((current_pct - 50) / 40))

        # Calculate total score
        total_score = collections_score + cash_conv_score + occupancy_score + aging_score

        # Determine status
        if total_score >= 85:
            status = "GREEN"
            grade = "A"
            explanation = "Excellent revenue quality. Strong collections, high occupancy, healthy cash conversion."
        elif total_score >= 70:
            status = "GREEN"
            grade = "B"
            explanation = "Good revenue quality. Generally healthy metrics with room for improvement."
        elif total_score >= 55:
            status = "YELLOW"
            grade = "C"
            explanation = "Fair revenue quality. Some areas need attention to improve collections."
        else:
            status = "RED"
            grade = "D"
            explanation = "Poor revenue quality. Significant improvements needed in collections and occupancy."

        return {
            "rule_code": "A-5.3",
            "rule_name": "Revenue Quality Score",
            "total_score": total_score,
            "grade": grade,
            "status": status,
            "explanation": explanation,
            "component_scores": {
                "collections_efficiency": {
                    "score": collections_score,
                    "max_points": self.WEIGHT_COLLECTIONS_EFFICIENCY,
                    "dso_days": dso_days
                },
                "cash_conversion": {
                    "score": cash_conv_score,
                    "max_points": self.WEIGHT_CASH_CONVERSION,
                    "ratio": cash_conv_ratio
                },
                "occupancy": {
                    "score": occupancy_score,
                    "max_points": self.WEIGHT_OCCUPANCY,
                    "rate": occupancy_rate
                },
                "ar_aging": {
                    "score": aging_score,
                    "max_points": self.WEIGHT_AR_AGING,
                    "current_pct": current_pct
                }
            },
            "recommendation": self._get_quality_score_recommendation(total_score)
        }

    async def run_all_collections_tests(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run all collections and revenue quality tests.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing all test results
        """
        logger.info(f"Running all collections tests for property {property_id}, period {period_id}")

        # Run all tests
        dso_result = await self.calculate_days_sales_outstanding(property_id, period_id)
        cash_conv_result = await self.calculate_cash_conversion_ratio(property_id, period_id)
        aging_result = await self.analyze_ar_aging(property_id, period_id)
        quality_score_result = await self.calculate_revenue_quality_score(property_id, period_id)

        # Determine overall status
        statuses = [
            dso_result["status"],
            cash_conv_result["status"],
            aging_result["status"],
            quality_score_result["status"]
        ]

        if "RED" in statuses:
            overall_status = "RED"
        elif "YELLOW" in statuses:
            overall_status = "YELLOW"
        else:
            overall_status = "GREEN"

        return {
            "property_id": str(property_id),
            "period_id": str(period_id),
            "overall_status": overall_status,
            "revenue_quality_score": quality_score_result["total_score"],
            "tests": {
                "days_sales_outstanding": dso_result,
                "cash_conversion_ratio": cash_conv_result,
                "ar_aging_analysis": aging_result,
                "revenue_quality_score": quality_score_result
            },
            "summary": {
                "dso_days": dso_result["dso_days"],
                "cash_conversion_pct": cash_conv_result["cash_conversion_percentage"],
                "current_ar_pct": aging_result["current_pct"],
                "quality_score": quality_score_result["total_score"],
                "grade": quality_score_result["grade"]
            }
        }

    async def save_collections_results(
        self,
        property_id: UUID,
        period_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Save collections quality results to database.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID
            results: Results from run_all_collections_tests()
        """
        logger.info(f"Saving collections results for property {property_id}, period {period_id}")

        # Save to collections_revenue_quality table (UPSERT)
        upsert_query = text("""
            INSERT INTO collections_revenue_quality (
                property_id,
                period_id,
                days_sales_outstanding,
                dso_status,
                cash_conversion_ratio,
                revenue_quality_score,
                ar_aging_details,
                overall_status,
                created_at,
                updated_at
            ) VALUES (
                :property_id,
                :period_id,
                :dso_days,
                :dso_status,
                :cash_conversion_ratio,
                :revenue_quality_score,
                CAST(:ar_aging_details AS jsonb),
                :overall_status,
                NOW(),
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                days_sales_outstanding = EXCLUDED.days_sales_outstanding,
                dso_status = EXCLUDED.dso_status,
                cash_conversion_ratio = EXCLUDED.cash_conversion_ratio,
                revenue_quality_score = EXCLUDED.revenue_quality_score,
                ar_aging_details = EXCLUDED.ar_aging_details,
                overall_status = EXCLUDED.overall_status,
                updated_at = NOW()
        """)

        import json

        await self.db.execute(
            upsert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "dso_days": results["summary"]["dso_days"],
                "dso_status": results["tests"]["days_sales_outstanding"]["status"],
                "cash_conversion_ratio": results["summary"]["cash_conversion_pct"] / 100,
                "revenue_quality_score": results["summary"]["quality_score"],
                "ar_aging_details": json.dumps(results["tests"]["ar_aging_analysis"]),
                "overall_status": results["overall_status"]
            }
        )

        await self.db.commit()
        logger.info(f"Collections results saved successfully")

    # Helper methods for recommendations

    def _get_dso_recommendation(self, dso_days: float) -> str:
        """Get recommendation based on DSO."""
        if dso_days < self.DSO_EXCELLENT:
            return "Maintain current collections processes. DSO is excellent."
        elif dso_days < self.DSO_GOOD:
            return "Continue monitoring DSO. Consider implementing automated payment reminders."
        elif dso_days < self.DSO_WARNING:
            return "Review collections procedures. Consider offering online payment options or incentives for early payment."
        else:
            return "Urgent: Implement aggressive collections strategy. Review tenant creditworthiness and consider stricter payment terms."

    def _get_cash_conversion_recommendation(self, ratio: float) -> str:
        """Get recommendation based on cash conversion ratio."""
        if ratio >= self.CASH_CONVERSION_EXCELLENT:
            return "Excellent cash collections. Maintain current processes."
        elif ratio >= self.CASH_CONVERSION_GOOD:
            return "Good cash conversion. Monitor for trends and continue current practices."
        elif ratio >= self.CASH_CONVERSION_WARNING:
            return "Review revenue recognition vs. cash collection timing. Consider accrual adjustments."
        else:
            return "Urgent: Large gap between billed revenue and cash collections. Review tenant payment patterns and creditworthiness immediately."

    def _get_aging_recommendation(self, current_pct: float, old_pct: float) -> str:
        """Get recommendation based on A/R aging."""
        if current_pct >= 80.0 and old_pct < 5.0:
            return "A/R aging is healthy. Maintain current collections practices."
        elif current_pct >= 60.0:
            return "Monitor aging trends. Consider automated reminders for 30+ day balances."
        else:
            return "Urgent: High percentage of old A/R. Implement formal collections policy with escalation procedures. Consider bad debt reserves."

    def _get_quality_score_recommendation(self, score: int) -> str:
        """Get recommendation based on overall quality score."""
        if score >= 85:
            return "Excellent revenue quality. Continue current practices and use as benchmark."
        elif score >= 70:
            return "Good revenue quality. Focus on improving lowest-scoring component."
        elif score >= 55:
            return "Fair revenue quality. Develop action plan to improve collections efficiency and occupancy."
        else:
            return "Urgent: Poor revenue quality requires immediate attention. Consider comprehensive review of property management and collections processes."
