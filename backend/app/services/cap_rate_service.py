"""
Cap Rate (Capitalization Rate) Analysis Service

Calculates and analyzes capitalization rates for property valuation and investment decisions.

Cap Rate = Net Operating Income (NOI) / Property Value

Used for:
- Property valuation
- Investment comparison
- Market analysis
- Exit strategy planning
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData

logger = logging.getLogger(__name__)


class CapRateService:
    """
    Capitalization Rate Analysis Service
    """

    # Market cap rate benchmarks by property type (mock data - replace with real market data)
    MARKET_CAP_RATES = {
        "Retail": {
            "strong_market": Decimal("0.065"),      # 6.5%
            "average_market": Decimal("0.075"),     # 7.5%
            "weak_market": Decimal("0.085"),        # 8.5%
        },
        "Office": {
            "strong_market": Decimal("0.060"),      # 6.0%
            "average_market": Decimal("0.070"),     # 7.0%
            "weak_market": Decimal("0.080"),        # 8.0%
        },
        "Mixed-Use": {
            "strong_market": Decimal("0.070"),      # 7.0%
            "average_market": Decimal("0.080"),     # 8.0%
            "weak_market": Decimal("0.090"),        # 9.0%
        },
        "Industrial": {
            "strong_market": Decimal("0.055"),      # 5.5%
            "average_market": Decimal("0.065"),     # 6.5%
            "weak_market": Decimal("0.075"),        # 7.5%
        },
        "Multifamily": {
            "strong_market": Decimal("0.050"),      # 5.0%
            "average_market": Decimal("0.060"),     # 6.0%
            "weak_market": Decimal("0.070"),        # 7.0%
        },
    }

    def __init__(self, db: Session):
        self.db = db

    def calculate_cap_rate(
        self,
        property_id: int,
        financial_period_id: Optional[int] = None,
        property_value: Optional[Decimal] = None
    ) -> Dict:
        """
        Calculate capitalization rate for a property

        Cap Rate = Net Operating Income (NOI) / Property Value

        Parameters:
        - property_id: Property ID
        - financial_period_id: Financial period (optional, uses latest if not specified)
        - property_value: Override property value (optional)

        Returns cap rate, NOI, property value, and market comparison
        """
        try:
            # Get property
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get financial period
            if financial_period_id:
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.id == financial_period_id
                ).first()
            else:
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.property_id == property_id
                ).order_by(FinancialPeriod.period_end_date.desc()).first()

            if not period:
                return {"success": False, "error": "No financial period found"}

            # Calculate NOI
            noi = self._calculate_noi(property_id, period.id)

            if noi <= 0:
                return {
                    "success": False,
                    "error": "NOI is zero or negative - cannot calculate cap rate"
                }

            # Get property value
            if property_value is None:
                property_value = self._get_property_value(property_id, period.id)

            if property_value <= 0:
                return {
                    "success": False,
                    "error": "Property value is zero or negative - cannot calculate cap rate"
                }

            # Calculate cap rate
            cap_rate = noi / property_value

            # Get market comparison
            market_comparison = self._get_market_comparison(
                property.property_type,
                cap_rate
            )

            # Determine status
            if cap_rate < market_comparison["strong_market"]:
                status = "premium"  # Lower cap rate = higher valuation = premium property
            elif cap_rate < market_comparison["average_market"]:
                status = "market_rate"
            elif cap_rate < market_comparison["weak_market"]:
                status = "below_market"
            else:
                status = "distressed"

            result = {
                "success": True,
                "cap_rate": float(cap_rate),
                "cap_rate_percentage": float(cap_rate * 100),
                "noi": float(noi),
                "property_value": float(property_value),
                "annualized_noi": float(noi * 12) if period.period_type == "monthly" else float(noi * 4) if period.period_type == "quarterly" else float(noi),
                "status": status,
                "property": {
                    "id": property.id,
                    "name": property.property_name,
                    "code": property.property_code,
                    "type": property.property_type,
                },
                "period": {
                    "id": period.id,
                    "start_date": period.period_start_date.isoformat(),
                    "end_date": period.period_end_date.isoformat(),
                    "period_type": period.period_type,
                },
                "market_comparison": market_comparison,
                "calculated_at": datetime.utcnow().isoformat(),
            }

            return result

        except Exception as e:
            logger.error(f"Cap rate calculation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_noi(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Calculate Net Operating Income (NOI)

        NOI = Total Revenue - Operating Expenses
        """
        income_data = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.financial_period_id == financial_period_id
        ).all()

        total_revenue = Decimal("0")
        operating_expenses = Decimal("0")

        for item in income_data:
            if item.account_code:
                # Revenue accounts (4xxxx)
                if item.account_code.startswith("4"):
                    total_revenue += Decimal(str(item.amount or 0))
                # Operating expense accounts (5xxxx, 6xxxx)
                elif item.account_code.startswith("5") or item.account_code.startswith("6"):
                    operating_expenses += Decimal(str(item.amount or 0))

        noi = total_revenue - operating_expenses
        return noi

    def _get_property_value(self, property_id: int, financial_period_id: int) -> Decimal:
        """
        Get property value from balance sheet or property record
        """
        # Try to get from balance sheet (total assets)
        balance_sheet_data = self.db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.financial_period_id == financial_period_id
        ).all()

        total_assets = Decimal("0")
        for item in balance_sheet_data:
            if item.account_code and item.account_code.startswith("1"):
                total_assets += Decimal(str(item.amount or 0))

        if total_assets > 0:
            return total_assets

        # Fallback: use mock value based on property size
        property = self.db.query(Property).filter(Property.id == property_id).first()
        if property and property.total_area_sqft:
            property_value = Decimal(str(property.total_area_sqft)) * Decimal("200")
            return property_value

        return Decimal("5000000")  # $5M default

    def _get_market_comparison(
        self,
        property_type: Optional[str],
        cap_rate: Decimal
    ) -> Dict:
        """
        Compare property cap rate to market benchmarks
        """
        # Get market rates for property type
        market_rates = self.MARKET_CAP_RATES.get(
            property_type,
            self.MARKET_CAP_RATES["Retail"]  # Default to retail
        )

        return {
            "property_type": property_type or "Unknown",
            "strong_market": float(market_rates["strong_market"]),
            "average_market": float(market_rates["average_market"]),
            "weak_market": float(market_rates["weak_market"]),
            "strong_market_percentage": float(market_rates["strong_market"] * 100),
            "average_market_percentage": float(market_rates["average_market"] * 100),
            "weak_market_percentage": float(market_rates["weak_market"] * 100),
            "variance_from_average": float((cap_rate - market_rates["average_market"]) * 100),
        }

    def get_cap_rate_history(
        self,
        property_id: int,
        limit: int = 12
    ) -> List[Dict]:
        """
        Get cap rate history for a property (last N periods)
        """
        periods = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(limit).all()

        history = []
        for period in reversed(periods):
            result = self.calculate_cap_rate(property_id, period.id)
            if result.get("success"):
                history.append({
                    "period": period.period_end_date.isoformat(),
                    "cap_rate": result["cap_rate"],
                    "cap_rate_percentage": result["cap_rate_percentage"],
                    "noi": result["noi"],
                    "property_value": result["property_value"],
                    "status": result["status"],
                })

        return history

    def get_cap_rate_trend(
        self,
        property_id: int,
        lookback_periods: int = 4
    ) -> Dict:
        """
        Analyze cap rate trend over time

        Returns trend direction and percentage change
        """
        history = self.get_cap_rate_history(property_id, lookback_periods)

        if len(history) < 2:
            return {
                "success": False,
                "error": "Insufficient historical data for trend analysis"
            }

        # Calculate trend
        oldest_cap_rate = Decimal(str(history[0]["cap_rate"]))
        latest_cap_rate = Decimal(str(history[-1]["cap_rate"]))

        change = latest_cap_rate - oldest_cap_rate
        change_percentage = (change / oldest_cap_rate) * 100

        if change > Decimal("0.005"):  # > 0.5% increase
            trend = "increasing"
            interpretation = "Cap rate increasing - property value declining or NOI improving slower than value growth"
        elif change < Decimal("-0.005"):  # > 0.5% decrease
            trend = "decreasing"
            interpretation = "Cap rate decreasing - property value increasing or NOI improving"
        else:
            trend = "stable"
            interpretation = "Cap rate stable - consistent property performance"

        return {
            "success": True,
            "property_id": property_id,
            "periods_analyzed": len(history),
            "oldest_cap_rate": float(oldest_cap_rate),
            "latest_cap_rate": float(latest_cap_rate),
            "change": float(change),
            "change_percentage": float(change_percentage),
            "trend": trend,
            "interpretation": interpretation,
            "history": history,
        }

    def estimate_property_value(
        self,
        property_id: int,
        target_cap_rate: Optional[Decimal] = None
    ) -> Dict:
        """
        Estimate property value based on NOI and target cap rate

        Property Value = NOI / Cap Rate
        """
        try:
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get latest period
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id
            ).order_by(FinancialPeriod.period_end_date.desc()).first()

            if not period:
                return {"success": False, "error": "No financial period found"}

            # Calculate NOI
            noi = self._calculate_noi(property_id, period.id)

            # Annualize NOI if needed
            if period.period_type == "monthly":
                annual_noi = noi * 12
            elif period.period_type == "quarterly":
                annual_noi = noi * 4
            else:
                annual_noi = noi

            # Use target cap rate or market average
            if target_cap_rate is None:
                market_rates = self.MARKET_CAP_RATES.get(
                    property.property_type,
                    self.MARKET_CAP_RATES["Retail"]
                )
                target_cap_rate = market_rates["average_market"]

            # Estimate value
            estimated_value = annual_noi / target_cap_rate

            # Calculate at different cap rates for sensitivity analysis
            scenarios = {}
            for scenario_name, rate_adjustment in [
                ("conservative", Decimal("0.01")),    # +1% cap rate (lower value)
                ("market", Decimal("0")),             # Market rate
                ("aggressive", Decimal("-0.01")),     # -1% cap rate (higher value)
            ]:
                scenario_cap_rate = target_cap_rate + rate_adjustment
                scenario_value = annual_noi / scenario_cap_rate

                scenarios[scenario_name] = {
                    "cap_rate": float(scenario_cap_rate),
                    "cap_rate_percentage": float(scenario_cap_rate * 100),
                    "estimated_value": float(scenario_value),
                }

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "annual_noi": float(annual_noi),
                "target_cap_rate": float(target_cap_rate),
                "target_cap_rate_percentage": float(target_cap_rate * 100),
                "estimated_value": float(estimated_value),
                "valuation_scenarios": scenarios,
                "calculated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Property valuation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def compare_properties(
        self,
        property_ids: List[int]
    ) -> Dict:
        """
        Compare cap rates across multiple properties
        """
        results = []

        for property_id in property_ids:
            cap_rate_result = self.calculate_cap_rate(property_id)

            if cap_rate_result.get("success"):
                results.append({
                    "property_id": property_id,
                    "property_name": cap_rate_result["property"]["name"],
                    "property_type": cap_rate_result["property"]["type"],
                    "cap_rate": cap_rate_result["cap_rate"],
                    "cap_rate_percentage": cap_rate_result["cap_rate_percentage"],
                    "noi": cap_rate_result["noi"],
                    "property_value": cap_rate_result["property_value"],
                    "status": cap_rate_result["status"],
                })

        # Sort by cap rate (descending)
        results.sort(key=lambda x: x["cap_rate"], reverse=True)

        # Calculate portfolio average
        if results:
            avg_cap_rate = sum(r["cap_rate"] for r in results) / len(results)
            total_noi = sum(r["noi"] for r in results)
            total_value = sum(r["property_value"] for r in results)
        else:
            avg_cap_rate = 0
            total_noi = 0
            total_value = 0

        return {
            "success": True,
            "properties_compared": len(results),
            "portfolio_summary": {
                "average_cap_rate": float(avg_cap_rate),
                "average_cap_rate_percentage": float(avg_cap_rate * 100),
                "total_noi": float(total_noi),
                "total_value": float(total_value),
            },
            "properties": results,
        }

    def get_cap_rate_sensitivity_analysis(
        self,
        property_id: int,
        noi_change_scenarios: Optional[List[float]] = None
    ) -> Dict:
        """
        Analyze how property value changes with different NOI scenarios

        Useful for investment decision making
        """
        if noi_change_scenarios is None:
            noi_change_scenarios = [-20, -10, 0, 10, 20]  # % changes

        cap_rate_result = self.calculate_cap_rate(property_id)

        if not cap_rate_result.get("success"):
            return cap_rate_result

        current_noi = Decimal(str(cap_rate_result["noi"]))
        current_cap_rate = Decimal(str(cap_rate_result["cap_rate"]))
        current_value = Decimal(str(cap_rate_result["property_value"]))

        scenarios = []

        for noi_change_pct in noi_change_scenarios:
            new_noi = current_noi * (1 + Decimal(str(noi_change_pct)) / 100)
            new_value = new_noi / current_cap_rate
            value_change = new_value - current_value
            value_change_pct = (value_change / current_value) * 100

            scenarios.append({
                "noi_change_percentage": noi_change_pct,
                "new_noi": float(new_noi),
                "new_value": float(new_value),
                "value_change": float(value_change),
                "value_change_percentage": float(value_change_pct),
            })

        return {
            "success": True,
            "property_id": property_id,
            "current_noi": float(current_noi),
            "current_cap_rate": float(current_cap_rate),
            "current_cap_rate_percentage": float(current_cap_rate * 100),
            "current_value": float(current_value),
            "sensitivity_scenarios": scenarios,
        }
