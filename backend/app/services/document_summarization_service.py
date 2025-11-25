"""
Document Summarization Service

AI-powered document summarization for leases, OMs, and other property documents
Implements M1/M2/M3 multi-agent pattern (Retriever, Writer, Auditor)
"""
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
import time
import json
import logging
import re

from sqlalchemy.orm import Session
from sqlalchemy import desc
import hashlib
import redis

from app.models.document_summary import DocumentSummary, DocumentType, SummaryStatus
from app.models.property import Property
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentSummarizationService:
    """
    Document Summarization Service

    Uses LLM (GPT-4 or Claude) to generate intelligent summaries of documents
    Implements multi-agent pattern: M1 (Retriever) → M2 (Writer) → M3 (Auditor)
    """

    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = settings.LLM_PROVIDER
        self.llm_model = settings.LLM_MODEL
        
        # BR-011: Initialize Redis cache for performance optimization
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
            self.cache_enabled = True
            self.cache_ttl = 7 * 24 * 60 * 60  # 7 days TTL
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}. Summarization will work without caching.")
            self.redis_client = None
            self.cache_enabled = False

        # Initialize LLM client
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize LLM client based on provider"""
        try:
            if self.llm_provider == "openai":
                import openai
                openai.api_key = settings.OPENAI_API_KEY
                self.client = openai
            elif self.llm_provider == "anthropic":
                import anthropic
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            else:
                logger.warning(f"Unknown LLM provider: {self.llm_provider}")
                self.client = None
        except ImportError as e:
            logger.error(f"Failed to import LLM client: {e}")
            self.client = None

    def summarize_lease(
        self,
        property_id: int,
        document_path: str,
        document_name: str,
        document_text: str,
        created_by: Optional[int] = None
    ) -> Dict:
        """
        Summarize a lease document

        Extracts key lease information:
        - Parties (landlord, tenant)
        - Term (start date, end date, options)
        - Rent (base rent, escalations, CAM)
        - Special provisions
        - Key dates

        Returns:
            - success: bool
            - summary_id: int
            - executive_summary: str
            - lease_data: dict with structured lease info
        """
        start_time = time.time()

        try:
            # Verify property exists
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Create summary record
            summary = DocumentSummary(
                property_id=property_id,
                document_type=DocumentType.LEASE,
                document_name=document_name,
                document_path=document_path,
                summary_type="lease",
                status=SummaryStatus.PROCESSING,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model,
                created_by=created_by,
            )
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)

            # M1: Retriever - Extract raw information from document
            retriever_result = self._m1_retrieve_lease_info(document_text)

            # M2: Writer - Generate structured summary from raw info
            writer_result = self._m2_write_lease_summary(retriever_result)

            # M3: Auditor - Verify summary against original document
            auditor_result = self._m3_audit_lease_summary(document_text, writer_result)

            # Update summary with results
            summary.executive_summary = writer_result.get("executive_summary")
            summary.detailed_summary = writer_result.get("detailed_summary")
            summary.key_points = writer_result.get("key_points")
            summary.lease_data = writer_result.get("lease_data")
            summary.extracted_data = retriever_result
            summary.confidence_score = auditor_result.get("confidence_score", 85)
            summary.has_hallucination_flag = auditor_result.get("has_issues", False)
            summary.hallucination_details = auditor_result.get("issues", [])
            summary.status = SummaryStatus.COMPLETED
            summary.processed_at = datetime.utcnow()
            summary.processing_time_seconds = int(time.time() - start_time)

            self.db.commit()
            self.db.refresh(summary)

            result = {
                "success": True,
                "summary_id": summary.id,
                "executive_summary": summary.executive_summary,
                "detailed_summary": summary.detailed_summary,
                "key_points": summary.key_points,
                "lease_data": summary.lease_data,
                "confidence_score": summary.confidence_score,
                "has_quality_issues": summary.has_quality_issues(),
                "processing_time_seconds": summary.processing_time_seconds,
                "from_cache": False
            }
            
            # BR-011: Cache the result for future requests
            self._cache_summary(cache_key, result)
            
            return result

        except Exception as e:
            logger.error(f"Lease summarization failed: {str(e)}")
            if 'summary' in locals():
                summary.status = SummaryStatus.FAILED
                summary.error_message = str(e)
                self.db.commit()
            return {"success": False, "error": str(e)}

    def summarize_om(
        self,
        property_id: int,
        document_path: str,
        document_name: str,
        document_text: str,
        created_by: Optional[int] = None
    ) -> Dict:
        """
        Summarize an Offering Memorandum (OM) (BR-011: Optimized with caching)

        Extracts key information:
        - Property overview
        - Financial highlights
        - Market analysis
        - Tenant mix
        - Investment highlights
        - Risk factors

        Returns:
            - success: bool
            - summary_id: int
            - executive_summary: str
            - om_data: dict with structured OM info
        """
        start_time = time.time()
        
        # BR-011: Check cache first
        cache_key = self._get_cache_key(document_text, "om")
        cached_result = self._get_cached_summary(cache_key)
        if cached_result:
            cached_result["property_id"] = property_id
            cached_result["from_cache"] = True
            cached_result["processing_time_seconds"] = int((time.time() - start_time) * 1000)  # milliseconds
            return cached_result

        try:
            # Verify property exists
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # Create summary record
            summary = DocumentSummary(
                property_id=property_id,
                document_type=DocumentType.OFFERING_MEMORANDUM,
                document_name=document_name,
                document_path=document_path,
                summary_type="offering_memorandum",
                status=SummaryStatus.PROCESSING,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model,
                created_by=created_by,
            )
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)

            # M1: Retriever - Extract raw information
            retriever_result = self._m1_retrieve_om_info(document_text)

            # M2: Writer - Generate structured summary
            writer_result = self._m2_write_om_summary(retriever_result)

            # M3: Auditor - Verify summary
            auditor_result = self._m3_audit_om_summary(document_text, writer_result)

            # Update summary
            summary.executive_summary = writer_result.get("executive_summary")
            summary.detailed_summary = writer_result.get("detailed_summary")
            summary.key_points = writer_result.get("key_points")
            summary.om_data = writer_result.get("om_data")
            summary.extracted_data = retriever_result
            summary.confidence_score = auditor_result.get("confidence_score", 85)
            summary.has_hallucination_flag = auditor_result.get("has_issues", False)
            summary.hallucination_details = auditor_result.get("issues", [])
            summary.status = SummaryStatus.COMPLETED
            summary.processed_at = datetime.utcnow()
            summary.processing_time_seconds = int(time.time() - start_time)

            self.db.commit()
            self.db.refresh(summary)

            result = {
                "success": True,
                "summary_id": summary.id,
                "executive_summary": summary.executive_summary,
                "detailed_summary": summary.detailed_summary,
                "key_points": summary.key_points,
                "om_data": summary.om_data,
                "confidence_score": summary.confidence_score,
                "has_quality_issues": summary.has_quality_issues(),
                "processing_time_seconds": summary.processing_time_seconds,
                "from_cache": False
            }
            
            # BR-011: Cache the result for future requests
            self._cache_summary(cache_key, result)
            
            return result

        except Exception as e:
            logger.error(f"OM summarization failed: {str(e)}")
            if 'summary' in locals():
                summary.status = SummaryStatus.FAILED
                summary.error_message = str(e)
                self.db.commit()
            return {"success": False, "error": str(e)}

    def _m1_retrieve_lease_info(self, document_text: str) -> Dict:
        """
        M1 Retriever: Extract raw information from lease document

        Uses LLM to extract structured data from the lease text
        """
        prompt = f"""
