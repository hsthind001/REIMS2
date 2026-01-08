"""
Reconciliation Agent - Cross-statement analysis and reconciliation queries

Handles queries about:
- Three-statement reconciliation (Balance Sheet, Income Statement, Cash Flow)
- Document vs database differences
- Cross-statement validation
- Reconciliation rules from /home/hsthind/Downloads/Reconcile - Aduit - Rules
- Forensic reconciliation

Examples:
- "Why doesn't net income match cash flow?"
- "Reconcile balance sheet to income statement"
- "What are the reconciliation rules for cash flow?"
- "Find differences between PDF and database for November 2025"
- "Explain the three-statement reconciliation"
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from loguru import logger
import os

from app.services.nlq.temporal_processor import temporal_processor
from app.services.nlq.vector_store_manager import vector_store_manager
from app.config.nlq_config import nlq_config


class ReconciliationAgent:
    """
    Specialized agent for reconciliation queries

    Features:
    - Three-statement reconciliation rules
    - Cross-statement analysis
    - PDF vs Database comparison
    - Reconciliation rule explanations
    - RAG from reconciliation documents
    """

    # Reconciliation knowledge from the documents
    RECONCILIATION_RULES = {
        "three_statement_model": {
            "name": "Three Statement Model Integration",
            "description": "How Balance Sheet, Income Statement, and Cash Flow connect",
            "key_rules": [
                "Net Income (IS) → Current Period Earnings (BS)",
                "Net Income (IS) → Starting point of Cash Flow (CF)",
                "Cash Flow (CF) → Change in Cash accounts (BS)",
                "Depreciation: IS expense → BS accumulated → CF add-back",
                "Every BS change explained by IS or CF activity"
            ],
            "source": "complete_three_statement_reconciliation.md"
        },
        "net_income_to_equity": {
            "name": "Net Income to Balance Sheet",
            "formula": "IS Net Income = Change in BS Current Period Earnings",
            "explanation": "Profit from Income Statement accumulates in equity",
            "verification": "Monthly change in Current Period Earnings = Net Income for that month",
            "source": "complete_three_statement_reconciliation.md"
        },
        "net_income_to_cash_flow": {
            "name": "Net Income to Cash Flow",
            "formula": "CF starts with Net Income, adjusts to arrive at cash flow",
            "explanation": "Accrual accounting vs cash accounting differences",
            "key_adjustments": [
                "Add back non-cash expenses (depreciation, amortization)",
                "Adjust for working capital changes (A/R, A/P, inventory)",
                "Subtract capital expenditures",
                "Subtract financing activities (debt payments, distributions)"
            ],
            "source": "cash_flow_income_statement_reconciliation.md"
        },
        "cash_flow_to_balance_sheet": {
            "name": "Cash Flow to Balance Sheet Cash",
            "formula": "CF Cash Flow = BS Ending Cash - BS Beginning Cash",
            "explanation": "Cash flow statement explains WHY cash changed",
            "verification": "Beginning Cash + Net Cash Flow = Ending Cash",
            "source": "complete_three_statement_reconciliation.md"
        },
        "depreciation_three_way": {
            "name": "Depreciation Three-Way Reconciliation",
            "flow": [
                "IS: Depreciation Expense (reduces net income)",
                "BS: Accumulated Depreciation (increases, reduces net book value)",
                "CF: Depreciation Add-Back (didn't use cash)"
            ],
            "formula": "IS Depreciation = BS Accum Depr Change = CF Add-Back",
            "explanation": "Same amount appears in all three statements, different purposes",
            "source": "complete_three_statement_reconciliation.md"
        },
        "working_capital_bridge": {
            "name": "Working Capital Bridge",
            "explanation": "Bridges accrual income to cash flow",
            "components": {
                "A/R": "Decrease = cash collected (positive CF adjustment)",
                "A/P": "Increase = deferred payment (positive CF adjustment)",
                "Prepaid": "Increase = cash paid in advance (negative CF adjustment)",
                "Accrued": "Increase = expense recognized but not paid (positive CF adjustment)"
            },
            "source": "cash_flow_rules.md"
        },
        "balance_sheet_equation": {
            "name": "Fundamental Accounting Equation",
            "formula": "Assets = Liabilities + Equity",
            "validation": "Must hold for ALL periods with <1% tolerance",
            "source": "balance_sheet_rules.md"
        },
        "income_statement_equation": {
            "name": "Income Statement Structure",
            "formula": "Net Income = Total Income - Total Expenses - (Interest + Depreciation + Amortization)",
            "noi_formula": "NOI = Total Income - Operating Expenses",
            "source": "income_statement_rules.md"
        },
        "cash_flow_indirect_method": {
            "name": "Indirect Method Cash Flow",
            "formula": "Cash Flow = Net Income + Total Adjustments",
            "explanation": "Starts with accrual income, adjusts to cash basis",
            "source": "cash_flow_rules.md"
        }
    }

    # Common reconciliation questions and answers
    RECONCILIATION_FAQ = {
        "why_net_income_not_equal_cash_flow": {
            "question": "Why doesn't net income match cash flow?",
            "answer": """Net Income and Cash Flow differ because:

**Net Income (Accrual Basis):**
- Revenue when earned (not necessarily collected)
- Expenses when incurred (not necessarily paid)
- Includes non-cash expenses (depreciation, amortization)

**Cash Flow (Cash Basis):**
- Only actual cash movements
- Add back non-cash expenses
- Adjust for timing differences (A/R, A/P)
- Include capital expenditures
- Include financing activities

**Example:**
```
Net Income:           $25,438
+ Depreciation:       $129,625  (add back non-cash)
+ Amortization:       $4,478    (add back non-cash)
+ A/R collected:      $196,438  (cash received)
- A/P paid:          -$108,912  (cash paid)
- CapEx:             -$221,986  (cash spent)
- Debt principal:    -$76,083   (cash paid)
= Cash Flow:         -$56,461   (actual cash change)
```

The business was **profitable** but **used cash** due to large capital investments."""
        },
        "depreciation_reconciliation": {
            "question": "How does depreciation reconcile across statements?",
            "answer": """Depreciation appears in all three statements:

**Income Statement:**
- Depreciation Expense: ~$129,625
- Reduces Net Income
- Non-cash charge

**Balance Sheet:**
- Accumulated Depreciation increases: -$64,727
- Reduces Net Property Value
- Contra-asset account

**Cash Flow:**
- Added back to Net Income: +$129,625
- Didn't actually use cash
- Reverses IS impact

**Why add back?**
Cash was spent when the asset was purchased (CapEx), not when depreciated.
Depreciation allocates that historical cost over time.

**Verification:**
IS Depreciation = BS Accum Depr Change = CF Add-Back ✓"""
        },
        "cash_reconciliation": {
            "question": "How do I reconcile cash between statements?",
            "answer": """Cash reconciliation between Balance Sheet and Cash Flow:

**Method:**
```
Beginning Cash (BS):    $444,961
+ Cash Flow (CF):       -$56,461
= Ending Cash (BS):     $388,500 ✓
```

**Components (BS):**
- Cash - Operating:     $3,375 (constant)
- Cash - Depository:    $119,514
- Cash - Operating PNC: $265,610
= Total Cash:           $388,500 ✓

**Cash Flow explains WHY cash changed:**
1. Operations: Net income adjusted for non-cash items
2. Working capital: A/R, A/P, prepaid changes
3. Investing: CapEx, asset purchases
4. Financing: Debt payments, distributions

