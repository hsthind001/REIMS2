"""
Financial Data Agent - Specialized agent for financial statement queries with temporal support

Handles queries about:
- Balance sheets (assets, liabilities, equity)
- Income statements (revenue, expenses, net income)
- Cash flow statements
- Rent rolls
- Mortgage statements
- Property financial metrics
- Time-series analysis and comparisons

Examples:
- "What was the cash position in November 2025?"
- "Show me total revenue for Q4 2025"
- "Compare net income between August and December 2025"
- "What are the A/R Tenants balances for last 6 months?"
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from loguru import logger

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.chart_of_accounts import ChartOfAccounts

from app.services.nlq.temporal_processor import temporal_processor
from app.config.nlq_config import nlq_config


class FinancialDataAgent:
    """
    Specialized agent for financial data queries with temporal awareness

    Features:
    - Automatic statement type detection
    - Temporal query parsing
    - Chart of accounts lookup
    - Multi-period comparisons
    - Aggregations (sum, avg, trend)
    - Natural language response generation
    """

    def __init__(self, db: Session, llm=None):
        """
        Initialize financial data agent

        Args:
            db: Database session
            llm: Language model for natural language generation
        """
        self.db = db
        self.llm = llm

        # Load chart of accounts for context
        self.chart_of_accounts = self._load_chart_of_accounts()

        # Statement type mappings
        self.statement_models = {
            "balance_sheet": BalanceSheetData,
            "income_statement": IncomeStatementData,
            "cash_flow": CashFlowData,
            "rent_roll": RentRollData,
            "mortgage_statement": MortgageStatementData
        }

    def _load_chart_of_accounts(self) -> Dict[str, Dict]:
        """Load chart of accounts mapping"""
        coa_records = self.db.query(ChartOfAccounts).all()
        return {
            record.account_code: {
                "name": record.account_name,
                "type": record.account_type,
                "category": record.category,
                "parent_code": record.parent_account_code,
                "level": record.level
            }
            for record in coa_records
        }

    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a financial data query

        Args:
            query: Natural language query
            context: Optional context (property_id, property_code, etc.)

        Returns:
            Query result with answer, data, and metadata
        """
        try:
            # Step 1: Extract temporal information
            temporal_info = temporal_processor.extract_temporal_info(query)
            logger.info(f"Temporal info: {temporal_info}")

            # Step 2: Detect intent (what financial data is needed)
            intent = self._detect_intent(query, context)
            logger.info(f"Detected intent: {intent}")

            # Step 3: Extract property context
            property_info = await self._extract_property_context(query, context)
            logger.info(f"Property context: {property_info}")

            # Step 4: Extract account/metric information
            account_info = self._extract_account_info(query)
            logger.info(f"Account info: {account_info}")

            # Step 5: Build and execute SQL query
            sql_result = await self._execute_financial_query(
                intent=intent,
                temporal_info=temporal_info,
                property_info=property_info,
                account_info=account_info
            )

            # Step 6: Generate natural language answer
            answer = await self._generate_answer(
                query=query,
                intent=intent,
                temporal_info=temporal_info,
                sql_result=sql_result
            )

            return {
                "success": True,
                "answer": answer,
                "data": sql_result.get("data", []),
                "sql_query": sql_result.get("sql_query"),
                "metadata": {
                    "intent": intent,
                    "temporal_info": temporal_info,
                    "property": property_info,
                    "accounts": account_info,
                    "row_count": sql_result.get("row_count", 0)
                },
                "confidence_score": 0.9,  # TODO: Implement confidence calculation
                "agent": "financial_data"
            }

        except Exception as e:
            logger.error(f"Error in financial data agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error while processing your financial query: {str(e)}",
                "agent": "financial_data"
            }

    def _detect_intent(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """
        Detect query intent

        Returns:
            {
                "statement_type": str,
                "query_type": "lookup|aggregation|comparison|trend",
                "aggregation": "sum|avg|count|min|max",
                "comparison_type": "period_over_period|year_over_year"
            }
        """
        query_lower = query.lower()

        # Detect statement type
        statement_type = None
        if any(word in query_lower for word in ["balance sheet", "asset", "liability", "equity", "cash position"]):
            statement_type = "balance_sheet"
        elif any(word in query_lower for word in ["income statement", "revenue", "expense", "net income", "noi"]):
            statement_type = "income_statement"
        elif any(word in query_lower for word in ["cash flow", "operating cash", "cash from operations"]):
            statement_type = "cash_flow"
        elif any(word in query_lower for word in ["rent roll", "tenant", "occupancy", "lease"]):
            statement_type = "rent_roll"
        elif any(word in query_lower for word in ["mortgage", "debt service", "principal", "interest"]):
            statement_type = "mortgage_statement"
        elif any(word in query_lower for word in ["metric", "ratio", "dscr", "ltv", "current ratio"]):
            statement_type = "metrics"

        # Detect query type
        query_type = "lookup"  # default
        if any(word in query_lower for word in ["total", "sum", "aggregate"]):
            query_type = "aggregation"
        elif any(word in query_lower for word in ["compare", "comparison", "vs", "versus", "difference"]):
            query_type = "comparison"
        elif any(word in query_lower for word in ["trend", "over time", "historical", "change"]):
            query_type = "trend"

        # Detect aggregation type
        aggregation = None
        if "total" in query_lower or "sum" in query_lower:
            aggregation = "sum"
        elif "average" in query_lower or "avg" in query_lower or "mean" in query_lower:
            aggregation = "avg"
        elif "count" in query_lower or "number of" in query_lower:
            aggregation = "count"
        elif "maximum" in query_lower or "highest" in query_lower:
            aggregation = "max"
        elif "minimum" in query_lower or "lowest" in query_lower:
            aggregation = "min"

        # Detect comparison type
        comparison_type = None
        if query_type == "comparison":
            if any(word in query_lower for word in ["month over month", "mom", "previous month"]):
                comparison_type = "month_over_month"
            elif any(word in query_lower for word in ["year over year", "yoy", "previous year"]):
                comparison_type = "year_over_year"
            elif "between" in query_lower:
                comparison_type = "range_comparison"

        return {
            "statement_type": statement_type,
            "query_type": query_type,
            "aggregation": aggregation,
            "comparison_type": comparison_type
        }

    async def _extract_property_context(
        self,
        query: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Extract property information from query or context"""
        property_info = {}

        # From context
        if context:
            if "property_id" in context:
                property_info["property_id"] = context["property_id"]
            if "property_code" in context:
                property_info["property_code"] = context["property_code"]
            if "property_name" in context:
                property_info["property_name"] = context["property_name"]

        # From query - look for property names or codes
        if not property_info:
            # Try to match known properties
            properties = self.db.query(Property).all()
            for prop in properties:
                if prop.property_code.lower() in query.lower() or \
                   (prop.property_name and prop.property_name.lower() in query.lower()):
                    property_info = {
                        "property_id": prop.id,
                        "property_code": prop.property_code,
                        "property_name": prop.property_name
                    }
                    break

        return property_info

    def _extract_account_info(self, query: str) -> Dict[str, Any]:
        """
        Extract account codes and names from query

        Looks for:
        - Account codes (e.g., "0122", "1310")
        - Account names (e.g., "Cash - Operating", "A/R Tenants")
        - Account categories (e.g., "cash accounts", "receivables")
        """
        query_lower = query.lower()
        matched_accounts = []

        # Match account codes (4-digit)
        account_code_pattern = r'\b\d{4}(?:-\d{4})?\b'
        code_matches = re.findall(account_code_pattern, query)
        for code in code_matches:
            if code in self.chart_of_accounts:
                matched_accounts.append({
                    "code": code,
                    "name": self.chart_of_accounts[code]["name"],
                    "type": self.chart_of_accounts[code]["type"]
                })

        # Match account names
        for code, info in self.chart_of_accounts.items():
            account_name_lower = info["name"].lower()
            if account_name_lower in query_lower:
                matched_accounts.append({
                    "code": code,
                    "name": info["name"],
                    "type": info["type"]
                })

        # Match account categories
        categories = []
        category_mappings = {
            "cash": ["cash", "cash accounts"],
            "receivables": ["receivable", "a/r", "accounts receivable"],
            "payables": ["payable", "a/p", "accounts payable"],
            "assets": ["asset", "assets"],
            "liabilities": ["liability", "liabilities"],
            "equity": ["equity", "capital"],
            "revenue": ["revenue", "income"],
            "expenses": ["expense", "expenses"]
        }

        for category, keywords in category_mappings.items():
            if any(keyword in query_lower for keyword in keywords):
                categories.append(category)

        return {
            "accounts": matched_accounts,
            "categories": categories,
            "has_specific_accounts": len(matched_accounts) > 0
        }

    async def _execute_financial_query(
        self,
        intent: Dict[str, Any],
        temporal_info: Dict[str, Any],
        property_info: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute financial database query

        Returns:
            {
                "data": List[Dict],
                "sql_query": str,
                "row_count": int
            }
        """
        statement_type = intent.get("statement_type")
        if not statement_type or statement_type not in self.statement_models:
            return {"data": [], "sql_query": None, "row_count": 0}

        Model = self.statement_models[statement_type]

        # Build query
        query = self.db.query(Model)

        # Apply property filter
        if property_info.get("property_id"):
            query = query.filter(Model.property_id == property_info["property_id"])
        elif property_info.get("property_code"):
            # Join with Property model
            query = query.join(Property).filter(
                Property.property_code == property_info["property_code"]
            )

        # Apply temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})

            if "year" in filters and "month" in filters:
                # Specific month
                query = query.filter(
                    and_(
                        Model.year == filters["year"],
                        Model.month == filters["month"]
                    )
                )
            elif "year" in filters:
                # Entire year
                query = query.filter(Model.year == filters["year"])

            elif "start_date" in filters and "end_date" in filters:
                # Date range - need to join with FinancialPeriod or filter by year/month
                start_year = int(filters["start_date"][:4])
                start_month = int(filters["start_date"][5:7])
                end_year = int(filters["end_date"][:4])
                end_month = int(filters["end_date"][5:7])

                query = query.filter(
                    or_(
                        and_(Model.year == start_year, Model.month >= start_month),
                        and_(Model.year > start_year, Model.year < end_year),
                        and_(Model.year == end_year, Model.month <= end_month)
                    )
                )

        # Apply account filters
        if account_info.get("has_specific_accounts"):
            account_codes = [acc["code"] for acc in account_info["accounts"]]
            if hasattr(Model, 'account_code'):
                query = query.filter(Model.account_code.in_(account_codes))

        # Apply aggregation
        query_type = intent.get("query_type")
        aggregation = intent.get("aggregation")

        if query_type == "aggregation" and aggregation and hasattr(Model, 'amount'):
            if aggregation == "sum":
                result = query.with_entities(func.sum(Model.amount)).scalar()
                data = [{"total": float(result) if result else 0.0}]
            elif aggregation == "avg":
                result = query.with_entities(func.avg(Model.amount)).scalar()
                data = [{"average": float(result) if result else 0.0}]
            elif aggregation == "count":
                result = query.count()
                data = [{"count": result}]
            else:
                data = [row.to_dict() for row in query.all()]
        else:
            # Regular query
            results = query.limit(nlq_config.SQL_MAX_ROWS).all()
            data = [row.to_dict() for row in results]

        # Generate SQL for transparency
        try:
            sql_query = str(query.statement.compile(
                compile_kwargs={"literal_binds": True}
            ))
        except:
            sql_query = str(query.statement)

        return {
            "data": data,
            "sql_query": sql_query,
            "row_count": len(data)
        }

    async def _generate_answer(
        self,
        query: str,
        intent: Dict[str, Any],
        temporal_info: Dict[str, Any],
        sql_result: Dict[str, Any]
    ) -> str:
        """
        Generate natural language answer from query results

        Args:
            query: Original query
            intent: Detected intent
            temporal_info: Temporal information
            sql_result: SQL execution results

        Returns:
            Natural language answer
        """
        data = sql_result.get("data", [])
        row_count = sql_result.get("row_count", 0)

        if row_count == 0:
            return "I couldn't find any data matching your query. Please check the property, time period, or account details."

        # Generate contextual answer based on intent
        if intent.get("query_type") == "aggregation":
            # Aggregation result
            if data and len(data) == 1:
                value = data[0].get("total") or data[0].get("average") or data[0].get("count")
                agg_type = intent.get("aggregation", "value")

                temporal_context = temporal_info.get("normalized_expression", "the specified period")

                answer = f"The {agg_type} for {temporal_context} is "
                if isinstance(value, (int, float)):
                    answer += f"${value:,.2f}"
                else:
                    answer += str(value)

                return answer

        elif intent.get("query_type") == "comparison":
            # Comparison result
            if len(data) >= 2:
                answer = f"Here's the comparison:\n\n"
                for row in data[:5]:  # Show top 5
                    period = f"{row.get('year', 'N/A')}-{row.get('month', 'N/A'):02d}" if 'year' in row else "Unknown"
                    amount = row.get('amount', row.get('total', 0))
                    answer += f"• {period}: ${amount:,.2f}\n"
                return answer.strip()

        elif intent.get("query_type") == "trend":
            # Trend analysis
            if len(data) > 1:
                first_value = data[0].get('amount', 0)
                last_value = data[-1].get('amount', 0)
                change = last_value - first_value
                pct_change = (change / first_value * 100) if first_value != 0 else 0

                direction = "increased" if change > 0 else "decreased"
                answer = f"The trend shows that the value has {direction} by ${abs(change):,.2f} ({abs(pct_change):.1f}%) over the period."
                return answer

        # Default: return first few rows with formatting
        answer = f"I found {row_count} record(s):\n\n"
        for i, row in enumerate(data[:5], 1):
            # Format key fields
            row_str = f"**Record {i}:**\n"
            for key, value in row.items():
                if key in ['amount', 'total', 'balance']:
                    row_str += f"  • {key}: ${value:,.2f}\n"
                elif isinstance(value, (int, float)):
                    row_str += f"  • {key}: {value:,.2f}\n"
                else:
                    row_str += f"  • {key}: {value}\n"
            answer += row_str + "\n"

        if row_count > 5:
            answer += f"\n_(Showing 5 of {row_count} records)_"

        return answer.strip()