You are an expert commercial real estate analyst. Extract key information from this lease document.

LEASE DOCUMENT:
{document_text[:8000]}

Extract and return the following information in JSON format:
{{
    "landlord": "Name of landlord",
    "tenant": "Name of tenant",
    "premises_address": "Property address",
    "premises_square_footage": "Size in square feet",
    "lease_start_date": "YYYY-MM-DD",
    "lease_end_date": "YYYY-MM-DD",
    "lease_term_months": "Number of months",
    "base_rent_per_month": "Monthly rent amount",
    "base_rent_per_sf": "Rent per square foot",
    "rent_escalations": ["List of rent escalation clauses"],
    "security_deposit": "Amount",
    "renewal_options": ["List of renewal options"],
    "termination_provisions": ["Early termination clauses"],
    "use_restrictions": ["Permitted uses"],
    "maintenance_obligations": ["Who is responsible for what"],
    "insurance_requirements": ["Required insurance coverage"],
    "special_provisions": ["Any unusual or important clauses"],
    "key_dates": ["Important dates to track"]
}}

Return ONLY valid JSON. If information is not found, use null.
"""

        try:
            if not self.client:
                # Fallback: basic extraction without LLM
                return self._fallback_lease_extraction(document_text)

            if self.llm_provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert commercial real estate analyst specializing in lease analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                result_text = response.choices[0].message.content
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=self.llm_model,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text

            # Parse JSON from response
            result = self._extract_json_from_text(result_text)
            return result

        except Exception as e:
            logger.error(f"M1 retriever failed: {e}")
            return self._fallback_lease_extraction(document_text)

    def _m2_write_lease_summary(self, retriever_data: Dict) -> Dict:
        """
        M2 Writer: Generate executive summary from extracted data

        Creates human-readable summaries from structured data
        """
        prompt = f"""
