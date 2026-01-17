import logging
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.local_llm_service import get_local_llm_service, LLMTaskType

logger = logging.getLogger(__name__)

class LLMExtractionService:
    """
    Service for extracting structured financial data using Local LLMs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.llm_service = get_local_llm_service()

    async def classify_document(self, text_content: str, max_length: int = 2000) -> Dict[str, Any]:
        """
        Classify document type using LLM semantic understanding.
        """
        if len(text_content) > max_length:
            context_text = text_content[:max_length]
        else:
            context_text = text_content
            
        system_prompt = """
        You are an expert document classifier for real estate financial documents.
        Classify the text into one of the following types:
        - balance_sheet
        - income_statement
        - rent_roll
        - cash_flow
        - invoice
        - unknown
        
        Return JSON matching this schema:
        {
            "document_type": "string",
            "confidence": float (0.0 to 1.0),
            "reasoning": "string explanation"
        }
        """
        
        try:
            result = await self.llm_service.generate_json(
                prompt=f"Classify this document:\n{context_text}",
                system_prompt=system_prompt,
                task_type=LLMTaskType.ANALYSIS
            )
            return result
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {"document_type": "unknown", "confidence": 0.0, "reasoning": str(e)}

    async def extract_financial_data(
        self, 
        text_content: str, 
        document_type: str,
        max_length: int = 4000
    ) -> Dict[str, Any]:
        """
        Extract structured data from text using LLM.
        
        Args:
            text_content: The raw text from the document
            document_type: The type of document (balance_sheet, income_statement, etc.)
            max_length: Context window limit for the prompt
            
        Returns:
            Dict containing extraction results and metadata
        """
        # Truncate text if too long (keep beginning and end as they usually contain key info)
        if len(text_content) > max_length:
            half = max_length // 2
            context_text = text_content[:half] + "\n...[snipped]...\n" + text_content[-half:]
        else:
            context_text = text_content

        # Select appropriate schema and prompt based on doc type
        if document_type == "balance_sheet":
            schema = self._get_balance_sheet_schema()
            system_prompt = self._get_balance_sheet_prompt()
        elif document_type == "income_statement" or document_type == "profit_loss":
             schema = self._get_income_statement_schema()
             system_prompt = self._get_income_statement_prompt()
        elif document_type == "rent_roll":
             schema = self._get_rent_roll_schema()
             system_prompt = self._get_rent_roll_prompt()
        else:
            # Generic fallback
            schema = self._get_generic_schema()
            system_prompt = "Extract all financial figures and dates from this document as key-value pairs."

        try:
            logger.info(f"Attempting LLM extraction for {document_type}...")
            
            # Retrieve Few-Shot Examples (Active Learning)
            try:
                from app.services.feedback_loop_service import FeedbackLoopService
                feedback_service = FeedbackLoopService()
                examples = feedback_service.get_few_shot_examples(document_type)
                
                if examples:
                    examples_text = "\n\nHere are some examples of valid extractions:\n"
                    for ex in examples:
                        examples_text += f"---\nInput: {ex.get('text_snippet', '')[:200]}...\nOutput: {json.dumps(ex.get('expected_json'))}\n"
                    
                    # Append examples to system prompt
                    system_prompt += examples_text
                    logger.info(f"Injected {len(examples)} active learning examples into prompt.")
            except Exception as e:
                logger.warning(f"Failed to inject feedback examples: {e}")

            # Use generate_json for structured output
            result = await self.llm_service.generate_json(
                prompt=f"Document Text:\n{context_text}",
                system_prompt=system_prompt,
                task_type=LLMTaskType.ANALYSIS,
                schema=schema
            )
            
            return {
                "success": True,
                "data": result,
                "method": "llm_fallback",
                "extracted_by": self.llm_service.config.model
            }
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "method": "llm_fallback_failed"
            }

    def _get_balance_sheet_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "statement_date": {"type": "string", "description": "Date of the statement (MM/DD/YYYY)"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "category": {"type": "string", "enum": ["Asset", "Liability", "Equity"]}
                        },
                        "required": ["account_name", "amount"]
                    }
                },
                "total_assets": {"type": "number"},
                "total_liabilities": {"type": "number"},
                "total_equity": {"type": "number"}
            },
            "required": ["line_items"]
        }

    def _get_balance_sheet_prompt(self) -> str:
        return """
        You are an expert financial analyst. Extract the Balance Sheet data from the provided text.
        
        Rules:
        1. Identify the statement date.
        2. Extract line items as 'account_name' and 'amount'.
        3. Classify each item as Asset, Liability, or Equity.
        4. Normalize amounts to numbers (remove currency symbols, handle parentheses as negative).
        5. Return ONLY the JSON object.
        """

    def _get_income_statement_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "section": {"type": "string", "enum": ["Revenue", "Expense", "NOI", "Other"]}
                        },
                        "required": ["account_name", "amount"]
                    }
                },
                "total_revenue": {"type": "number"},
                "total_expenses": {"type": "number"},
                "net_operating_income": {"type": "number"}
            },
            "required": ["line_items"]
        }

    def _get_income_statement_prompt(self) -> str:
        return """
        You are an expert financial analyst. Extract Income Statement (P&L) data.
        
        Rules:
        1. Identify the period (start/end dates or 'For the month ended...').
        2. Extract line items (Revenue, Expenses).
        3. Identify Net Operating Income (NOI).
        4. Return ONLY valid JSON.
        """

    def _get_rent_roll_schema(self) -> Dict:
         return {
            "type": "object",
            "properties": {
                "as_of_date": {"type": "string"},
                "property_name": {"type": "string"},
                "units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "unit_id": {"type": "string"},
                            "tenant_name": {"type": "string"},
                            "lease_start": {"type": "string"},
                            "lease_end": {"type": "string"},
                            "monthly_rent": {"type": "number"},
                            "sf": {"type": "number"}
                        },
                        "required": ["unit_id", "monthly_rent"]
                    }
                }
            },
            "required": ["units"]
        }
        
    def _get_rent_roll_prompt(self) -> str:
        return """
        You are an expert real estate analyst. Extract Rent Roll data.
        
        Rules:
        1. Extract unit-level details (Unit ID, Tenant, Rent, SQFT, Lease Dates).
        2. Ignore totals or summary rows in the content.
        3. Normalize numeric values.
        4. Return ONLY valid JSON.
        """

    def _get_generic_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "key_values": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"}
                        }
                    }
                }
            }
        }
