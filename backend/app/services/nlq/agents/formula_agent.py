"""
Formula & Calculation Agent - Financial formula explanations and calculations

Handles queries about:
- How financial metrics are calculated (DSCR, NOI, LTV, Current Ratio, etc.)
- Formula explanations with examples
- Calculation verification
- What-if scenarios
- Metric interpretation

Examples:
- "How is DSCR calculated?"
- "What is the formula for Current Ratio?"
- "Calculate DSCR for November 2025"
- "Explain Net Operating Income calculation"
- "What does a Current Ratio of 2.5 mean?"
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.services.metrics_service import MetricsService
from app.services.nlq.temporal_processor import temporal_processor


class FormulaAgent:
    """
    Specialized agent for financial formula queries

    Features:
    - 50+ financial formulas from REIMS
    - Natural language explanations
    - Step-by-step calculations
    - Metric interpretation
    - Industry benchmarks
    """

    # Complete formula definitions from REIMS metrics_service.py
    FORMULAS = {
        # Liquidity Ratios
        "current_ratio": {
            "name": "Current Ratio",
            "formula": "Current Assets / Current Liabilities",
            "explanation": "Measures ability to pay short-term obligations with short-term assets",
            "benchmark": {
                "excellent": "> 2.0",
                "good": "1.5 - 2.0",
                "acceptable": "1.0 - 1.5",
                "poor": "< 1.0"
            },
            "interpretation": "Higher is better. Above 1.0 means assets exceed liabilities.",
            "category": "liquidity"
        },
        "quick_ratio": {
            "name": "Quick Ratio (Acid Test)",
            "formula": "(Current Assets - Receivables) / Current Liabilities",
            "explanation": "More conservative liquidity measure excluding less liquid receivables",
            "benchmark": {
                "excellent": "> 1.5",
                "good": "1.0 - 1.5",
                "acceptable": "0.75 - 1.0",
                "poor": "< 0.75"
            },
            "interpretation": "Measures ability to pay obligations with most liquid assets",
            "category": "liquidity"
        },
        "cash_ratio": {
            "name": "Cash Ratio",
            "formula": "Total Cash / Current Liabilities",
            "explanation": "Most conservative liquidity measure using only cash",
            "benchmark": {
                "excellent": "> 0.5",
                "good": "0.25 - 0.5",
                "acceptable": "0.1 - 0.25",
                "poor": "< 0.1"
            },
            "interpretation": "Shows ability to pay liabilities with cash on hand",
            "category": "liquidity"
        },
        "working_capital": {
            "name": "Working Capital",
            "formula": "Current Assets - Current Liabilities",
            "explanation": "Excess of current assets over current liabilities",
            "benchmark": {
                "excellent": "> $500,000",
                "good": "$250,000 - $500,000",
                "acceptable": "$0 - $250,000",
                "poor": "< $0"
            },
            "interpretation": "Positive working capital indicates financial health",
            "category": "liquidity"
        },

        # Leverage Ratios
        "debt_to_assets": {
            "name": "Debt-to-Assets Ratio",
            "formula": "Total Liabilities / Total Assets",
            "explanation": "Percentage of assets financed by debt",
            "benchmark": {
                "excellent": "< 0.3",
                "good": "0.3 - 0.5",
                "acceptable": "0.5 - 0.7",
                "poor": "> 0.7"
            },
            "interpretation": "Lower is better. Higher ratio means more financial risk",
            "category": "leverage"
        },
        "debt_to_equity": {
            "name": "Debt-to-Equity Ratio",
            "formula": "Total Liabilities / Total Equity",
            "explanation": "Relationship between borrowed funds and owner's equity",
            "benchmark": {
                "excellent": "< 1.0",
                "good": "1.0 - 2.0",
                "acceptable": "2.0 - 3.0",
                "poor": "> 3.0"
            },
            "interpretation": "Shows how much debt is used relative to equity",
            "category": "leverage"
        },
        "equity_ratio": {
            "name": "Equity Ratio",
            "formula": "Total Equity / Total Assets",
            "explanation": "Percentage of assets financed by equity",
            "benchmark": {
                "excellent": "> 0.5",
                "good": "0.3 - 0.5",
                "acceptable": "0.2 - 0.3",
                "poor": "< 0.2"
            },
            "interpretation": "Higher is better. Shows owner's stake in assets",
            "category": "leverage"
        },
        "ltv": {
            "name": "Loan-to-Value (LTV) Ratio",
            "formula": "Total Long-Term Debt / Net Property Value × 100",
            "explanation": "Percentage of property value financed by debt",
            "benchmark": {
                "excellent": "< 60%",
                "good": "60% - 75%",
                "acceptable": "75% - 85%",
                "poor": "> 85%"
            },
            "interpretation": "Lower is better. Higher LTV means more leverage risk",
            "category": "leverage"
        },

        # Mortgage Metrics
        "dscr": {
            "name": "Debt Service Coverage Ratio (DSCR)",
            "formula": "Net Operating Income (NOI) / Annual Debt Service",
            "explanation": "Property's ability to cover mortgage payments from operations",
            "benchmark": {
                "excellent": "> 1.5",
                "good": "1.25 - 1.5",
                "acceptable": "1.15 - 1.25",
                "poor": "< 1.15"
            },
            "interpretation": "Must be > 1.0. Higher means better debt coverage. Most lenders require 1.25+",
            "category": "mortgage",
            "critical": True
        },
        "interest_coverage": {
            "name": "Interest Coverage Ratio",
            "formula": "EBIT / Interest Expense",
            "explanation": "Ability to pay interest expenses from earnings",
            "benchmark": {
                "excellent": "> 3.0",
                "good": "2.0 - 3.0",
                "acceptable": "1.5 - 2.0",
                "poor": "< 1.5"
            },
            "interpretation": "Higher is better. Shows how many times interest is covered",
            "category": "mortgage"
        },
        "debt_yield": {
            "name": "Debt Yield",
            "formula": "NOI / Total Loan Amount × 100",
            "explanation": "Return lender would get if property were foreclosed",
            "benchmark": {
                "excellent": "> 12%",
                "good": "10% - 12%",
                "acceptable": "8% - 10%",
                "poor": "< 8%"
            },
            "interpretation": "Higher is better. Lenders typically require 10%+",
            "category": "mortgage"
        },
        "break_even_occupancy": {
            "name": "Break-Even Occupancy",
            "formula": "(Operating Expenses + Debt Service) / Gross Potential Rent × 100",
            "explanation": "Occupancy rate needed to cover expenses and debt",
            "benchmark": {
                "excellent": "< 70%",
                "good": "70% - 80%",
                "acceptable": "80% - 90%",
                "poor": "> 90%"
            },
            "interpretation": "Lower is better. Shows cushion for vacancy",
            "category": "mortgage"
        },

        # Income Statement Metrics
        "noi": {
            "name": "Net Operating Income (NOI)",
            "formula": "Total Income - Total Operating Expenses",
            "explanation": "Property income before debt service and capital expenses",
            "benchmark": {
                "excellent": "> $500,000",
                "good": "$250,000 - $500,000",
                "acceptable": "$100,000 - $250,000",
                "poor": "< $100,000"
            },
            "interpretation": "Key measure of property operating performance",
            "category": "income_statement",
            "critical": True
        },
        "operating_margin": {
            "name": "Operating Margin",
            "formula": "NOI / Total Revenue × 100",
            "explanation": "Percentage of revenue retained as operating income",
            "benchmark": {
                "excellent": "> 60%",
                "good": "50% - 60%",
                "acceptable": "40% - 50%",
                "poor": "< 40%"
            },
            "interpretation": "Higher is better. Shows operational efficiency",
            "category": "income_statement"
        },
        "profit_margin": {
            "name": "Profit Margin",
            "formula": "Net Income / Total Revenue × 100",
            "explanation": "Percentage of revenue retained as profit after all expenses",
            "benchmark": {
                "excellent": "> 30%",
                "good": "20% - 30%",
                "acceptable": "10% - 20%",
                "poor": "< 10%"
            },
            "interpretation": "Higher is better. Shows overall profitability",
            "category": "income_statement"
        },
        "expense_ratio": {
            "name": "Expense Ratio",
            "formula": "Operating Expenses / Total Revenue × 100",
            "explanation": "Percentage of revenue consumed by operating expenses",
            "benchmark": {
                "excellent": "< 40%",
                "good": "40% - 50%",
                "acceptable": "50% - 60%",
                "poor": "> 60%"
            },
            "interpretation": "Lower is better. Shows cost control efficiency",
            "category": "income_statement"
        },

        # Rent Roll Metrics
        "occupancy_rate": {
            "name": "Occupancy Rate",
            "formula": "Occupied Units / Total Units × 100",
            "explanation": "Percentage of units that are leased",
            "benchmark": {
                "excellent": "> 95%",
                "good": "90% - 95%",
                "acceptable": "85% - 90%",
                "poor": "< 85%"
            },
            "interpretation": "Higher is better. Key driver of revenue",
            "category": "rent_roll",
            "critical": True
        },
        "vacancy_rate": {
            "name": "Vacancy Rate",
            "formula": "Vacant Units / Total Units × 100",
            "explanation": "Percentage of units that are vacant",
            "benchmark": {
                "excellent": "< 5%",
                "good": "5% - 10%",
                "acceptable": "10% - 15%",
                "poor": "> 15%"
            },
            "interpretation": "Lower is better. Inverse of occupancy",
            "category": "rent_roll"
        },
        "rent_per_sqft": {
            "name": "Rent per Square Foot",
            "formula": "Annual Rent / Total Square Feet",
            "explanation": "Average annual rent per square foot",
            "benchmark": "Varies by market and property type",
            "interpretation": "Compare to market comps for pricing analysis",
            "category": "rent_roll"
        },

        # Property Value Metrics
        "net_property_value": {
            "name": "Net Property Value",
            "formula": "Gross Property Value - Accumulated Depreciation",
            "explanation": "Book value of property after depreciation",
            "category": "balance_sheet"
        },
        "depreciation_rate": {
            "name": "Depreciation Rate",
            "formula": "Accumulated Depreciation / Gross Property Value × 100",
            "explanation": "Percentage of property value that has been depreciated",
            "category": "balance_sheet"
        },

        # Cash Flow Metrics
        "operating_cash_flow": {
            "name": "Operating Cash Flow",
            "formula": "Net Income + Depreciation + Amortization + Working Capital Changes",
            "explanation": "Cash generated from core business operations",
            "category": "cash_flow"
        },
        "free_cash_flow": {
            "name": "Free Cash Flow",
            "formula": "Operating Cash Flow - Capital Expenditures",
            "explanation": "Cash available after maintaining/expanding asset base",
            "category": "cash_flow"
        }
    }

    def __init__(self, db: Session, llm=None):
        """Initialize formula agent"""
        self.db = db
        self.llm = llm
        self.metrics_service = MetricsService(db)

    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process formula/calculation query

        Args:
            query: Natural language query
            context: Optional context (property_id, etc.)

        Returns:
            Query result with formula, calculation, and explanation
        """
        try:
            query_lower = query.lower()

            # Detect query intent
            intent = self._detect_intent(query_lower)

            # Extract temporal info if calculation requested
            temporal_info = None
            if intent["type"] in ["calculate", "verify"]:
                temporal_info = temporal_processor.extract_temporal_info(query)

            # Process based on intent
            if intent["type"] == "explain":
                result = await self._explain_formula(intent["metric"])
            elif intent["type"] == "calculate":
                result = await self._calculate_metric(
                    intent["metric"],
                    temporal_info,
                    context
                )
            elif intent["type"] == "interpret":
                result = await self._interpret_metric(intent["metric"], context)
            elif intent["type"] == "compare":
                result = await self._compare_metrics(intent["metrics"], context)
            else:
                result = await self._explain_formula(intent.get("metric"))

            return {
                "success": True,
                **result,
                "metadata": {
                    "intent": intent,
                    "temporal_info": temporal_info
                },
                "agent": "formula"
            }

        except Exception as e:
            logger.error(f"Error in formula agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error: {str(e)}",
                "agent": "formula"
            }

    def _detect_intent(self, query: str) -> Dict[str, Any]:
        """Detect what the user wants"""
        intent = {"type": "explain", "metric": None, "metrics": []}

        # Find metric being asked about
        for metric_key, formula_info in self.FORMULAS.items():
            name_lower = formula_info["name"].lower()
            if name_lower in query or metric_key in query:
                intent["metric"] = metric_key
                break

        # Detect intent type
        if any(word in query for word in ["calculate", "compute", "what is", "what was"]):
            intent["type"] = "calculate"
        elif any(word in query for word in ["how is", "formula for", "how do you calculate", "how to calculate"]):
            intent["type"] = "explain"
        elif any(word in query for word in ["interpret", "mean", "what does", "significance"]):
            intent["type"] = "interpret"
        elif any(word in query for word in ["compare", "versus", "vs", "difference between"]):
            intent["type"] = "compare"

        return intent

    async def _explain_formula(self, metric_key: Optional[str]) -> Dict[str, Any]:
        """Explain a formula"""
        if not metric_key or metric_key not in self.FORMULAS:
            # List all formulas
            return await self._list_all_formulas()

        formula = self.FORMULAS[metric_key]

        answer = f"**{formula['name']}**\n\n"
        answer += f"**Formula:** `{formula['formula']}`\n\n"
        answer += f"**Explanation:** {formula['explanation']}\n\n"

        if "benchmark" in formula and isinstance(formula["benchmark"], dict):
            answer += "**Benchmarks:**\n"
            for level, value in formula["benchmark"].items():
                answer += f"  • {level.capitalize()}: {value}\n"
            answer += "\n"

        if "interpretation" in formula:
            answer += f"**Interpretation:** {formula['interpretation']}\n\n"

        if formula.get("critical"):
            answer += "⭐ **Critical Metric** - Key indicator for lenders and investors\n\n"

        # Add example calculation
        answer += "**Example:**\n"
        if metric_key == "dscr":
            answer += "```\nNOI: $500,000\nAnnual Debt Service: $350,000\nDSCR = $500,000 / $350,000 = 1.43\n\nInterpretation: Property generates 1.43x the cash needed for debt payments (Good)\n```"
        elif metric_key == "current_ratio":
            answer += "```\nCurrent Assets: $800,000\nCurrent Liabilities: $400,000\nCurrent Ratio = $800,000 / $400,000 = 2.0\n\nInterpretation: Can cover short-term obligations 2x over (Excellent)\n```"

        return {
            "answer": answer,
            "formula": formula,
            "confidence_score": 0.99
        }

    async def _calculate_metric(
        self,
        metric_key: str,
        temporal_info: Dict,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Calculate a metric for a specific period"""
        if not metric_key or metric_key not in self.FORMULAS:
            return {"answer": "I need to know which metric to calculate."}

        # Get property and period
        property_id = context.get("property_id") if context else None
        if not property_id:
            return {"answer": "I need a property ID to calculate metrics."}

        # Get period from temporal info
        if temporal_info and temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            year = filters.get("year")
            month = filters.get("month")
        else:
            # Use latest period
            from app.models.financial_period import FinancialPeriod
            latest_period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == property_id
            ).order_by(
                FinancialPeriod.period_year.desc(),
                FinancialPeriod.period_month.desc()
            ).first()

            if not latest_period:
                return {"answer": "No financial data found for this property."}

            year = latest_period.period_year
            month = latest_period.period_month

        # Get period
        from app.models.financial_period import FinancialPeriod
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == year,
            FinancialPeriod.period_month == month
        ).first()

        if not period:
            return {"answer": f"No data found for {year}-{month:02d}"}

        # Calculate metrics
        metrics = self.metrics_service.calculate_all_metrics(property_id, period.id)

        # Get the requested metric value
        metric_value = getattr(metrics, metric_key, None)

        if metric_value is None:
            return {"answer": f"Could not calculate {metric_key} for this period."}

        formula = self.FORMULAS[metric_key]

        # Format answer
        answer = f"**{formula['name']} for {year}-{month:02d}**\n\n"

        if isinstance(metric_value, float):
            if metric_key in ["dscr", "current_ratio", "quick_ratio", "debt_to_equity"]:
                answer += f"**Value:** {metric_value:.2f}\n\n"
            else:
                answer += f"**Value:** {metric_value:,.2f}\n\n"
        else:
            answer += f"**Value:** ${metric_value:,.2f}\n\n"

        # Add interpretation based on benchmarks
        if "benchmark" in formula and isinstance(formula["benchmark"], dict):
            for level, threshold in formula["benchmark"].items():
                # Simple threshold checking (can be made more sophisticated)
                answer += f"\n**Assessment:** "
                if metric_value is not None:
                    # This is simplified - actual benchmark comparison would be more complex
                    answer += f"See benchmarks in formula explanation"
                break

        answer += f"\n\n**Formula:** `{formula['formula']}`"

        return {
            "answer": answer,
            "data": {
                "metric": metric_key,
                "value": float(metric_value) if metric_value else None,
                "period": f"{year}-{month:02d}",
                "property_id": property_id
            },
            "confidence_score": 0.95
        }

    async def _interpret_metric(
        self,
        metric_key: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Interpret what a metric value means"""
        if not metric_key or metric_key not in self.FORMULAS:
            return {"answer": "I need to know which metric to interpret."}

        formula = self.FORMULAS[metric_key]

        answer = f"**Understanding {formula['name']}**\n\n"
        answer += f"{formula['interpretation']}\n\n"

        if "benchmark" in formula and isinstance(formula["benchmark"], dict):
            answer += "**What the values mean:**\n\n"
            for level, value in formula["benchmark"].items():
                answer += f"• **{level.capitalize()}** ({value}): "

                if metric_key == "dscr":
                    if "excellent" in level:
                        answer += "Strong cash flow coverage, low risk\n"
                    elif "good" in level:
                        answer += "Adequate coverage, meets lender requirements\n"
                    elif "acceptable" in level:
                        answer += "Minimal coverage, higher risk\n"
                    else:
                        answer += "Insufficient coverage, refinancing may be difficult\n"
                elif metric_key == "occupancy_rate":
                    if "excellent" in level:
                        answer += "Near full occupancy, optimal performance\n"
                    elif "good" in level:
                        answer += "Healthy occupancy, typical for market\n"
                    elif "acceptable" in level:
                        answer += "Below optimal, may impact NOI\n"
                    else:
                        answer += "Low occupancy, revenue concern\n"
                else:
                    answer += "\n"

        return {
            "answer": answer,
            "formula": formula,
            "confidence_score": 0.95
        }

    async def _list_all_formulas(self) -> Dict[str, Any]:
        """List all available formulas by category"""
        categories = {}
        for key, formula in self.FORMULAS.items():
            cat = formula.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "key": key,
                "name": formula["name"],
                "formula": formula["formula"],
                "critical": formula.get("critical", False)
            })

        answer = "**Available Financial Formulas**\n\n"

        category_names = {
            "liquidity": "💧 Liquidity Ratios",
            "leverage": "⚖️ Leverage Ratios",
            "mortgage": "🏦 Mortgage Metrics",
            "income_statement": "📊 Income Statement Metrics",
            "rent_roll": "🏢 Rent Roll Metrics",
            "balance_sheet": "💰 Balance Sheet Metrics",
            "cash_flow": "💵 Cash Flow Metrics"
        }

        for cat, formulas in categories.items():
            answer += f"**{category_names.get(cat, cat.replace('_', ' ').title())}**\n"
            for f in formulas:
                critical_mark = " ⭐" if f.get("critical") else ""
                answer += f"  • **{f['name']}**{critical_mark}: `{f['formula']}`\n"
            answer += "\n"

        answer += "\nAsk me about any formula for detailed explanation and calculation!"

        return {
            "answer": answer,
            "data": {"categories": categories},
            "confidence_score": 1.0
        }