Based on the extracted lease data below, write a comprehensive lease summary.

EXTRACTED DATA:
{json.dumps(retriever_data, indent=2)}

Provide:
1. Executive Summary (2-3 sentences highlighting the most important terms)
2. Detailed Summary (comprehensive overview of all key lease terms)
3. Key Points (bullet points of the 5-7 most critical items)

Return as JSON:
{{
    "executive_summary": "2-3 sentence overview",
    "detailed_summary": "Comprehensive paragraph summary",
    "key_points": ["Point 1", "Point 2", ...],
    "lease_data": {{
        "tenant_name": "...",
        "lease_term": "...",
        "monthly_rent": "...",
        "key_provisions": ["..."]
    }}
}}

Return ONLY valid JSON.
"""

        try:
            if not self.client:
                return self._fallback_lease_summary(retriever_data)

            if self.llm_provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert commercial real estate analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                result_text = response.choices[0].message.content
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=self.llm_model,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text

            result = self._extract_json_from_text(result_text)
            return result

        except Exception as e:
            logger.error(f"M2 writer failed: {e}")
            return self._fallback_lease_summary(retriever_data)

    def _m3_audit_lease_summary(self, original_text: str, summary: Dict) -> Dict:
        """
        M3 Auditor: Verify summary against original document

        Checks for hallucinations and missing information
        """
        prompt = f"""
You are a fact-checking auditor. Verify the lease summary against the original document.

ORIGINAL DOCUMENT (excerpt):
{original_text[:4000]}

GENERATED SUMMARY:
{json.dumps(summary, indent=2)}

Check for:
1. Hallucinations (information in summary not in original)
2. Missing critical information
3. Factual errors or misrepresentations

Return as JSON:
{{
    "confidence_score": 85,
    "has_issues": false,
    "issues": [
        {{"type": "hallucination", "description": "...", "severity": "high"}},
        {{"type": "missing_info", "description": "...", "severity": "medium"}}
    ],
    "verified_facts": ["List of facts verified against original"],
    "recommendations": ["Suggestions for improvement"]
}}

Return ONLY valid JSON.
"""

        try:
            if not self.client:
                return {"confidence_score": 70, "has_issues": False, "issues": []}

            if self.llm_provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are a meticulous fact-checking auditor."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,  # Lower temperature for auditing
                    max_tokens=2000,
                )
                result_text = response.choices[0].message.content
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=self.llm_model,
                    max_tokens=2000,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text

            result = self._extract_json_from_text(result_text)
            return result

        except Exception as e:
            logger.error(f"M3 auditor failed: {e}")
            return {"confidence_score": 70, "has_issues": False, "issues": []}

    def _m1_retrieve_om_info(self, document_text: str) -> Dict:
        """M1 Retriever for Offering Memorandum"""
        prompt = f"""
Extract key information from this Offering Memorandum.

DOCUMENT:
{document_text[:8000]}

Extract and return in JSON:
{{
    "property_name": "...",
    "property_address": "...",
    "property_type": "...",
    "total_square_footage": "...",
    "year_built": "...",
    "asking_price": "...",
    "cap_rate": "...",
    "noi": "Net Operating Income",
    "occupancy_rate": "...",
    "number_of_tenants": "...",
    "major_tenants": ["List of major tenants"],
    "market_overview": "Brief market description",
    "investment_highlights": ["Key selling points"],
    "financial_summary": {{
        "gross_revenue": "...",
        "operating_expenses": "...",
        "noi": "..."
    }},
    "risk_factors": ["Potential risks"]
}}

