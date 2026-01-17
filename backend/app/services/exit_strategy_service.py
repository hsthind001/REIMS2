"""
Exit Strategy Intelligence Service

Analyzes exit strategies for commercial real estate investments:
- Hold strategy
- Refinance strategy
- Sale strategy

Includes:
- IRR (Internal Rate of Return) calculations
- NPV (Net Present Value) analysis
- Cap rate impact modeling
- Interest rate sensitivity
- Optimal exit timing recommendations
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import numpy as np

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.cap_rate_service import CapRateService
from app.services.ltv_monitoring_service import LTVMonitoringService

logger = logging.getLogger(__name__)


class ExitStrategyService:
    """
    Exit Strategy Intelligence Service

    Analyzes and compares different exit strategies for real estate investments
    """

    def __init__(self, db: Session):
        self.db = db
        self.cap_rate_service = CapRateService(db)
        self.ltv_service = LTVMonitoringService(db)

    def analyze_exit_strategies(
        self,
        property_id: int,
        investment_amount: Optional[Decimal] = None,
        investment_date: Optional[datetime] = None,
        holding_period_years: int = 5,
        discount_rate: Decimal = Decimal("0.10"),  # 10% discount rate
        exit_cap_rate: Optional[Decimal] = None,
    ) -> Dict:
        """
        Comprehensive exit strategy analysis

        Compares three scenarios:
        1. Hold: Continue operating the property
        2. Refinance: Refinance debt and extract equity
        3. Sale: Sell the property

        Returns IRR, NPV, and recommendations for each strategy
        """
        try:
            # Get property
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Get current cap rate and NOI
            cap_rate_result = self.cap_rate_service.calculate_cap_rate(property_id)
            if not cap_rate_result.get("success"):
                return {"success": False, "error": "Failed to calculate cap rate"}

            current_noi = Decimal(str(cap_rate_result["noi"]))
            current_cap_rate = Decimal(str(cap_rate_result["cap_rate"]))
            current_value = Decimal(str(cap_rate_result["property_value"]))

            # Determine investment parameters
            if investment_amount is None:
                # Use property acquisition value or current value * typical down payment
                investment_amount = current_value * Decimal("0.30")  # 30% equity

            if investment_date is None:
                # Use acquisition date or estimate
                investment_date = property.acquisition_date or (
                    datetime.utcnow() - timedelta(days=365 * 3)  # 3 years ago
                )

            # Determine exit cap rate (typically 0.5-1% higher than current)
            if exit_cap_rate is None:
                exit_cap_rate = current_cap_rate + Decimal("0.005")  # +0.5%

            # Analyze each strategy
            hold_result = self._analyze_hold_strategy(
                property_id=property_id,
                current_noi=current_noi,
                current_value=current_value,
                investment_amount=investment_amount,
                investment_date=investment_date,
                holding_period_years=holding_period_years,
                discount_rate=discount_rate,
            )

            refinance_result = self._analyze_refinance_strategy(
                property_id=property_id,
                current_noi=current_noi,
                current_value=current_value,
                investment_amount=investment_amount,
                investment_date=investment_date,
                discount_rate=discount_rate,
            )

            sale_result = self._analyze_sale_strategy(
                property_id=property_id,
                current_noi=current_noi,
                current_value=current_value,
                exit_cap_rate=exit_cap_rate,
                investment_amount=investment_amount,
                investment_date=investment_date,
                discount_rate=discount_rate,
            )

            # Determine recommended strategy
            strategies = [
                ("hold", hold_result["irr"] if hold_result.get("success") else -999),
                ("refinance", refinance_result["irr"] if refinance_result.get("success") else -999),
                ("sale", sale_result["irr"] if sale_result.get("success") else -999),
            ]

            recommended_strategy = max(strategies, key=lambda x: x[1])[0]

            # Generate recommendation confidence
            irr_values = [s[1] for s in strategies if s[1] > -999]
            if irr_values:
                max_irr = max(irr_values)
                second_max_irr = sorted(irr_values, reverse=True)[1] if len(irr_values) > 1 else 0
                confidence = min((max_irr - second_max_irr) / max_irr, 1.0) if max_irr > 0 else 0.5
            else:
                confidence = 0.0

            return {
                "success": True,
                "property_id": property_id,
                "property_name": property.property_name,
                "analysis_date": datetime.utcnow().isoformat(),
                "assumptions": {
                    "investment_amount": float(investment_amount),
                    "investment_date": investment_date.isoformat(),
                    "current_value": float(current_value),
                    "current_noi": float(current_noi),
                    "current_cap_rate": float(current_cap_rate),
                    "exit_cap_rate": float(exit_cap_rate),
                    "holding_period_years": holding_period_years,
                    "discount_rate": float(discount_rate),
                },
                "strategies": {
                    "hold": hold_result,
                    "refinance": refinance_result,
                    "sale": sale_result,
                },
                "recommendation": {
                    "strategy": recommended_strategy,
                    "confidence": float(confidence),
                    "confidence_percentage": float(confidence * 100),
                    "rationale": self._generate_recommendation_rationale(
                        recommended_strategy,
                        hold_result,
                        refinance_result,
                        sale_result,
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Exit strategy analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _analyze_hold_strategy(
        self,
        property_id: int,
        current_noi: Decimal,
        current_value: Decimal,
        investment_amount: Decimal,
        investment_date: datetime,
        holding_period_years: int,
        discount_rate: Decimal,
    ) -> Dict:
        """
        Analyze hold strategy (continue operating)

        Projects cash flows for holding period with NOI growth
        """
        try:
            # Project cash flows (NOI growth at 3% per year)
            noi_growth_rate = Decimal("0.03")
            cash_flows = []

            # Initial investment (negative)
            cash_flows.append(-float(investment_amount))

            # Annual NOI for holding period
            projected_noi = current_noi
            for year in range(holding_period_years):
                projected_noi = projected_noi * (1 + noi_growth_rate)
                cash_flows.append(float(projected_noi))

            # Terminal value at end of holding period (property value)
            exit_cap_rate = Decimal("0.075")  # Assume 7.5% exit cap rate
            terminal_noi = projected_noi
            terminal_value = terminal_noi / exit_cap_rate
            cash_flows[-1] += float(terminal_value)  # Add terminal value to last year

            # Calculate IRR and NPV
            irr = self._calculate_irr(cash_flows)
            npv = self._calculate_npv(cash_flows, discount_rate)

            # Calculate equity multiple
            total_cash_inflows = sum(cf for cf in cash_flows[1:] if cf > 0)
            equity_multiple = total_cash_inflows / float(investment_amount) if investment_amount > 0 else 0

            return {
                "success": True,
                "strategy": "hold",
                "irr": irr,
                "irr_percentage": irr * 100,
                "npv": npv,
                "equity_multiple": equity_multiple,
                "terminal_value": float(terminal_value),
                "total_cash_flow": sum(cash_flows[1:]),
                "cash_flows": cash_flows,
                "assumptions": {
                    "noi_growth_rate": float(noi_growth_rate),
                    "exit_cap_rate": float(exit_cap_rate),
                    "holding_period_years": holding_period_years,
                },
            }

        except Exception as e:
            logger.error(f"Hold strategy analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _analyze_refinance_strategy(
        self,
        property_id: int,
        current_noi: Decimal,
        current_value: Decimal,
        investment_amount: Decimal,
        investment_date: datetime,
        discount_rate: Decimal,
    ) -> Dict:
        """
        Analyze refinance strategy

        Extract equity while continuing to operate
        """
        try:
            # Get current LTV
            ltv_result = self.ltv_service.calculate_ltv(property_id)
            current_ltv = Decimal(str(ltv_result.get("ltv", 0.70)))

            # Refinance parameters
            target_ltv = Decimal("0.75")  # Refinance to 75% LTV
            new_loan_amount = current_value * target_ltv
            current_loan_balance = current_value * current_ltv
            equity_extracted = new_loan_amount - current_loan_balance

            # New loan terms
            interest_rate = Decimal("0.055")  # 5.5% interest rate
            loan_term_years = 10
            monthly_payment = self._calculate_mortgage_payment(
                new_loan_amount,
                interest_rate,
                loan_term_years
            )
            annual_debt_service = monthly_payment * 12

            # Cash flows after refinance
            # Year 0: Initial investment + equity extracted
            cash_flows = [-float(investment_amount), float(equity_extracted)]

            # Annual cash flows (NOI - debt service)
            noi_growth_rate = Decimal("0.03")
            projected_noi = current_noi
            for year in range(1, 6):  # 5-year projection
                projected_noi = projected_noi * (1 + noi_growth_rate)
                annual_cash_flow = projected_noi - annual_debt_service
                cash_flows.append(float(annual_cash_flow))

            # Terminal value (property sale)
            exit_cap_rate = Decimal("0.075")
            terminal_noi = projected_noi
            terminal_value = terminal_noi / exit_cap_rate
            remaining_loan_balance = self._calculate_remaining_balance(
                new_loan_amount,
                interest_rate,
                loan_term_years,
                5  # 5 years of payments
            )
            net_sale_proceeds = terminal_value - remaining_loan_balance
            cash_flows[-1] += float(net_sale_proceeds)

            # Calculate IRR and NPV
            irr = self._calculate_irr(cash_flows)
            npv = self._calculate_npv(cash_flows, discount_rate)

            return {
                "success": True,
                "strategy": "refinance",
                "irr": irr,
                "irr_percentage": irr * 100,
                "npv": npv,
                "equity_extracted": float(equity_extracted),
                "new_loan_amount": float(new_loan_amount),
                "annual_debt_service": float(annual_debt_service),
                "remaining_balance_at_exit": float(remaining_loan_balance),
                "terminal_value": float(terminal_value),
                "net_sale_proceeds": float(net_sale_proceeds),
                "cash_flows": cash_flows,
            }

        except Exception as e:
            logger.error(f"Refinance strategy analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _analyze_sale_strategy(
        self,
        property_id: int,
        current_noi: Decimal,
        current_value: Decimal,
        exit_cap_rate: Decimal,
        investment_amount: Decimal,
        investment_date: datetime,
        discount_rate: Decimal,
    ) -> Dict:
        """
        Analyze sale strategy (sell now)
        """
        try:
            # Calculate sale price based on exit cap rate
            sale_price = current_noi / exit_cap_rate

            # Get current loan balance
            ltv_result = self.ltv_service.calculate_ltv(property_id)
            current_ltv = Decimal(str(ltv_result.get("ltv", 0.70)))
            loan_balance = current_value * current_ltv

            # Calculate selling costs (typically 5-7%)
            selling_costs_rate = Decimal("0.06")  # 6%
            selling_costs = sale_price * selling_costs_rate

            # Net proceeds
            net_proceeds = sale_price - loan_balance - selling_costs

            # Calculate holding period return
            years_held = (datetime.utcnow() - investment_date).days / 365.25

            # Cash flows: initial investment, then sale proceeds
            cash_flows = [-float(investment_amount), float(net_proceeds)]

            # Calculate IRR and NPV
            irr = self._calculate_irr(cash_flows)
            npv = self._calculate_npv(cash_flows, discount_rate)

            # Calculate annualized return
            if years_held > 0:
                annualized_return = (float(net_proceeds) / float(investment_amount)) ** (1 / years_held) - 1
            else:
                annualized_return = 0

            return {
                "success": True,
                "strategy": "sale",
                "irr": irr,
                "irr_percentage": irr * 100,
                "npv": npv,
                "sale_price": float(sale_price),
                "loan_balance": float(loan_balance),
                "selling_costs": float(selling_costs),
                "selling_costs_percentage": float(selling_costs_rate * 100),
                "net_proceeds": float(net_proceeds),
                "years_held": years_held,
                "annualized_return": annualized_return,
                "annualized_return_percentage": annualized_return * 100,
                "cash_flows": cash_flows,
            }

        except Exception as e:
            logger.error(f"Sale strategy analysis failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_irr(self, cash_flows: List[float]) -> float:
        """
        Calculate Internal Rate of Return using numpy

        IRR is the discount rate that makes NPV = 0
        """
        try:
            irr = np.irr(cash_flows)
            return float(irr) if not np.isnan(irr) else 0.0
        except (ValueError, RuntimeWarning, FloatingPointError):
            # IRR calculation can fail with invalid cash flows
            return 0.0

    def _calculate_npv(self, cash_flows: List[float], discount_rate: Decimal) -> float:
        """
        Calculate Net Present Value

        NPV = Sum of (Cash Flow / (1 + r)^t)
        """
        try:
            npv = np.npv(float(discount_rate), cash_flows)
            return float(npv)
        except (ValueError, TypeError, ZeroDivisionError):
            # NPV calculation can fail with invalid inputs
            return 0.0

    def _calculate_mortgage_payment(
        self,
        loan_amount: Decimal,
        annual_interest_rate: Decimal,
        loan_term_years: int
    ) -> Decimal:
        """
        Calculate monthly mortgage payment

        Payment = P * (r * (1 + r)^n) / ((1 + r)^n - 1)
        """
        monthly_rate = annual_interest_rate / 12
        num_payments = loan_term_years * 12

        if monthly_rate == 0:
            return loan_amount / num_payments

        payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / (
            (1 + monthly_rate) ** num_payments - 1
        )

        return payment

    def _calculate_remaining_balance(
        self,
        original_loan: Decimal,
        annual_interest_rate: Decimal,
        loan_term_years: int,
        years_paid: int
    ) -> Decimal:
        """
        Calculate remaining loan balance after N years
        """
        monthly_rate = annual_interest_rate / 12
        total_payments = loan_term_years * 12
        payments_made = years_paid * 12

        monthly_payment = self._calculate_mortgage_payment(
            original_loan,
            annual_interest_rate,
            loan_term_years
        )

        # Remaining balance formula
        remaining_balance = original_loan * (
            (1 + monthly_rate) ** payments_made
        ) - monthly_payment * (
            ((1 + monthly_rate) ** payments_made - 1) / monthly_rate
        )

        return max(remaining_balance, Decimal("0"))

    def _generate_recommendation_rationale(
        self,
        recommended_strategy: str,
        hold_result: Dict,
        refinance_result: Dict,
        sale_result: Dict,
    ) -> str:
        """
        Generate explanation for the recommendation
        """
        if recommended_strategy == "hold":
            return (
                f"Hold strategy recommended with IRR of {hold_result.get('irr_percentage', 0):.2f}%. "
                f"The property shows strong cash flow potential with projected NOI growth. "
                f"Continuing to operate will maximize long-term value."
            )
        elif recommended_strategy == "refinance":
            equity_extracted = refinance_result.get("equity_extracted", 0)
            return (
                f"Refinance strategy recommended with IRR of {refinance_result.get('irr_percentage', 0):.2f}%. "
                f"You can extract ${equity_extracted:,.2f} in equity while maintaining ownership. "
                f"This provides liquidity while preserving upside potential."
            )
        else:  # sale
            sale_price = sale_result.get("sale_price", 0)
            net_proceeds = sale_result.get("net_proceeds", 0)
            return (
                f"Sale strategy recommended with IRR of {sale_result.get('irr_percentage', 0):.2f}%. "
                f"Current market conditions favor selling at ${sale_price:,.2f}. "
                f"Net proceeds of ${net_proceeds:,.2f} can be redeployed to higher-return opportunities."
            )

    def get_interest_rate_sensitivity(
        self,
        property_id: int,
        rate_scenarios: Optional[List[float]] = None
    ) -> Dict:
        """
        Analyze impact of interest rate changes on exit strategies
        """
        if rate_scenarios is None:
            rate_scenarios = [-2.0, -1.0, 0.0, 1.0, 2.0]  # % changes

        base_analysis = self.analyze_exit_strategies(property_id)

        if not base_analysis.get("success"):
            return base_analysis

        results = []

        for rate_change in rate_scenarios:
            # Adjust discount rate
            base_discount_rate = Decimal(str(base_analysis["assumptions"]["discount_rate"]))
            new_discount_rate = base_discount_rate + Decimal(str(rate_change)) / 100

            analysis = self.analyze_exit_strategies(
                property_id=property_id,
                discount_rate=new_discount_rate
            )

            if analysis.get("success"):
                results.append({
                    "rate_change": rate_change,
                    "discount_rate": float(new_discount_rate),
                    "hold_irr": analysis["strategies"]["hold"].get("irr_percentage", 0),
                    "refinance_irr": analysis["strategies"]["refinance"].get("irr_percentage", 0),
                    "sale_irr": analysis["strategies"]["sale"].get("irr_percentage", 0),
                    "recommended_strategy": analysis["recommendation"]["strategy"],
                })

        return {
            "success": True,
            "property_id": property_id,
            "base_case": base_analysis,
            "sensitivity_analysis": results,
        }
