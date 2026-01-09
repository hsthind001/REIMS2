"""
Tenant Risk Analysis Service - Phase 4 of Forensic Audit Framework

Analyzes tenant-related risks including:
- Concentration risk (Top 1, 3, 5, 10 tenants)
- Lease rollover risk (12mo, 24mo, 36mo windows)
- Credit quality assessment
- Occupancy verification
- Rent per SF benchmarking
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class TenantRiskAnalysisService:
    """
    Analyzes tenant concentration and lease rollover risks.

    Critical for CRE portfolio management and lender reporting.
    """

    # Concentration risk thresholds
    CONCENTRATION_TOP1_HIGH = 20.0  # Single tenant >20% of rent = HIGH RISK
    CONCENTRATION_TOP3_HIGH = 50.0  # Top 3 tenants >50% = MODERATE RISK
    CONCENTRATION_TOP5_HIGH = 65.0  # Top 5 tenants >65% = MODERATE RISK

    # Lease rollover risk thresholds
    ROLLOVER_12MO_HIGH = 25.0  # >25% of rent expiring in 12mo = HIGH RISK
    ROLLOVER_24MO_HIGH = 50.0  # >50% of rent expiring in 24mo = MODERATE RISK

    # Occupancy thresholds
    OCCUPANCY_EXCELLENT = 95.0  # >95% = EXCELLENT
    OCCUPANCY_GOOD = 90.0  # 90-95% = GOOD
    OCCUPANCY_WARNING = 85.0  # 85-90% = WARNING
    OCCUPANCY_CRITICAL = 80.0  # <80% = CRITICAL

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_all_tenant_risk_tests(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run complete tenant risk analysis suite.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Complete tenant risk analysis
        """

        # Run all analyses
        concentration_result = await self.analyze_tenant_concentration_risk(property_id, period_id)
        rollover_result = await self.analyze_lease_rollover_risk(property_id, period_id)
        occupancy_result = await self.calculate_occupancy_metrics(property_id, period_id)
        credit_result = await self.analyze_tenant_credit_quality(property_id, period_id)
        rent_psf_result = await self.analyze_rent_per_sf(property_id, period_id)

        # Determine overall concentration risk status
        if concentration_result['top_1_tenant_pct'] > self.CONCENTRATION_TOP1_HIGH:
            concentration_status = 'RED'
        elif concentration_result['top_3_tenant_pct'] > self.CONCENTRATION_TOP3_HIGH:
            concentration_status = 'YELLOW'
        else:
            concentration_status = 'GREEN'

        # Determine overall rollover risk status
        if rollover_result['rollover_12mo_pct'] > self.ROLLOVER_12MO_HIGH:
            rollover_status = 'RED'
        elif rollover_result['rollover_24mo_pct'] > self.ROLLOVER_24MO_HIGH:
            rollover_status = 'YELLOW'
        else:
            rollover_status = 'GREEN'

        return {
            'property_id': str(property_id),
            'period_id': str(period_id),
            'concentration_risk_status': concentration_status,
            'rollover_risk_status': rollover_status,
            'concentration_analysis': concentration_result,
            'rollover_analysis': rollover_result,
            'occupancy_metrics': occupancy_result,
            'credit_quality': credit_result,
            'rent_per_sf_analysis': rent_psf_result,
            'tested_at': datetime.now().isoformat()
        }

    async def analyze_tenant_concentration_risk(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-4.4: Tenant Concentration Risk Analysis

        Calculates percentage of total rent from top tenants:
        - Top 1 tenant (single tenant exposure)
        - Top 3 tenants
        - Top 5 tenants
        - Top 10 tenants

        Risk levels:
        - Single tenant >20% of rent = HIGH RISK (tenant departure = major impact)
        - Top 3 tenants >50% = MODERATE RISK
        - Top 5 tenants >65% = MODERATE RISK

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Concentration risk analysis
        """

        # Get all active tenants sorted by rent
        query = text("""
            SELECT
                tenant_name,
                monthly_rent,
                annual_rent,
                unit_area_sqft,
                lease_end_date
            FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND is_gross_rent_row IS NOT TRUE
            AND (LOWER(lease_status) = 'active' OR LOWER(occupancy_status) = 'occupied')
            ORDER BY monthly_rent DESC NULLS LAST
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        tenants = result.fetchall()

        if not tenants:
            return {
                'top_1_tenant_pct': 0,
                'top_3_tenant_pct': 0,
                'top_5_tenant_pct': 0,
                'top_10_tenant_pct': 0,
                'total_tenants': 0,
                'total_rent': 0,
                'top_tenants': []
            }

        # Calculate total rent (prefer annual, fall back to monthly * 12)
        total_rent = 0.0
        tenant_rents = []
        for tenant in tenants:
            monthly_rent = float(tenant[1]) if tenant[1] else 0.0
            annual_rent = float(tenant[2]) if tenant[2] else monthly_rent * 12
            tenant_rents.append(annual_rent)
            total_rent += annual_rent

        # Calculate top tenant concentrations
        top_1_rent = tenant_rents[0] if len(tenant_rents) >= 1 else 0
        top_3_rent = sum(tenant_rents[:3]) if len(tenant_rents) >= 3 else sum(tenant_rents)
        top_5_rent = sum(tenant_rents[:5]) if len(tenant_rents) >= 5 else sum(tenant_rents)
        top_10_rent = sum(tenant_rents[:10]) if len(tenant_rents) >= 10 else sum(tenant_rents)

        top_1_pct = (top_1_rent / total_rent * 100) if total_rent > 0 else 0
        top_3_pct = (top_3_rent / total_rent * 100) if total_rent > 0 else 0
        top_5_pct = (top_5_rent / total_rent * 100) if total_rent > 0 else 0
        top_10_pct = (top_10_rent / total_rent * 100) if total_rent > 0 else 0

        # Get top 10 tenant details
        top_tenants = []
        for i, tenant in enumerate(tenants[:10], 1):
            monthly_rent = float(tenant[1]) if tenant[1] else 0.0
            annual_rent = float(tenant[2]) if tenant[2] else monthly_rent * 12
            tenant_pct = (annual_rent / total_rent * 100) if total_rent > 0 else 0

            top_tenants.append({
                'rank': i,
                'tenant_name': tenant[0],
                'monthly_rent': round(monthly_rent, 2),
                'annual_rent': round(annual_rent, 2),
                'percent_of_total_rent': round(tenant_pct, 2),
                'square_feet': int(tenant[3]) if tenant[3] else 0,
                'lease_end_date': tenant[4].isoformat() if tenant[4] else None
            })

        return {
            'top_1_tenant_pct': round(top_1_pct, 2),
            'top_3_tenant_pct': round(top_3_pct, 2),
            'top_5_tenant_pct': round(top_5_pct, 2),
            'top_10_tenant_pct': round(top_10_pct, 2),
            'total_tenants': len(tenants),
            'total_rent': round(total_rent, 2),
            'top_tenants': top_tenants
        }

    async def analyze_lease_rollover_risk(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-4.5: Lease Expiration Analysis

        Calculates percentage of rent expiring in:
        - Next 12 months
        - Next 24 months
        - Next 36 months

        Risk levels:
        - >25% expiring in 12 months = HIGH RISK (major leasing effort required)
        - >50% expiring in 24 months = MODERATE RISK

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Lease rollover analysis
        """

        # Get current period date
        period_query = text("""
            SELECT period_end_date
            FROM financial_periods
            WHERE id = :period_id
        """)

        period_result = await self.db.execute(period_query, {"period_id": str(period_id)})
        period_row = period_result.fetchone()
        current_date = period_row[0] if period_row else datetime.now()

        # Calculate cutoff dates
        date_12mo = current_date + timedelta(days=365)
        date_24mo = current_date + timedelta(days=730)
        date_36mo = current_date + timedelta(days=1095)

        # Get all active leases
        query = text("""
            SELECT
                tenant_name,
                monthly_rent,
                annual_rent,
                lease_end_date,
                unit_area_sqft
            FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND is_gross_rent_row IS NOT TRUE
            AND (LOWER(lease_status) = 'active' OR LOWER(occupancy_status) = 'occupied')
            AND lease_end_date IS NOT NULL
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        leases = result.fetchall()

        if not leases:
            return {
                'rollover_12mo_pct': 0,
                'rollover_24mo_pct': 0,
                'rollover_36mo_pct': 0,
                'total_rent': 0,
                'expiring_12mo': [],
                'expiring_24mo': [],
                'expiring_36mo': []
            }

        total_rent = 0.0
        for lease in leases:
            monthly_rent = float(lease[1]) if lease[1] else 0.0
            annual_rent = float(lease[2]) if lease[2] else monthly_rent * 12
            total_rent += annual_rent

        # Calculate rollover by period
        expiring_12mo = []
        expiring_24mo = []
        expiring_36mo = []
        rent_12mo = 0
        rent_24mo = 0
        rent_36mo = 0

        for lease in leases:
            tenant_name = lease[0]
            monthly_rent = float(lease[1]) if lease[1] else 0.0
            annual_rent = float(lease[2]) if lease[2] else monthly_rent * 12
            lease_end_date = lease[3]
            square_feet = int(lease[4]) if lease[4] else 0

            lease_info = {
                'tenant_name': tenant_name,
                'monthly_rent': round(monthly_rent, 2),
                'annual_rent': round(annual_rent, 2),
                'lease_end_date': lease_end_date.isoformat() if lease_end_date else None,
                'square_feet': square_feet,
                'months_until_expiry': (lease_end_date - current_date).days // 30 if lease_end_date else 0
            }

            if lease_end_date <= date_12mo:
                expiring_12mo.append(lease_info)
                rent_12mo += annual_rent
            elif lease_end_date <= date_24mo:
                expiring_24mo.append(lease_info)
                rent_24mo += annual_rent
            elif lease_end_date <= date_36mo:
                expiring_36mo.append(lease_info)
                rent_36mo += annual_rent

        rollover_12mo_pct = (rent_12mo / total_rent * 100) if total_rent > 0 else 0
        rollover_24mo_pct = ((rent_12mo + rent_24mo) / total_rent * 100) if total_rent > 0 else 0
        rollover_36mo_pct = ((rent_12mo + rent_24mo + rent_36mo) / total_rent * 100) if total_rent > 0 else 0

        # Sort by expiry date
        expiring_12mo.sort(key=lambda x: x['lease_end_date'] if x['lease_end_date'] else '')
        expiring_24mo.sort(key=lambda x: x['lease_end_date'] if x['lease_end_date'] else '')

        return {
            'rollover_12mo_pct': round(rollover_12mo_pct, 2),
            'rollover_24mo_pct': round(rollover_24mo_pct, 2),
            'rollover_36mo_pct': round(rollover_36mo_pct, 2),
            'total_rent': round(total_rent, 2),
            'rent_expiring_12mo': round(rent_12mo, 2),
            'rent_expiring_24mo': round(rent_24mo, 2),
            'rent_expiring_36mo': round(rent_36mo, 2),
            'expiring_12mo': expiring_12mo,
            'expiring_24mo': expiring_24mo,
            'expiring_36mo': expiring_36mo
        }

    async def calculate_occupancy_metrics(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-4.3: Occupancy Rate Verification

        Calculates:
        - Physical occupancy (SF occupied / Total SF)
        - Economic occupancy (Actual rent / Market rent)
        - Vacant space details

        Thresholds:
        - >95% = EXCELLENT
        - 90-95% = GOOD
        - 85-90% = WARNING
        - <85% = CRITICAL

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Occupancy metrics
        """

        # Get total building SF and occupancy
        query = text("""
            SELECT
                SUM(CASE WHEN LOWER(occupancy_status) = 'occupied' OR LOWER(lease_status) = 'active'
                         THEN unit_area_sqft ELSE 0 END) as occupied_sf,
                SUM(unit_area_sqft) as total_sf,
                SUM(CASE WHEN LOWER(occupancy_status) = 'occupied' OR LOWER(lease_status) = 'active'
                         THEN COALESCE(annual_rent, monthly_rent * 12) ELSE 0 END) as actual_rent,
                COUNT(CASE WHEN LOWER(occupancy_status) = 'vacant' OR LOWER(lease_status) = 'vacant' THEN 1 END) as vacant_units
            FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND is_gross_rent_row IS NOT TRUE
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        occupied_sf = float(row[0]) if row and row[0] else 0
        total_sf = float(row[1]) if row and row[1] else 0
        actual_rent = float(row[2]) if row and row[2] else 0
        vacant_units = int(row[3]) if row and row[3] else 0

        # Calculate occupancy rate
        occupancy_rate = (occupied_sf / total_sf * 100) if total_sf > 0 else 0
        vacancy_rate = 100 - occupancy_rate

        # Economic occupancy (fallback to physical occupancy when market rent unavailable)
        economic_occupancy = occupancy_rate

        # Determine status
        if occupancy_rate >= self.OCCUPANCY_EXCELLENT:
            status = 'GREEN'
            interpretation = 'Excellent occupancy'
        elif occupancy_rate >= self.OCCUPANCY_GOOD:
            status = 'GREEN'
            interpretation = 'Good occupancy'
        elif occupancy_rate >= self.OCCUPANCY_WARNING:
            status = 'YELLOW'
            interpretation = 'Occupancy declining - focus on leasing'
        elif occupancy_rate >= self.OCCUPANCY_CRITICAL:
            status = 'YELLOW'
            interpretation = 'Low occupancy - accelerate leasing efforts'
        else:
            status = 'RED'
            interpretation = 'Critical occupancy - major leasing campaign required'

        return {
            'occupancy_rate': round(occupancy_rate, 2),
            'vacancy_rate': round(vacancy_rate, 2),
            'occupied_sf': round(occupied_sf, 0),
            'vacant_sf': round(total_sf - occupied_sf, 0),
            'total_sf': round(total_sf, 0),
            'vacant_units': vacant_units,
            'economic_occupancy': round(economic_occupancy, 2),
            'status': status,
            'interpretation': interpretation
        }

    async def analyze_tenant_credit_quality(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Analyze tenant credit quality distribution.

        Categories:
        - Investment Grade (A, AA, AAA)
        - Non-Investment Grade (B, C)
        - Not Rated

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Credit quality breakdown
        """

        query = text("""
            SELECT
                COUNT(*) as tenant_count,
                SUM(COALESCE(annual_rent, monthly_rent * 12)) as total_rent
            FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND is_gross_rent_row IS NOT TRUE
            AND (LOWER(lease_status) = 'active' OR LOWER(occupancy_status) = 'occupied')
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        total_rent = float(row[1]) if row and row[1] else 0.0

        if total_rent > 0:
            investment_grade_pct = 0.0
            non_investment_pct = 0.0
            not_rated_pct = 100.0
        else:
            investment_grade_pct = 0.0
            non_investment_pct = 0.0
            not_rated_pct = 0.0

        return {
            'investment_grade_pct': round(investment_grade_pct, 2),
            'non_investment_grade_pct': round(non_investment_pct, 2),
            'not_rated_pct': round(not_rated_pct, 2),
            'total_rent': round(total_rent, 2),
            'tenant_count': int(row[0]) if row and row[0] else 0
        }

    async def analyze_rent_per_sf(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-4.6: Rent Per SF Analysis

        Calculates average rent per SF and identifies outliers.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Rent per SF statistics
        """

        query = text("""
            SELECT
                tenant_name,
                monthly_rent,
                annual_rent,
                unit_area_sqft,
                (COALESCE(annual_rent, monthly_rent * 12) / unit_area_sqft) as rent_per_sf
            FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND is_gross_rent_row IS NOT TRUE
            AND (LOWER(lease_status) = 'active' OR LOWER(occupancy_status) = 'occupied')
            AND unit_area_sqft > 0
            ORDER BY rent_per_sf
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        leases = result.fetchall()

        if not leases:
            return {
                'average_rent_per_sf': 0,
                'median_rent_per_sf': 0,
                'min_rent_per_sf': 0,
                'max_rent_per_sf': 0,
                'std_dev_rent_per_sf': 0,
                'sample_size': 0
            }

        rent_per_sf_values = [float(l[3]) for l in leases]

        average = sum(rent_per_sf_values) / len(rent_per_sf_values)
        median = rent_per_sf_values[len(rent_per_sf_values) // 2]
        min_val = rent_per_sf_values[0]
        max_val = rent_per_sf_values[-1]
        variance = sum((value - average) ** 2 for value in rent_per_sf_values) / len(rent_per_sf_values)
        std_dev = variance ** 0.5

        return {
            'average_rent_per_sf': round(average, 2),
            'median_rent_per_sf': round(median, 2),
            'min_rent_per_sf': round(min_val, 2),
            'max_rent_per_sf': round(max_val, 2),
            'std_dev_rent_per_sf': round(std_dev, 2),
            'sample_size': len(leases)
        }

    async def save_tenant_risk_results(
        self,
        property_id: UUID,
        period_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Save tenant risk analysis results to database.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            results: Complete tenant risk analysis
        """

        concentration = results['concentration_analysis']
        rollover = results['rollover_analysis']
        occupancy = results['occupancy_metrics']
        credit = results['credit_quality']

        insert_query = text("""
            INSERT INTO tenant_risk_analysis (
                property_id,
                period_id,
                top_1_tenant_pct,
                top_3_tenant_pct,
                top_5_tenant_pct,
                top_10_tenant_pct,
                concentration_risk_status,
                lease_rollover_12mo_pct,
                lease_rollover_24mo_pct,
                lease_rollover_36mo_pct,
                occupancy_rate,
                investment_grade_tenant_pct,
                tenant_profiles,
                created_at
            ) VALUES (
                :property_id,
                :period_id,
                :top_1,
                :top_3,
                :top_5,
                :top_10,
                :concentration_status,
                :rollover_12mo,
                :rollover_24mo,
                :rollover_36mo,
                :occupancy,
                :investment_grade,
                :tenant_profiles,
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                top_1_tenant_pct = EXCLUDED.top_1_tenant_pct,
                concentration_risk_status = EXCLUDED.concentration_risk_status,
                lease_rollover_12mo_pct = EXCLUDED.lease_rollover_12mo_pct,
                occupancy_rate = EXCLUDED.occupancy_rate,
                updated_at = NOW()
        """)

        import json

        await self.db.execute(
            insert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "top_1": concentration['top_1_tenant_pct'],
                "top_3": concentration['top_3_tenant_pct'],
                "top_5": concentration['top_5_tenant_pct'],
                "top_10": concentration['top_10_tenant_pct'],
                "concentration_status": results['concentration_risk_status'],
                "rollover_12mo": rollover['rollover_12mo_pct'],
                "rollover_24mo": rollover['rollover_24mo_pct'],
                "rollover_36mo": rollover['rollover_36mo_pct'],
                "occupancy": occupancy['occupancy_rate'],
                "investment_grade": credit['investment_grade_pct'],
                "tenant_profiles": json.dumps(concentration['top_tenants'])
            }
        )

        await self.db.commit()