Return ONLY valid JSON.
"""

        try:
            if not self.client:
                return self._fallback_om_extraction(document_text)

            if self.llm_provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert real estate investment analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                result_text = response.choices[0].message.content
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=self.llm_model,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text

            result = self._extract_json_from_text(result_text)
            return result

        except Exception as e:
            logger.error(f"M1 retriever for OM failed: {e}")
            return self._fallback_om_extraction(document_text)

    def _m2_write_om_summary(self, retriever_data: Dict) -> Dict:
        """M2 Writer for Offering Memorandum"""
        prompt = f"""
Write an investment summary based on this extracted OM data.

EXTRACTED DATA:
{json.dumps(retriever_data, indent=2)}

Provide:
{{
    "executive_summary": "2-3 sentence investment overview",
    "detailed_summary": "Comprehensive analysis",
    "key_points": ["Top 5-7 investment highlights"],
    "om_data": {{
        "property_overview": "...",
        "financial_performance": "...",
        "market_position": "...",
        "investment_thesis": "..."
    }}
}}

Return ONLY valid JSON.
"""

        try:
            if not self.client:
                return self._fallback_om_summary(retriever_data)

            if self.llm_provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert real estate investment analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                result_text = response.choices[0].message.content
            elif self.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=self.llm_model,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text

            result = self._extract_json_from_text(result_text)
            return result

        except Exception as e:
            logger.error(f"M2 writer for OM failed: {e}")
            return self._fallback_om_summary(retriever_data)

    def _m3_audit_om_summary(self, original_text: str, summary: Dict) -> Dict:
        """M3 Auditor for Offering Memorandum"""
        # Similar to lease auditor
        return self._m3_audit_lease_summary(original_text, summary)

    def _extract_json_from_text(self, text: str) -> Dict:
        """Extract JSON from LLM response text"""
        try:
            # Try direct JSON parse first
            return json.loads(text)
        except:
            # Extract JSON from markdown code blocks or other text
            json_pattern = r'\{.*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except:
                    pass
            return {}

    def _fallback_lease_extraction(self, text: str) -> Dict:
        """Fallback extraction without LLM"""
        return {
            "landlord": "N/A",
            "tenant": "N/A",
            "extraction_method": "fallback_regex",
            "note": "LLM unavailable, basic extraction performed"
        }

    def _fallback_lease_summary(self, data: Dict) -> Dict:
        """Fallback summary without LLM"""
        return {
            "executive_summary": "Lease document processed. LLM unavailable for detailed analysis.",
            "detailed_summary": f"Extracted data: {json.dumps(data)}",
            "key_points": ["LLM unavailable", "Basic extraction performed"],
            "lease_data": data
        }

    def _fallback_om_extraction(self, text: str) -> Dict:
        """Fallback OM extraction"""
        return {
            "property_name": "N/A",
            "extraction_method": "fallback",
            "note": "LLM unavailable"
        }

    def _fallback_om_summary(self, data: Dict) -> Dict:
        """Fallback OM summary"""
        return {
            "executive_summary": "OM document processed. LLM unavailable for detailed analysis.",
            "detailed_summary": f"Extracted data: {json.dumps(data)}",
            "key_points": ["LLM unavailable"],
            "om_data": data
        }

    def get_summary(self, summary_id: int) -> Dict:
        """Get document summary by ID"""
        summary = self.db.query(DocumentSummary).filter(DocumentSummary.id == summary_id).first()
        if not summary:
            return {"success": False, "error": "Summary not found"}

        return {
            "success": True,
            "summary": summary.to_dict()
        }

    def get_property_summaries(self, property_id: int, document_type: Optional[str] = None) -> Dict:
        """Get all summaries for a property"""
        query = self.db.query(DocumentSummary).filter(DocumentSummary.property_id == property_id)

        if document_type:
            try:
                doc_type_enum = DocumentType[document_type.upper()]
                query = query.filter(DocumentSummary.document_type == doc_type_enum)
            except KeyError:
                return {"success": False, "error": f"Invalid document type: {document_type}"}

        summaries = query.order_by(desc(DocumentSummary.created_at)).all()

        return {
            "success": True,
            "summaries": [summary.to_dict() for summary in summaries],
            "total": len(summaries)
        }
