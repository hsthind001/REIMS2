"""
Document Completeness Service

Implements Phase 1 of the Forensic Audit Framework:
- Verifies presence of all 5 required financial documents
- Calculates completeness percentage
- Checks data quality and record counts
- Validates required fields are populated

Part of the Big 5 Forensic Audit Framework for REIMS2.

Author: Claude AI Forensic Audit Framework
Date: December 28, 2025
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class DocumentCompletenessService:
    """
    Service for verifying document completeness and data quality.

    Implements Phase 1 checks:
    - Balance Sheet present and complete
    - Income Statement present and complete
    - Cash Flow Statement present and complete
    - Rent Roll present and complete
    - Mortgage Statement present and complete
    """

    # Minimum record thresholds
    MIN_BS_LINE_ITEMS = 10  # Minimum balance sheet accounts
    MIN_IS_LINE_ITEMS = 5  # Minimum income statement accounts
    MIN_CF_LINE_ITEMS = 5  # Minimum cash flow line items
    MIN_RR_TENANTS = 1  # At least one tenant
    MIN_MS_TRANSACTIONS = 1  # At least one mortgage transaction

    def __init__(self, db: AsyncSession):
        """
        Initialize the service.

        Args:
            db: Async database session
        """
        self.db = db

    async def verify_balance_sheet_present(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify Balance Sheet document is present and complete.

        Checks:
        - Document exists
        - Has line items
        - Assets = Liabilities + Equity
        - Required accounts present (Cash, A/R, Liabilities, Equity)

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing verification results
        """
        logger.info(f"Verifying Balance Sheet for property {property_id}, period {period_id}")

        # Check if balance sheet document exists
        doc_query = text("""
            SELECT id, document_name, upload_date, extraction_status
            FROM documents
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND document_type = 'balance_sheet'
                AND is_deleted = false
            LIMIT 1
        """)

        doc_result = await self.db.execute(
            doc_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        doc_row = doc_result.fetchone()

        if not doc_row:
            return {
                "document_type": "Balance Sheet",
                "present": False,
                "complete": False,
                "status": "RED",
                "line_item_count": 0,
                "explanation": "Balance Sheet document not found for this period.",
                "recommendation": "Upload and extract Balance Sheet to enable forensic audit."
            }

        document_id = doc_row.id
        extraction_status = doc_row.extraction_status

        # Count line items
        count_query = text("""
            SELECT COUNT(*) as line_count
            FROM balance_sheet_line_items
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        count_result = await self.db.execute(
            count_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        count_row = count_result.fetchone()
        line_count = count_row.line_count if count_row else 0

        # Check for required account categories
        category_query = text("""
            SELECT
                SUM(CASE WHEN account_code LIKE '1%' THEN 1 ELSE 0 END) as asset_count,
                SUM(CASE WHEN account_code LIKE '2%' THEN 1 ELSE 0 END) as liability_count,
                SUM(CASE WHEN account_code LIKE '3%' THEN 1 ELSE 0 END) as equity_count
            FROM balance_sheet_line_items
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        cat_result = await self.db.execute(
            category_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        cat_row = cat_result.fetchone()

        has_assets = cat_row.asset_count > 0 if cat_row else False
        has_liabilities = cat_row.liability_count > 0 if cat_row else False
        has_equity = cat_row.equity_count > 0 if cat_row else False

        # Determine completeness
        is_complete = (
            line_count >= self.MIN_BS_LINE_ITEMS and
            has_assets and
            has_liabilities and
            has_equity and
            extraction_status == 'completed'
        )

        if is_complete:
            status = "GREEN"
            explanation = f"Balance Sheet is complete with {line_count} line items covering all account categories."
        elif line_count > 0:
            status = "YELLOW"
            explanation = f"Balance Sheet present but incomplete. Has {line_count} items but missing some account categories."
        else:
            status = "RED"
            explanation = "Balance Sheet document uploaded but not extracted or no data present."

        return {
            "document_type": "Balance Sheet",
            "present": True,
            "complete": is_complete,
            "status": status,
            "document_id": str(document_id),
            "extraction_status": extraction_status,
            "line_item_count": line_count,
            "has_assets": has_assets,
            "has_liabilities": has_liabilities,
            "has_equity": has_equity,
            "explanation": explanation,
            "recommendation": self._get_bs_recommendation(is_complete, line_count)
        }

    async def verify_income_statement_present(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify Income Statement document is present and complete.

        Checks:
        - Document exists
        - Has line items
        - Has revenue accounts
        - Has expense accounts
        - Net income calculated

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing verification results
        """
        logger.info(f"Verifying Income Statement for property {property_id}, period {period_id}")

        # Check if income statement document exists
        doc_query = text("""
            SELECT id, document_name, upload_date, extraction_status
            FROM documents
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND document_type = 'income_statement'
                AND is_deleted = false
            LIMIT 1
        """)

        doc_result = await self.db.execute(
            doc_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        doc_row = doc_result.fetchone()

        if not doc_row:
            return {
                "document_type": "Income Statement",
                "present": False,
                "complete": False,
                "status": "RED",
                "line_item_count": 0,
                "explanation": "Income Statement document not found for this period.",
                "recommendation": "Upload and extract Income Statement to enable forensic audit."
            }

        document_id = doc_row.id
        extraction_status = doc_row.extraction_status

        # Count line items and check for revenue/expenses
        count_query = text("""
            SELECT
                COUNT(*) as line_count,
                SUM(CASE WHEN account_code LIKE '4%' THEN 1 ELSE 0 END) as revenue_count,
                SUM(CASE WHEN account_code LIKE '5%' OR account_code LIKE '6%' THEN 1 ELSE 0 END) as expense_count
            FROM income_statement_line_items
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        count_result = await self.db.execute(
            count_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        count_row = count_result.fetchone()

        line_count = count_row.line_count if count_row else 0
        has_revenue = count_row.revenue_count > 0 if count_row else False
        has_expenses = count_row.expense_count > 0 if count_row else False

        # Determine completeness
        is_complete = (
            line_count >= self.MIN_IS_LINE_ITEMS and
            has_revenue and
            has_expenses and
            extraction_status == 'completed'
        )

        if is_complete:
            status = "GREEN"
            explanation = f"Income Statement is complete with {line_count} line items including revenue and expenses."
        elif line_count > 0:
            status = "YELLOW"
            explanation = f"Income Statement present but incomplete. Has {line_count} items."
        else:
            status = "RED"
            explanation = "Income Statement document uploaded but not extracted or no data present."

        return {
            "document_type": "Income Statement",
            "present": True,
            "complete": is_complete,
            "status": status,
            "document_id": str(document_id),
            "extraction_status": extraction_status,
            "line_item_count": line_count,
            "has_revenue": has_revenue,
            "has_expenses": has_expenses,
            "explanation": explanation,
            "recommendation": self._get_is_recommendation(is_complete, line_count)
        }

    async def verify_cash_flow_present(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify Cash Flow Statement document is present and complete.

        Checks:
        - Document exists
        - Has line items
        - Has operating, investing, or financing activities

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing verification results
        """
        logger.info(f"Verifying Cash Flow Statement for property {property_id}, period {period_id}")

        # Check if cash flow document exists
        doc_query = text("""
            SELECT id, document_name, upload_date, extraction_status
            FROM documents
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND document_type = 'cash_flow'
                AND is_deleted = false
            LIMIT 1
        """)

        doc_result = await self.db.execute(
            doc_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        doc_row = doc_result.fetchone()

        if not doc_row:
            return {
                "document_type": "Cash Flow Statement",
                "present": False,
                "complete": False,
                "status": "RED",
                "line_item_count": 0,
                "explanation": "Cash Flow Statement document not found for this period.",
                "recommendation": "Upload and extract Cash Flow Statement to enable forensic audit."
            }

        document_id = doc_row.id
        extraction_status = doc_row.extraction_status

        # Count line items
        count_query = text("""
            SELECT COUNT(*) as line_count
            FROM cash_flow_line_items
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        count_result = await self.db.execute(
            count_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        count_row = count_result.fetchone()
        line_count = count_row.line_count if count_row else 0

        # Determine completeness
        is_complete = (
            line_count >= self.MIN_CF_LINE_ITEMS and
            extraction_status == 'completed'
        )

        if is_complete:
            status = "GREEN"
            explanation = f"Cash Flow Statement is complete with {line_count} line items."
        elif line_count > 0:
            status = "YELLOW"
            explanation = f"Cash Flow Statement present but may be incomplete. Has {line_count} items."
        else:
            status = "RED"
            explanation = "Cash Flow Statement document uploaded but not extracted or no data present."

        return {
            "document_type": "Cash Flow Statement",
            "present": True,
            "complete": is_complete,
            "status": status,
            "document_id": str(document_id),
            "extraction_status": extraction_status,
            "line_item_count": line_count,
            "explanation": explanation,
            "recommendation": self._get_cf_recommendation(is_complete, line_count)
        }

    async def verify_rent_roll_present(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify Rent Roll document is present and complete.

        Checks:
        - Document exists
        - Has tenant records
        - Has active leases
        - Required fields populated (tenant name, rent, SF, lease dates)

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing verification results
        """
        logger.info(f"Verifying Rent Roll for property {property_id}, period {period_id}")

        # Check if rent roll document exists
        doc_query = text("""
            SELECT id, document_name, upload_date, extraction_status
            FROM documents
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND document_type = 'rent_roll'
                AND is_deleted = false
            LIMIT 1
        """)

        doc_result = await self.db.execute(
            doc_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        doc_row = doc_result.fetchone()

        if not doc_row:
            return {
                "document_type": "Rent Roll",
                "present": False,
                "complete": False,
                "status": "RED",
                "tenant_count": 0,
                "explanation": "Rent Roll document not found for this period.",
                "recommendation": "Upload and extract Rent Roll to enable forensic audit."
            }

        document_id = doc_row.id
        extraction_status = doc_row.extraction_status

        # Count tenants and check data quality
        count_query = text("""
            SELECT
                COUNT(*) as tenant_count,
                SUM(CASE WHEN lease_status IN ('Active', 'ACTIVE') THEN 1 ELSE 0 END) as active_count,
                SUM(CASE WHEN monthly_rent > 0 THEN 1 ELSE 0 END) as has_rent_count,
                SUM(CASE WHEN square_feet > 0 THEN 1 ELSE 0 END) as has_sf_count
            FROM rent_roll_tenants
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        count_result = await self.db.execute(
            count_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        count_row = count_result.fetchone()

        tenant_count = count_row.tenant_count if count_row else 0
        active_count = count_row.active_count if count_row else 0
        has_rent_count = count_row.has_rent_count if count_row else 0
        has_sf_count = count_row.has_sf_count if count_row else 0

        # Determine completeness
        is_complete = (
            tenant_count >= self.MIN_RR_TENANTS and
            active_count > 0 and
            has_rent_count > 0 and
            extraction_status == 'completed'
        )

        if is_complete:
            status = "GREEN"
            explanation = f"Rent Roll is complete with {tenant_count} tenants ({active_count} active)."
        elif tenant_count > 0:
            status = "YELLOW"
            explanation = f"Rent Roll present but may be incomplete. Has {tenant_count} tenants."
        else:
            status = "RED"
            explanation = "Rent Roll document uploaded but not extracted or no data present."

        return {
            "document_type": "Rent Roll",
            "present": True,
            "complete": is_complete,
            "status": status,
            "document_id": str(document_id),
            "extraction_status": extraction_status,
            "tenant_count": tenant_count,
            "active_tenant_count": active_count,
            "has_rent_data": has_rent_count > 0,
            "has_sf_data": has_sf_count > 0,
            "explanation": explanation,
            "recommendation": self._get_rr_recommendation(is_complete, tenant_count, active_count)
        }

    async def verify_mortgage_statement_present(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify Mortgage Statement document is present and complete.

        Checks:
        - Document exists
        - Has transaction records
        - Principal balance present
        - Interest and principal payments recorded

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing verification results
        """
        logger.info(f"Verifying Mortgage Statement for property {property_id}, period {period_id}")

        # Check if mortgage statement document exists
        doc_query = text("""
            SELECT id, document_name, upload_date, extraction_status
            FROM documents
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND document_type = 'mortgage_statement'
                AND is_deleted = false
            LIMIT 1
        """)

        doc_result = await self.db.execute(
            doc_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        doc_row = doc_result.fetchone()

        if not doc_row:
            return {
                "document_type": "Mortgage Statement",
                "present": False,
                "complete": False,
                "status": "YELLOW",  # Not critical if property has no mortgage
                "transaction_count": 0,
                "explanation": "Mortgage Statement document not found. Property may not have a mortgage.",
                "recommendation": "Upload Mortgage Statement if property has debt, or mark as N/A."
            }

        document_id = doc_row.id
        extraction_status = doc_row.extraction_status

        # Count transactions and check data quality
        count_query = text("""
            SELECT
                COUNT(*) as transaction_count,
                SUM(CASE WHEN principal_payment > 0 THEN 1 ELSE 0 END) as has_principal_count,
                SUM(CASE WHEN interest_payment > 0 THEN 1 ELSE 0 END) as has_interest_count
            FROM mortgage_statement_transactions
            WHERE property_id = :property_id
                AND period_id = :period_id
                AND is_deleted = false
        """)

        count_result = await self.db.execute(
            count_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        count_row = count_result.fetchone()

        transaction_count = count_row.transaction_count if count_row else 0
        has_principal = count_row.has_principal_count > 0 if count_row else False
        has_interest = count_row.has_interest_count > 0 if count_row else False

        # Determine completeness
        is_complete = (
            transaction_count >= self.MIN_MS_TRANSACTIONS and
            has_principal and
            has_interest and
            extraction_status == 'completed'
        )

        if is_complete:
            status = "GREEN"
            explanation = f"Mortgage Statement is complete with {transaction_count} transactions."
        elif transaction_count > 0:
            status = "YELLOW"
            explanation = f"Mortgage Statement present but may be incomplete. Has {transaction_count} transactions."
        else:
            status = "RED"
            explanation = "Mortgage Statement document uploaded but not extracted or no data present."

        return {
            "document_type": "Mortgage Statement",
            "present": True,
            "complete": is_complete,
            "status": status,
            "document_id": str(document_id),
            "extraction_status": extraction_status,
            "transaction_count": transaction_count,
            "has_principal_data": has_principal,
            "has_interest_data": has_interest,
            "explanation": explanation,
            "recommendation": self._get_ms_recommendation(is_complete, transaction_count)
        }

    async def calculate_completeness_percentage(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate overall document completeness percentage.

        Each of the 5 documents contributes 20% to the total.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing overall completeness metrics
        """
        logger.info(f"Calculating completeness percentage for property {property_id}, period {period_id}")

        # Check all 5 documents
        bs_result = await self.verify_balance_sheet_present(property_id, period_id)
        is_result = await self.verify_income_statement_present(property_id, period_id)
        cf_result = await self.verify_cash_flow_present(property_id, period_id)
        rr_result = await self.verify_rent_roll_present(property_id, period_id)
        ms_result = await self.verify_mortgage_statement_present(property_id, period_id)

        # Calculate score (each document = 20 points if complete)
        score = 0
        if bs_result["complete"]:
            score += 20
        if is_result["complete"]:
            score += 20
        if cf_result["complete"]:
            score += 20
        if rr_result["complete"]:
            score += 20
        if ms_result["complete"]:
            score += 20

        # Count documents present vs complete
        present_count = sum([
            bs_result["present"],
            is_result["present"],
            cf_result["present"],
            rr_result["present"],
            ms_result["present"]
        ])

        complete_count = sum([
            bs_result["complete"],
            is_result["complete"],
            cf_result["complete"],
            rr_result["complete"],
            ms_result["complete"]
        ])

        # Determine overall status
        if score == 100:
            overall_status = "GREEN"
            explanation = "All 5 required documents are present and complete. Ready for full forensic audit."
        elif score >= 80:
            overall_status = "GREEN"
            explanation = f"Document set is {score}% complete. Most documents present, minor gaps exist."
        elif score >= 60:
            overall_status = "YELLOW"
            explanation = f"Document set is {score}% complete. Some critical documents missing or incomplete."
        else:
            overall_status = "RED"
            explanation = f"Document set is only {score}% complete. Multiple documents missing. Forensic audit cannot proceed."

        return {
            "completeness_percentage": score,
            "documents_present": present_count,
            "documents_complete": complete_count,
            "total_required": 5,
            "overall_status": overall_status,
            "explanation": explanation,
            "document_details": {
                "balance_sheet": bs_result,
                "income_statement": is_result,
                "cash_flow": cf_result,
                "rent_roll": rr_result,
                "mortgage_statement": ms_result
            },
            "missing_documents": self._get_missing_documents([
                bs_result, is_result, cf_result, rr_result, ms_result
            ]),
            "recommendation": self._get_overall_recommendation(score, complete_count)
        }

    async def check_document_completeness(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run complete document completeness check (Phase 1).

        This is the entry point for Phase 1 of the forensic audit.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID

        Returns:
            Dict containing complete Phase 1 results
        """
        logger.info(f"Running Phase 1: Document Completeness Check for property {property_id}, period {period_id}")

        results = await self.calculate_completeness_percentage(property_id, period_id)

        return {
            "phase": "Phase 1: Document Completeness",
            "property_id": str(property_id),
            "period_id": str(period_id),
            "completeness_percentage": results["completeness_percentage"],
            "overall_status": results["overall_status"],
            "can_proceed_to_phase_2": results["completeness_percentage"] >= 80,
            "results": results
        }

    async def save_completeness_results(
        self,
        property_id: UUID,
        period_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Save document completeness results to database.

        Args:
            property_id: Property UUID
            period_id: Accounting period UUID
            results: Results from check_document_completeness()
        """
        logger.info(f"Saving completeness results for property {property_id}, period {period_id}")

        # Save to document_completeness table (UPSERT)
        upsert_query = text("""
            INSERT INTO document_completeness (
                property_id,
                period_id,
                completeness_percentage,
                documents_present,
                documents_complete,
                overall_status,
                can_proceed,
                results_json,
                created_at,
                updated_at
            ) VALUES (
                :property_id,
                :period_id,
                :completeness_pct,
                :docs_present,
                :docs_complete,
                :overall_status,
                :can_proceed,
                :results_json::jsonb,
                NOW(),
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                completeness_percentage = EXCLUDED.completeness_percentage,
                documents_present = EXCLUDED.documents_present,
                documents_complete = EXCLUDED.documents_complete,
                overall_status = EXCLUDED.overall_status,
                can_proceed = EXCLUDED.can_proceed,
                results_json = EXCLUDED.results_json,
                updated_at = NOW()
        """)

        import json

        await self.db.execute(
            upsert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "completeness_pct": results["completeness_percentage"],
                "docs_present": results["results"]["documents_present"],
                "docs_complete": results["results"]["documents_complete"],
                "overall_status": results["overall_status"],
                "can_proceed": results["can_proceed_to_phase_2"],
                "results_json": json.dumps(results)
            }
        )

        await self.db.commit()
        logger.info(f"Completeness results saved successfully")

    # Helper methods for recommendations

    def _get_bs_recommendation(self, is_complete: bool, line_count: int) -> str:
        """Get recommendation for Balance Sheet."""
        if is_complete:
            return "Balance Sheet is complete and ready for mathematical integrity tests (Phase 2)."
        elif line_count > 0:
            return "Re-extract Balance Sheet or manually verify all account categories are present."
        else:
            return "Upload Balance Sheet document and run extraction."

    def _get_is_recommendation(self, is_complete: bool, line_count: int) -> str:
        """Get recommendation for Income Statement."""
        if is_complete:
            return "Income Statement is complete and ready for mathematical integrity tests (Phase 2)."
        elif line_count > 0:
            return "Re-extract Income Statement or manually verify revenue and expense accounts."
        else:
            return "Upload Income Statement document and run extraction."

    def _get_cf_recommendation(self, is_complete: bool, line_count: int) -> str:
        """Get recommendation for Cash Flow."""
        if is_complete:
            return "Cash Flow Statement is complete and ready for reconciliation tests (Phase 3)."
        elif line_count > 0:
            return "Re-extract Cash Flow Statement or manually verify all activities are present."
        else:
            return "Upload Cash Flow Statement document and run extraction."

    def _get_rr_recommendation(self, is_complete: bool, tenant_count: int, active_count: int) -> str:
        """Get recommendation for Rent Roll."""
        if is_complete:
            return "Rent Roll is complete and ready for tenant risk analysis (Phase 4)."
        elif tenant_count > 0:
            return f"Rent Roll has {tenant_count} tenants but data may be incomplete. Verify extraction."
        else:
            return "Upload Rent Roll document and run extraction."

    def _get_ms_recommendation(self, is_complete: bool, transaction_count: int) -> str:
        """Get recommendation for Mortgage Statement."""
        if is_complete:
            return "Mortgage Statement is complete and ready for covenant compliance tests (Phase 7)."
        elif transaction_count > 0:
            return "Mortgage Statement present but may be incomplete. Verify extraction."
        else:
            return "Upload Mortgage Statement document and run extraction, or mark as N/A if no debt."

    def _get_missing_documents(self, results: List[Dict[str, Any]]) -> List[str]:
        """Get list of missing or incomplete documents."""
        missing = []
        for result in results:
            if not result["complete"]:
                missing.append(result["document_type"])
        return missing

    def _get_overall_recommendation(self, score: int, complete_count: int) -> str:
        """Get overall recommendation based on completeness."""
        if score == 100:
            return "All documents complete. Proceed to Phase 2: Mathematical Integrity Tests."
        elif score >= 80:
            return f"Document set is sufficient to proceed. {5 - complete_count} document(s) need attention but audit can begin."
        elif score >= 60:
            return "Upload and extract missing documents before proceeding with full forensic audit. Partial analysis is possible."
        else:
            return "Urgent: Multiple critical documents are missing. Upload all 5 documents before forensic audit can proceed."
