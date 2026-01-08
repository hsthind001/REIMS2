"""
Audit Trail Agent - Handles queries about data changes and user actions

Capabilities:
1. Track who changed what data and when
2. View audit history for specific properties/accounts
3. Analyze modification patterns
4. Detect unusual activity
5. Compliance reporting

Supported Queries:
- "Who changed cash position in November 2025?"
- "Show me audit history for property ESP"
- "What was modified last week?"
- "List all changes by user John Doe"
- "Show me changes to account 1010 in Q4 2025"
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from loguru import logger

from app.services.nlq.temporal_processor import temporal_processor
from app.db.models import (
    AuditLog,
    User,
    Property,
    BalanceSheetData,
    IncomeStatementData,
    CashFlowData,
    RentRollData,
    MortgageStatementData
)


class AuditAgent:
    """
    Specialized agent for audit trail queries

    Handles:
    - Data modification history
    - User activity tracking
    - Change detection and analysis
    - Compliance reporting
    """

    def __init__(self, db: Session, llm=None):
        """Initialize audit agent"""
        self.db = db
        self.llm = llm

        # Supported audit query types
        self.QUERY_TYPES = {
            "who_changed": {
                "keywords": ["who changed", "who modified", "who updated", "who edited"],
                "description": "Find who made specific changes"
            },
            "what_changed": {
                "keywords": ["what changed", "what was modified", "changes to", "modifications"],
                "description": "Find what was changed in a period"
            },
            "when_changed": {
                "keywords": ["when was", "when did", "date of change", "modification date"],
                "description": "Find when changes occurred"
            },
            "user_activity": {
                "keywords": ["activity by", "changes by", "user", "made by"],
                "description": "Track specific user activity"
            },
            "property_history": {
                "keywords": ["history for", "audit trail for", "changes for property"],
                "description": "Full audit history for property"
            },
            "account_history": {
                "keywords": ["account changes", "account history", "modifications to account"],
                "description": "Audit trail for specific account"
            },
            "recent_changes": {
                "keywords": ["recent changes", "latest modifications", "what's new"],
                "description": "Recent system activity"
            }
        }

        # Statement type mapping
        self.STATEMENT_MODELS = {
            "balance_sheet": BalanceSheetData,
            "income_statement": IncomeStatementData,
            "cash_flow": CashFlowData,
            "rent_roll": RentRollData,
            "mortgage_statement": MortgageStatementData
        }

    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process audit-related query

        Args:
            query: Natural language audit query
            context: Optional context (property_id, user_id, etc.)

        Returns:
            Audit trail information and natural language answer
        """
        try:
            # 1. Extract temporal information
            temporal_info = temporal_processor.extract_temporal_info(query)

            # 2. Detect audit query type
            query_type = self._detect_audit_query_type(query)

            # 3. Extract entity information (property, account, user)
            entities = self._extract_entities(query, context)

            # 4. Build and execute audit query
            audit_results = await self._execute_audit_query(
                query_type=query_type,
                temporal_info=temporal_info,
                entities=entities,
                context=context
            )

            # 5. Generate natural language answer
            answer = await self._generate_answer(
                query=query,
                query_type=query_type,
                results=audit_results,
                temporal_info=temporal_info,
                entities=entities
            )

            return {
                "success": True,
                "answer": answer,
                "data": audit_results,
                "metadata": {
                    "query_type": query_type,
                    "temporal_info": temporal_info,
                    "entities": entities,
                    "result_count": len(audit_results) if isinstance(audit_results, list) else 1
                },
                "confidence_score": 0.85
            }

        except Exception as e:
            logger.error(f"Audit agent error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"I encountered an error processing your audit query: {str(e)}",
                "confidence_score": 0.0
            }

    def _detect_audit_query_type(self, query: str) -> str:
        """Detect the type of audit query"""
        query_lower = query.lower()

        # Score each query type
        scores = {}
        for query_type, config in self.QUERY_TYPES.items():
            score = sum(1 for keyword in config["keywords"] if keyword in query_lower)
            if score > 0:
                scores[query_type] = score

        # Return highest scoring type
        if scores:
            return max(scores, key=scores.get)

        # Default to recent changes
        return "recent_changes"

    def _extract_entities(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract property, account, and user information from query"""
        entities = {
            "property_id": context.get("property_id") if context else None,
            "property_code": context.get("property_code") if context else None,
            "user_id": None,
            "user_name": None,
            "account_code": None,
            "account_name": None,
            "statement_type": None
        }

        query_lower = query.lower()

        # Extract property code (ESP, OAK, etc.)
        property_codes = ["esp", "oak", "pin", "map", "elm"]  # Add more as needed
        for code in property_codes:
            if code in query_lower:
                entities["property_code"] = code.upper()
                break

        # Extract account code (1010, 5000, etc.)
        import re
        account_match = re.search(r'\b(\d{4})\b', query)
        if account_match:
            entities["account_code"] = account_match.group(1)

        # Extract user name
        user_keywords = ["by user", "user", "by"]
        for keyword in user_keywords:
            if keyword in query_lower:
                # Simple extraction - production would use NER
                words_after = query_lower.split(keyword)[1].split()[:2]
                if words_after:
                    entities["user_name"] = " ".join(words_after).strip(" ,.?")

        # Detect statement type
        statement_keywords = {
            "balance_sheet": ["balance sheet", "assets", "liabilities", "cash position"],
            "income_statement": ["income statement", "revenue", "expenses", "net income"],
            "cash_flow": ["cash flow", "operating cash", "free cash flow"],
            "rent_roll": ["rent roll", "occupancy", "rent"],
            "mortgage_statement": ["mortgage", "loan", "debt service"]
        }

        for stmt_type, keywords in statement_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                entities["statement_type"] = stmt_type
                break

        return entities

    async def _execute_audit_query(
        self,
        query_type: str,
        temporal_info: Dict[str, Any],
        entities: Dict[str, Any],
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Execute audit database query based on detected type"""

        # Build base query
        query = self.db.query(AuditLog).join(User, AuditLog.user_id == User.id)

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})

            if "start_date" in filters and "end_date" in filters:
                start = datetime.fromisoformat(filters["start_date"])
                end = datetime.fromisoformat(filters["end_date"])
                query = query.filter(AuditLog.timestamp.between(start, end))

            elif "year" in filters and "month" in filters:
                year = filters["year"]
                month = filters["month"]
                start = datetime(year, month, 1)
                if month == 12:
                    end = datetime(year + 1, 1, 1)
                else:
                    end = datetime(year, month + 1, 1)
                query = query.filter(AuditLog.timestamp.between(start, end))

            elif "year" in filters:
                year = filters["year"]
                start = datetime(year, 1, 1)
                end = datetime(year + 1, 1, 1)
                query = query.filter(AuditLog.timestamp.between(start, end))

        # Add entity filters
        if entities.get("property_id"):
            query = query.filter(AuditLog.property_id == entities["property_id"])

        if entities.get("user_id"):
            query = query.filter(AuditLog.user_id == entities["user_id"])

        if entities.get("statement_type"):
            query = query.filter(AuditLog.table_name == entities["statement_type"])

        # Execute query with limit
        audit_logs = query.order_by(desc(AuditLog.timestamp)).limit(100).all()

        # Convert to dict format
        results = []
        for log in audit_logs:
            results.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "user_name": log.user.username if log.user else "Unknown",
                "action": log.action,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "property_id": log.property_id,
                "ip_address": log.ip_address
            })

        return results

    async def _generate_answer(
        self,
        query: str,
        query_type: str,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Generate natural language answer from audit results"""

        if not results:
            # No audit records found
            temporal_desc = self._format_temporal_description(temporal_info)
            entity_desc = self._format_entity_description(entities)

            return (
                f"I didn't find any audit records {entity_desc}{temporal_desc}. "
                f"This could mean:\n\n"
                f"• No changes were made during this period\n"
                f"• The audit logging wasn't enabled at that time\n"
                f"• The data you're looking for is outside the audit retention period"
            )

        # Generate answer based on query type
        if query_type == "who_changed":
            return self._answer_who_changed(results, temporal_info, entities)

        elif query_type == "what_changed":
            return self._answer_what_changed(results, temporal_info, entities)

        elif query_type == "when_changed":
            return self._answer_when_changed(results, temporal_info, entities)

        elif query_type == "user_activity":
            return self._answer_user_activity(results, temporal_info, entities)

        elif query_type == "property_history":
            return self._answer_property_history(results, temporal_info, entities)

        elif query_type == "recent_changes":
            return self._answer_recent_changes(results, temporal_info, entities)

        else:
            # Generic answer
            return self._answer_generic(results, temporal_info, entities)

    def _answer_who_changed(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer 'who changed' queries"""

        # Group by user
        user_changes = {}
        for record in results:
            user_name = record["user_name"]
            if user_name not in user_changes:
                user_changes[user_name] = []
            user_changes[user_name].append(record)

        temporal_desc = self._format_temporal_description(temporal_info)
        entity_desc = self._format_entity_description(entities)

        answer = f"Here's who made changes {entity_desc}{temporal_desc}:\n\n"

        for user_name, changes in user_changes.items():
            answer += f"**{user_name}** ({len(changes)} changes):\n"

            # Show first 3 changes
            for change in changes[:3]:
                timestamp = datetime.fromisoformat(change["timestamp"]).strftime("%Y-%m-%d %H:%M")
                action = change["action"]
                table = change["table_name"]
                answer += f"  • {timestamp} - {action} {table}\n"

            if len(changes) > 3:
                answer += f"  ... and {len(changes) - 3} more changes\n"
            answer += "\n"

        answer += f"\n**Total:** {len(results)} changes by {len(user_changes)} users"

        return answer

    def _answer_what_changed(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer 'what changed' queries"""

        temporal_desc = self._format_temporal_description(temporal_info)

        answer = f"Here's what was changed {temporal_desc}:\n\n"

        # Show most recent changes
        for i, record in enumerate(results[:10], 1):
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            user = record["user_name"]
            action = record["action"]
            table = record["table_name"]

            answer += f"{i}. **{timestamp}** - {user} {action} {table}\n"

            # Show changed fields if available
            if record.get("old_values") and record.get("new_values"):
                old_vals = record["old_values"]
                new_vals = record["new_values"]

                changed_fields = set(old_vals.keys()) & set(new_vals.keys())
                if changed_fields:
                    answer += "   Changed fields: "
                    for field in list(changed_fields)[:3]:
                        answer += f"{field} ({old_vals[field]} → {new_vals[field]}), "
                    answer = answer.rstrip(", ") + "\n"
            answer += "\n"

        if len(results) > 10:
            answer += f"\n... and {len(results) - 10} more changes"

        return answer

    def _answer_when_changed(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer 'when changed' queries"""

        if results:
            first_change = results[-1]  # Oldest
            last_change = results[0]     # Most recent

            first_time = datetime.fromisoformat(first_change["timestamp"]).strftime("%Y-%m-%d %H:%M")
            last_time = datetime.fromisoformat(last_change["timestamp"]).strftime("%Y-%m-%d %H:%M")

            entity_desc = self._format_entity_description(entities)

            answer = f"Changes {entity_desc}:\n\n"
            answer += f"**First change:** {first_time} by {first_change['user_name']}\n"
            answer += f"**Most recent change:** {last_time} by {last_change['user_name']}\n"
            answer += f"**Total changes:** {len(results)}\n\n"

            # Show timeline summary
            answer += "**Recent Activity:**\n"
            for record in results[:5]:
                timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
                answer += f"  • {timestamp} - {record['user_name']} {record['action']} {record['table_name']}\n"

            return answer

        return "No change records found."

    def _answer_user_activity(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer user activity queries"""

        if not results:
            return "No activity found for this user."

        user_name = results[0]["user_name"]
        temporal_desc = self._format_temporal_description(temporal_info)

        answer = f"**Activity for {user_name}** {temporal_desc}:\n\n"
        answer += f"**Total actions:** {len(results)}\n\n"

        # Group by action type
        action_counts = {}
        for record in results:
            action = record["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        answer += "**Actions:**\n"
        for action, count in action_counts.items():
            answer += f"  • {action}: {count}\n"

        answer += "\n**Recent Activity:**\n"
        for record in results[:10]:
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            answer += f"  • {timestamp} - {record['action']} {record['table_name']}\n"

        return answer

    def _answer_property_history(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer property history queries"""

        property_desc = entities.get("property_code", "this property")
        temporal_desc = self._format_temporal_description(temporal_info)

        answer = f"**Audit History for {property_desc}** {temporal_desc}:\n\n"
        answer += f"**Total changes:** {len(results)}\n\n"

        # Group by statement type
        by_table = {}
        for record in results:
            table = record["table_name"]
            by_table.setdefault(table, []).append(record)

        answer += "**Changes by Statement Type:**\n"
        for table, records in by_table.items():
            answer += f"  • {table}: {len(records)} changes\n"

        answer += "\n**Recent Changes:**\n"
        for record in results[:10]:
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            answer += f"  • {timestamp} - {record['user_name']} {record['action']} {record['table_name']}\n"

        return answer

    def _answer_recent_changes(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Answer recent changes queries"""

        answer = "**Recent System Activity:**\n\n"
        answer += f"**Total recent changes:** {len(results)}\n\n"

        for i, record in enumerate(results[:15], 1):
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            answer += (
                f"{i}. **{timestamp}** - {record['user_name']} "
                f"{record['action']} {record['table_name']}\n"
            )

        if len(results) > 15:
            answer += f"\n... and {len(results) - 15} more changes"

        return answer

    def _answer_generic(
        self,
        results: List[Dict],
        temporal_info: Dict,
        entities: Dict
    ) -> str:
        """Generic answer for audit queries"""

        temporal_desc = self._format_temporal_description(temporal_info)
        entity_desc = self._format_entity_description(entities)

        answer = f"**Audit Results** {entity_desc}{temporal_desc}:\n\n"
        answer += f"**Total records:** {len(results)}\n\n"

        for i, record in enumerate(results[:10], 1):
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M")
            answer += (
                f"{i}. **{timestamp}** - {record['user_name']} "
                f"{record['action']} {record['table_name']}\n"
            )

        if len(results) > 10:
            answer += f"\n... and {len(results) - 10} more records"

        return answer

    def _format_temporal_description(self, temporal_info: Dict) -> str:
        """Format temporal info for answers"""
        if not temporal_info.get("has_temporal"):
            return ""

        normalized = temporal_info.get("normalized_expression", "")
        if normalized:
            return f"in {normalized}"

        return ""

    def _format_entity_description(self, entities: Dict) -> str:
        """Format entity info for answers"""
        parts = []

        if entities.get("property_code"):
            parts.append(f"for property {entities['property_code']}")

        if entities.get("account_code"):
            parts.append(f"for account {entities['account_code']}")

        if entities.get("statement_type"):
            parts.append(f"in {entities['statement_type']}")

        if parts:
            return " ".join(parts) + " "

        return ""
