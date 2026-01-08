"""
Orchestrator Agent - Routes queries to specialized agents using LangGraph

Manages:
- Intent classification (11 domains)
- Query decomposition (complex → simple)
- Agent routing and execution
- Result synthesis
- Conversation context
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import operator
from sqlalchemy.orm import Session
from loguru import logger

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not available - orchestrator will use simplified routing")
    LANGGRAPH_AVAILABLE = False

from app.services.nlq.agents.financial_data_agent import FinancialDataAgent
from app.services.nlq.agents.formula_agent import FormulaAgent
from app.services.nlq.agents.reconciliation_agent import ReconciliationAgent
from app.services.nlq.agents.audit_agent import AuditAgent
from app.services.nlq.temporal_processor import temporal_processor
from app.config.nlq_config import nlq_config


class QueryState(TypedDict):
    """State for query processing workflow"""
    query: str
    user_id: int
    context: Dict[str, Any]
    temporal_info: Dict[str, Any]
    intent: Dict[str, Any]
    subqueries: List[str]
    agent_results: Annotated[List[Dict], operator.add]
    final_answer: Optional[str]
    confidence_score: float
    error: Optional[str]


class OrchestratorAgent:
    """
    Orchestrates multi-agent query processing

    Flow:
    1. Extract temporal information
    2. Classify intent (which domain/agent)
    3. Decompose complex queries (if needed)
    4. Route to appropriate agent(s)
    5. Synthesize results
    6. Return final answer
    """

    def __init__(self, db: Session, llm=None):
        """Initialize orchestrator"""
        self.db = db
        self.llm = llm

        # Initialize available agents
        self.agents = {
            "financial_data": FinancialDataAgent(db, llm),
            "formula": FormulaAgent(db, llm),
            "reconciliation": ReconciliationAgent(db, llm),
            "audit": AuditAgent(db, llm),
            # Add more agents as they're implemented
            # "anomaly": AnomalyDetectionAgent(db, llm),
            # "validation": ValidationAgent(db, llm),
            # "alert": AlertAgent(db, llm),
        }

        # Build workflow
        if LANGGRAPH_AVAILABLE and nlq_config.ENABLE_MULTI_AGENT:
            self.workflow = self._build_langgraph_workflow()
        else:
            self.workflow = None

    def _build_langgraph_workflow(self) -> StateGraph:
        """Build LangGraph workflow for multi-agent orchestration"""
        workflow = StateGraph(QueryState)

        # Add nodes
        workflow.add_node("extract_temporal", self._extract_temporal_node)
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("decompose_query", self._decompose_query_node)
        workflow.add_node("route_to_agents", self._route_to_agents_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Define edges
        workflow.set_entry_point("extract_temporal")
        workflow.add_edge("extract_temporal", "classify_intent")

        # Conditional: decompose complex queries
        workflow.add_conditional_edges(
            "classify_intent",
            self._should_decompose,
            {
                "decompose": "decompose_query",
                "route": "route_to_agents"
            }
        )

        workflow.add_edge("decompose_query", "route_to_agents")
        workflow.add_edge("route_to_agents", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def process_query(
        self,
        query: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query

        Args:
            query: User's question
            user_id: User ID
            context: Optional context (property_id, etc.)

        Returns:
            Complete answer with metadata
        """
        try:
            if self.workflow and LANGGRAPH_AVAILABLE:
                # Use LangGraph workflow
                return await self._process_with_langgraph(query, user_id, context)
            else:
                # Use simplified routing
                return await self._process_simple(query, user_id, context)

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error: {str(e)}",
                "query": query
            }

    async def _process_with_langgraph(
        self,
        query: str,
        user_id: int,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Process using LangGraph workflow"""
        initial_state = QueryState(
            query=query,
            user_id=user_id,
            context=context or {},
            temporal_info={},
            intent={},
            subqueries=[],
            agent_results=[],
            final_answer=None,
            confidence_score=0.0,
            error=None
        )

        # Run workflow
        final_state = await self.workflow.ainvoke(initial_state)

        return {
            "success": True,
            "answer": final_state["final_answer"],
            "data": final_state.get("agent_results", []),
            "metadata": {
                "intent": final_state.get("intent"),
                "temporal_info": final_state.get("temporal_info"),
                "agents_used": [r.get("agent") for r in final_state.get("agent_results", [])],
                "subqueries": final_state.get("subqueries", [])
            },
            "confidence_score": final_state.get("confidence_score", 0.0),
            "query": query
        }

    async def _process_simple(
        self,
        query: str,
        user_id: int,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Simplified routing without LangGraph"""
        # 1. Extract temporal info
        temporal_info = temporal_processor.extract_temporal_info(query)

        # 2. Classify intent
        intent = self._classify_intent_simple(query)

        # 3. Route to agent
        agent_name = intent.get("agent", "financial_data")
        if agent_name not in self.agents:
            agent_name = "financial_data"

        agent = self.agents[agent_name]

        # 4. Process with agent
        result = await agent.process_query(query, context)

        return result

    def _extract_temporal_node(self, state: QueryState) -> QueryState:
        """Extract temporal information from query"""
        temporal_info = temporal_processor.extract_temporal_info(state["query"])
        state["temporal_info"] = temporal_info
        return state

    def _classify_intent_node(self, state: QueryState) -> QueryState:
        """Classify query intent and determine target agent"""
        intent = self._classify_intent_simple(state["query"])
        state["intent"] = intent
        return state

    def _classify_intent_simple(self, query: str) -> Dict[str, Any]:
        """Simple rule-based intent classification"""
        query_lower = query.lower()

        # Domain keywords for each agent
        domain_keywords = {
            "formula": [
                "how is", "calculated", "formula", "calculate", "dscr", "ratio",
                "current ratio", "ltv", "debt service", "noi", "metric"
            ],
            "financial_data": [
                "what was", "show me", "balance sheet", "income statement",
                "cash flow", "revenue", "expense", "assets", "liabilities",
                "rent roll", "mortgage", "cash position"
            ],
            "audit": [
                "who changed", "audit", "history", "modified", "when was",
                "audit trail", "changes", "revision"
            ],
            "anomaly": [
                "anomaly", "unusual", "spike", "drop", "variance", "outlier",
                "different", "unexpected"
            ],
            "reconciliation": [
                "reconcile", "difference", "match", "discrepancy", "variance",
                "pdf vs database", "compare"
            ]
        }

        # Score each domain
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[domain] = score

        # Get highest scoring domain
        if scores:
            primary_domain = max(scores, key=scores.get)
        else:
            primary_domain = "financial_data"  # Default

        return {
            "primary_domain": primary_domain,
            "agent": primary_domain,
            "scores": scores,
            "is_complex": len(scores) > 1  # Multiple domains = complex
        }

    def _should_decompose(self, state: QueryState) -> str:
        """Decide if query needs decomposition"""
        intent = state.get("intent", {})

        # Decompose if:
        # 1. Multiple domains detected
        # 2. Query has "and" or "compare"
        # 3. Temporal info has ranges

        if intent.get("is_complex"):
            return "decompose"

        query_lower = state["query"].lower()
        if any(word in query_lower for word in [" and ", "compare", "versus", "vs"]):
            return "decompose"

        temporal_info = state.get("temporal_info", {})
        if temporal_info.get("temporal_type") == "range":
            return "decompose"

        return "route"

    def _decompose_query_node(self, state: QueryState) -> QueryState:
        """Decompose complex query into sub-queries"""
        query = state["query"]
        query_lower = query.lower()

        subqueries = []

        # Simple decomposition rules
        if " and " in query_lower:
            # Split on "and"
            parts = query.split(" and ")
            subqueries.extend(parts)

        elif "compare" in query_lower:
            # Extract comparison subjects
            # This is simplified - production would use LLM
            if "between" in query_lower:
                # "Compare X between A and B"
                subqueries = [query]  # Keep as single for now
            else:
                subqueries = [query]

        else:
            subqueries = [query]

        state["subqueries"] = subqueries if subqueries else [query]
        return state

    async def _route_to_agents_node(self, state: QueryState) -> QueryState:
        """Route query/subqueries to appropriate agents"""
        subqueries = state.get("subqueries") or [state["query"]]
        agent_results = []

        for subquery in subqueries:
            # Classify each subquery
            intent = self._classify_intent_simple(subquery)
            agent_name = intent.get("agent", "financial_data")

            if agent_name in self.agents:
                agent = self.agents[agent_name]
                result = await agent.process_query(subquery, state["context"])
                agent_results.append(result)

        state["agent_results"] = agent_results
        return state

    def _synthesize_node(self, state: QueryState) -> QueryState:
        """Synthesize results from multiple agents"""
        agent_results = state.get("agent_results", [])

        if not agent_results:
            state["final_answer"] = "I couldn't process your query."
            state["confidence_score"] = 0.0
            return state

        if len(agent_results) == 1:
            # Single agent result
            result = agent_results[0]
            state["final_answer"] = result.get("answer", "No answer available")
            state["confidence_score"] = result.get("confidence_score", 0.0)
        else:
            # Multiple agent results - combine them
            combined_answer = ""
            total_confidence = 0.0

            for i, result in enumerate(agent_results, 1):
                combined_answer += f"**Part {i}:**\n{result.get('answer', '')}\n\n"
                total_confidence += result.get("confidence_score", 0.0)

            state["final_answer"] = combined_answer.strip()
            state["confidence_score"] = total_confidence / len(agent_results)

        return state


# Singleton pattern for use in API
_orchestrator_instance = None


def get_orchestrator(db: Session) -> OrchestratorAgent:
    """Get or create orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestratorAgent(db)
    return _orchestrator_instance