Every dollar of cash change is explained in Cash Flow Statement."""
        }
    }

    def __init__(self, db: Session, llm=None):
        """Initialize reconciliation agent"""
        self.db = db
        self.llm = llm
        self.reconciliation_docs_loaded = False

        # Try to load reconciliation documents into vector store
        self._load_reconciliation_knowledge()

    def _load_reconciliation_knowledge(self):
        """Load reconciliation documents into vector store if available"""
        try:
            reconciliation_dir = "/home/hsthind/Downloads/Reconcile - Aduit - Rules"
            if os.path.exists(reconciliation_dir):
                # Documents will be loaded by ingestion script
                self.reconciliation_docs_loaded = True
                logger.info("Reconciliation documents directory found")
            else:
                logger.warning(f"Reconciliation docs not found at {reconciliation_dir}")
        except Exception as e:
            logger.warning(f"Could not check reconciliation docs: {e}")

    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process reconciliation query

        Args:
            query: Natural language query
            context: Optional context

        Returns:
            Query result with reconciliation explanation
        """
        try:
            query_lower = query.lower()

            # Extract temporal info
            temporal_info = temporal_processor.extract_temporal_info(query)

            # Detect reconciliation intent
            intent = self._detect_reconciliation_intent(query_lower)

            # Process based on intent
            if intent["type"] == "three_statement":
                result = await self._explain_three_statement_model()
            elif intent["type"] == "cross_statement":
                result = await self._reconcile_cross_statement(intent, temporal_info, context)
            elif intent["type"] == "rule_lookup":
                result = await self._lookup_reconciliation_rule(intent)
            elif intent["type"] == "pdf_vs_db":
                result = await self._compare_pdf_vs_database(temporal_info, context)
            elif intent["type"] == "faq":
                result = await self._answer_reconciliation_faq(intent)
            else:
                # Use RAG from reconciliation documents
                result = await self._rag_reconciliation_docs(query, temporal_info)

            return {
                "success": True,
                **result,
                "metadata": {
                    "intent": intent,
                    "temporal_info": temporal_info
                },
                "agent": "reconciliation"
            }

        except Exception as e:
            logger.error(f"Reconciliation agent error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error: {str(e)}",
                "agent": "reconciliation"
            }

    def _detect_reconciliation_intent(self, query: str) -> Dict[str, Any]:
        """Detect what type of reconciliation query this is"""
        intent = {"type": "general"}

        # Three-statement model
        if any(phrase in query for phrase in ["three statement", "three-statement", "all three statements"]):
            intent["type"] = "three_statement"

        # Cross-statement reconciliation
        elif any(phrase in query for phrase in [
            "balance sheet to income statement",
            "income statement to cash flow",
            "cash flow to balance sheet",
            "reconcile", "why doesn't", "why don't"
        ]):
            intent["type"] = "cross_statement"

            # Identify which statements
            statements = []
            if "balance sheet" in query or "bs" in query:
                statements.append("balance_sheet")
            if "income statement" in query or "is" in query or "p&l" in query:
                statements.append("income_statement")
            if "cash flow" in query or "cf" in query:
                statements.append("cash_flow")

            intent["statements"] = statements

        # Rule lookup
        elif any(phrase in query for phrase in ["rule", "what are the rules", "reconciliation rules"]):
            intent["type"] = "rule_lookup"

        # PDF vs Database
        elif any(phrase in query for phrase in ["pdf vs database", "pdf versus database", "differences", "discrepancies"]):
            intent["type"] = "pdf_vs_db"

        # FAQ
        elif any(phrase in query for phrase in [
            "why doesn't net income match",
            "why net income different",
            "depreciation reconcile",
            "how do i reconcile cash"
        ]):
            intent["type"] = "faq"

            # Match specific FAQ
            for faq_key, faq_data in self.RECONCILIATION_FAQ.items():
                if any(keyword in query for keyword in faq_data["question"].lower().split()):
                    intent["faq_key"] = faq_key
                    break

        return intent

    async def _explain_three_statement_model(self) -> Dict[str, Any]:
        """Explain the three-statement model integration"""
        rule = self.RECONCILIATION_RULES["three_statement_model"]

        answer = f"**{rule['name']}**\n\n"
        answer += f"{rule['description']}\n\n"

        answer += "**Key Integration Rules:**\n\n"
        for i, key_rule in enumerate(rule["key_rules"], 1):
            answer += f"{i}. {key_rule}\n"

        answer += "\n**The Three Statements Tell One Complete Story:**\n\n"
        answer += "📊 **Income Statement** - How profitable was the business?\n"
        answer += "   • Revenue earned and expenses incurred\n"
        answer += "   • Net Income (the \"score\")\n\n"

        answer += "💰 **Balance Sheet** - What does the business own and owe?\n"
        answer += "   • Assets, Liabilities, Equity\n"
        answer += "   • Financial position at a point in time\n\n"

        answer += "💵 **Cash Flow** - Where did cash come from and go?\n"
        answer += "   • Bridge between profit and cash\n"
        answer += "   • Explains cash changes from operations, investing, financing\n\n"

        answer += "**Critical Reconciliations:**\n\n"
        answer += "1. **Net Income Flow:**\n"
        answer += "   ```\n"
        answer += "   Income Statement → Net Income\n"
        answer += "          ↓\n"
        answer += "   Balance Sheet → Current Period Earnings (equity)\n"
        answer += "          ↓\n"
        answer += "   Cash Flow → Starting point, adjusted to cash\n"
        answer += "   ```\n\n"

        answer += "2. **Depreciation Three-Way:**\n"
        answer += "   - IS: Expense (reduces profit)\n"
        answer += "   - BS: Accumulated (reduces asset value)\n"
        answer += "   - CF: Add-back (didn't use cash)\n\n"

        answer += "3. **Cash Reconciliation:**\n"
        answer += "   - Beginning Cash (BS) + Cash Flow (CF) = Ending Cash (BS)\n\n"

        answer += f"\n**Source:** {rule['source']}"

        return {
            "answer": answer,
            "data": rule,
            "confidence_score": 1.0
        }

    async def _reconcile_cross_statement(
        self,
        intent: Dict,
        temporal_info: Dict,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Reconcile between specific statements"""
        statements = intent.get("statements", [])

        if "net_income" in intent or len(statements) >= 2:
            # Common case: reconciling net income
            answer = self.RECONCILIATION_FAQ["why_net_income_not_equal_cash_flow"]["answer"]

            # Add specific period data if available
            if temporal_info.get("has_temporal"):
                answer += f"\n\n**Period:** {temporal_info.get('normalized_expression')}"

            return {
                "answer": answer,
                "confidence_score": 0.95
            }

        # Generic cross-statement reconciliation
        answer = "**Cross-Statement Reconciliation**\n\n"
        answer += "The financial statements are interconnected:\n\n"

        for rule_key, rule_data in self.RECONCILIATION_RULES.items():
            if rule_key.endswith("_to_"):
                answer += f"• **{rule_data['name']}**\n"
                answer += f"  Formula: `{rule_data.get('formula', 'See details')}`\n"
                answer += f"  {rule_data.get('explanation', '')}\n\n"

        return {
            "answer": answer,
            "confidence_score": 0.85
        }

    async def _lookup_reconciliation_rule(self, intent: Dict) -> Dict[str, Any]:
        """Look up specific reconciliation rule"""
        # List all rules
        answer = "**Reconciliation Rules:**\n\n"

        categories = {
            "Fundamental Equations": ["balance_sheet_equation", "income_statement_equation", "cash_flow_indirect_method"],
            "Cross-Statement": ["net_income_to_equity", "net_income_to_cash_flow", "cash_flow_to_balance_sheet"],
            "Special Items": ["depreciation_three_way", "working_capital_bridge"]
        }

        for category, rule_keys in categories.items():
            answer += f"**{category}:**\n\n"
            for rule_key in rule_keys:
                if rule_key in self.RECONCILIATION_RULES:
                    rule = self.RECONCILIATION_RULES[rule_key]
                    answer += f"• **{rule['name']}**\n"
                    if "formula" in rule:
                        answer += f"  ```{rule['formula']}```\n"
                    answer += f"  {rule.get('explanation', '')}\n\n"

        return {
            "answer": answer,
            "confidence_score": 1.0
        }

    async def _compare_pdf_vs_database(
        self,
        temporal_info: Dict,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Compare PDF vs database values"""
        answer = "**PDF vs Database Reconciliation**\n\n"

        answer += "To find differences between PDF and database:\n\n"
        answer += "1. **Download PDF** from MinIO storage\n"
        answer += "2. **Extract data** using multi-engine extraction\n"
        answer += "3. **Compare** to database records\n"
        answer += "4. **Detect differences:**\n"
        answer += "   - Amount discrepancies\n"
        answer += "   - Missing accounts (in PDF but not DB)\n"
        answer += "   - Extra accounts (in DB but not PDF)\n\n"

        answer += "**Reconciliation Service:**\n"
        answer += "```python\n"
        answer += "from app.services.reconciliation_service import ReconciliationService\n"
        answer += "service = ReconciliationService(db)\n"
        answer += "session = service.start_reconciliation(property_id, period_id)\n"
        answer += "differences = service.get_differences(session.id)\n"
        answer += "```\n\n"

        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            answer += f"**Period:** {temporal_info.get('normalized_expression')}\n"
            if "year" in filters and "month" in filters:
                answer += f"**Filters:** Year={filters['year']}, Month={filters['month']}\n"

        return {
            "answer": answer,
            "confidence_score": 0.90
        }

    async def _answer_reconciliation_faq(self, intent: Dict) -> Dict[str, Any]:
        """Answer common reconciliation FAQ"""
        faq_key = intent.get("faq_key")

        if faq_key and faq_key in self.RECONCILIATION_FAQ:
            faq = self.RECONCILIATION_FAQ[faq_key]
            return {
                "answer": faq["answer"],
                "confidence_score": 0.98
            }

        # Default: list all FAQs
        answer = "**Common Reconciliation Questions:**\n\n"
        for faq_key, faq_data in self.RECONCILIATION_FAQ.items():
            answer += f"**Q: {faq_data['question']}**\n\n"
            answer += f"{faq_data['answer'][:200]}...\n\n"
            answer += "---\n\n"

        return {
            "answer": answer,
            "confidence_score": 0.85
        }

    async def _rag_reconciliation_docs(
        self,
        query: str,
        temporal_info: Dict
    ) -> Dict[str, Any]:
        """Use RAG to search reconciliation documents"""
        try:
            # Search vector store for relevant reconciliation rules
            if nlq_config.ENABLE_HYBRID_SEARCH:
                results = vector_store_manager.hybrid_search(
                    query=query,
                    collection_name=nlq_config.QDRANT_DOCUMENTS_COLLECTION,
                    temporal_filters=temporal_info.get("filters") if temporal_info.get("has_temporal") else None,
                    top_k=5
                )
            else:
                results = vector_store_manager.search(
                    query=query,
                    collection_name=nlq_config.QDRANT_DOCUMENTS_COLLECTION,
                    temporal_filters=temporal_info.get("filters") if temporal_info.get("has_temporal") else None,
                    top_k=5
                )

            if results:
                # Format answer from search results
                answer = "Based on reconciliation rules:\n\n"
                for i, result in enumerate(results[:3], 1):
                    answer += f"**{i}. {result.get('metadata', {}).get('source', 'Source')}**\n"
                    answer += f"{result.get('text', '')[:300]}...\n\n"

                return {
                    "answer": answer,
                    "data": results,
                    "confidence_score": 0.85
                }

        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        # Fallback: provide general reconciliation guidance
        return {
            "answer": "I can help with reconciliation queries. Ask me about:\n\n"
                     "• Three-statement reconciliation\n"
                     "• Why net income ≠ cash flow\n"
                     "• Depreciation reconciliation\n"
                     "• Cash reconciliation\n"
                     "• PDF vs database differences\n"
                     "• Specific reconciliation rules",
            "confidence_score": 0.70
        }
