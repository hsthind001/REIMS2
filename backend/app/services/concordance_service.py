"""
Concordance Table Service

Generates and maintains concordance tables comparing extraction results
across all models. Automatically updated on document upload.
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.concordance_table import ConcordanceTable
from app.models.document_upload import DocumentUpload
from app.utils.extraction_engine import MultiEngineExtractor
from app.services.ensemble_engine import NumericNormalizer
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
import logging
import re

logger = logging.getLogger(__name__)


class ConcordanceService:
    """
    Service for generating and maintaining concordance tables
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.extractor = MultiEngineExtractor()
        self.normalizer = NumericNormalizer()
    
    def generate_concordance_table(
        self,
        upload_id: int,
        pdf_data: bytes,
        document_type: str,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Generate concordance table for a document upload
        
        Runs all models, extracts field values, compares them, and stores
        in concordance_tables table.
        
        Args:
            upload_id: Document upload ID
            pdf_data: PDF file bytes
            document_type: Type of document (balance_sheet, income_statement, etc.)
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            dict: Summary of concordance table generation
        """
        try:
            # Delete existing concordance records for this upload (replace strategy)
            self.db.query(ConcordanceTable).filter(
                ConcordanceTable.upload_id == upload_id
            ).delete()
            
            # Extract with all models
            all_results = self.extractor.extract_with_all_models_scored(pdf_data)
            
            if not all_results.get("success"):
                return {
                    "success": False,
                    "error": "Failed to extract with all models"
                }
            
            # Get field values from database (already extracted and stored)
            # This is more reliable than parsing text, as it uses the actual structured data
            field_values = self._extract_field_values_from_db(
                upload_id,
                document_type,
                all_results.get("results", [])
            )
            
            # Generate concordance records
            concordance_records = []
            total_fields = 0
            perfect_agreement = 0
            partial_agreement = 0
            
            for field_name, field_data in field_values.items():
                # Calculate agreement
                agreement_metrics = self._calculate_agreement(field_data)
                
                # Create concordance record
                record = ConcordanceTable(
                    upload_id=upload_id,
                    property_id=property_id,
                    period_id=period_id,
                    document_type=document_type,
                    field_name=field_name,
                    field_display_name=field_data.get("display_name", field_name),
                    account_code=field_data.get("account_code"),
                    model_values=field_data["values"],
                    normalized_value=agreement_metrics["normalized_value"],
                    agreement_count=agreement_metrics["agreement_count"],
                    total_models=agreement_metrics["total_models"],
                    agreement_percentage=agreement_metrics["agreement_percentage"],
                    has_consensus=agreement_metrics["has_consensus"],
                    is_perfect_agreement=agreement_metrics["is_perfect_agreement"],
                    conflicting_models=agreement_metrics["conflicting_models"],
                    final_value=agreement_metrics["final_value"],
                    final_model=agreement_metrics["final_model"]
                )
                
                self.db.add(record)
                concordance_records.append(record)
                
                total_fields += 1
                if agreement_metrics["is_perfect_agreement"]:
                    perfect_agreement += 1
                elif agreement_metrics["has_consensus"]:
                    partial_agreement += 1
            
            self.db.commit()
            
            # Calculate overall agreement
            overall_agreement = 0.0
            if concordance_records:
                overall_agreement = sum(
                    float(r.agreement_percentage) for r in concordance_records
                ) / len(concordance_records)
            
            logger.info(
                f"✅ Concordance table generated for upload {upload_id}: "
                f"{total_fields} fields, {overall_agreement:.2f}% overall agreement"
            )
            
            return {
                "success": True,
                "upload_id": upload_id,
                "total_fields": total_fields,
                "perfect_agreement": perfect_agreement,
                "partial_agreement": partial_agreement,
                "no_agreement": total_fields - perfect_agreement - partial_agreement,
                "overall_agreement_percentage": round(overall_agreement, 2),
                "records_created": len(concordance_records)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Concordance table generation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_field_values_from_db(
        self,
        upload_id: int,
        document_type: str,
        model_results: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Extract field values from database records and model extraction results
        
        Uses database records as the source of truth, then tries to match
        values from each model's extraction results.
        
        Args:
            upload_id: Document upload ID
            document_type: Type of document
            model_results: List of extraction results from all models
            
        Returns:
            dict: {field_name: {values: {...}, display_name: "...", account_code: "..."}}
        """
        field_values = {}
        
        # Map model names
        model_name_map = {
            "PyMuPDF": "pymupdf",
            "PDFPlumber": "pdfplumber",
            "Camelot": "camelot",
            "LayoutLMv3": "layoutlm",
            "EasyOCR": "easyocr",
            "Tesseract OCR": "tesseract",
            "OCR": "tesseract"
        }
        
        # Get database records based on document type
        if document_type == "income_statement":
            db_records = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload_id
            ).all()
            
            for record in db_records:
                field_name = f"account_{record.account_code.replace('-', '_')}"
                account_code = record.account_code
                display_name = record.account_name or account_code
                
                # Use period_amount as primary value
                value = record.period_amount if record.period_amount is not None else record.ytd_amount
                
                if value is not None:
                    if field_name not in field_values:
                        field_values[field_name] = {
                            "values": {},
                            "display_name": display_name,
                            "account_code": account_code
                        }
                    
                    # Store database value as reference
                    field_values[field_name]["db_value"] = str(value)
                    
                    # Try to find matching values in model results
                    value_str = str(value)
                    normalized_db_value = self.normalizer.normalize(value_str)
                    
                    for result in model_results:
                        if not result.get("success"):
                            continue
                        
                        model_name = model_name_map.get(result["model"], result["model"].lower())
                        extracted_data = result.get("extracted_data", {})
                        text = extracted_data.get("text", "")
                        tables = extracted_data.get("tables", [])
                        
                        # Search for this account code and amount in extracted data
                        found_value = self._find_value_in_extraction(
                            account_code,
                            normalized_db_value,
                            text,
                            tables
                        )
                        
                        if found_value:
                            field_values[field_name]["values"][model_name] = found_value
                        else:
                            # If not found, mark as missing
                            if model_name not in field_values[field_name]["values"]:
                                field_values[field_name]["values"][model_name] = None
        
        elif document_type == "balance_sheet":
            db_records = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.upload_id == upload_id
            ).all()
            
            for record in db_records:
                field_name = f"account_{record.account_code.replace('-', '_')}"
                account_code = record.account_code
                display_name = record.account_name or account_code
                value = record.amount
                
                if value is not None:
                    if field_name not in field_values:
                        field_values[field_name] = {
                            "values": {},
                            "display_name": display_name,
                            "account_code": account_code
                        }
                    
                    field_values[field_name]["db_value"] = str(value)
                    normalized_db_value = self.normalizer.normalize(str(value))
                    
                    for result in model_results:
                        if not result.get("success"):
                            continue
                        
                        model_name = model_name_map.get(result["model"], result["model"].lower())
                        extracted_data = result.get("extracted_data", {})
                        text = extracted_data.get("text", "")
                        tables = extracted_data.get("tables", [])
                        
                        found_value = self._find_value_in_extraction(
                            account_code,
                            normalized_db_value,
                            text,
                            tables
                        )
                        
                        if found_value:
                            field_values[field_name]["values"][model_name] = found_value
                        else:
                            if model_name not in field_values[field_name]["values"]:
                                field_values[field_name]["values"][model_name] = None
        
        elif document_type == "cash_flow":
            db_records = self.db.query(CashFlowData).filter(
                CashFlowData.upload_id == upload_id
            ).all()
            
            for record in db_records:
                field_name = f"account_{record.account_code.replace('-', '_')}"
                account_code = record.account_code
                display_name = record.account_name or account_code
                value = record.amount
                
                if value is not None:
                    if field_name not in field_values:
                        field_values[field_name] = {
                            "values": {},
                            "display_name": display_name,
                            "account_code": account_code
                        }
                    
                    field_values[field_name]["db_value"] = str(value)
                    normalized_db_value = self.normalizer.normalize(str(value))
                    
                    for result in model_results:
                        if not result.get("success"):
                            continue
                        
                        model_name = model_name_map.get(result["model"], result["model"].lower())
                        extracted_data = result.get("extracted_data", {})
                        text = extracted_data.get("text", "")
                        tables = extracted_data.get("tables", [])
                        
                        found_value = self._find_value_in_extraction(
                            account_code,
                            normalized_db_value,
                            text,
                            tables
                        )
                        
                        if found_value:
                            field_values[field_name]["values"][model_name] = found_value
                        else:
                            if model_name not in field_values[field_name]["values"]:
                                field_values[field_name]["values"][model_name] = None
        
        return field_values
    
    def _find_value_in_extraction(
        self,
        account_code: str,
        normalized_value: str,
        text: str,
        tables: List[Dict]
    ) -> Optional[str]:
        """
        Find a value in extracted text/tables matching account code and normalized value
        
        Args:
            account_code: Account code to search for (e.g., "4010-0000")
            normalized_value: Normalized numeric value to match
            text: Extracted text
            tables: Extracted tables
            
        Returns:
            Found value string or None
        """
        # Search in text for account code pattern
        pattern = rf'{re.escape(account_code)}\s+[^\n]*?([-]?[\d,]+\.[\d]{{2}})'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found_amount = match.group(1)
            normalized_found = self.normalizer.normalize(found_amount)
            
            if normalized_found == normalized_value:
                return found_amount
        
        # Search in tables
        for table in tables:
            if isinstance(table, dict) and "data" in table:
                rows = table.get("data", [])
                headers = table.get("headers", [])
                
                # Find account code column
                account_col = None
                amount_col = None
                
                for idx, header in enumerate(headers):
                    header_str = str(header).lower()
                    if "account" in header_str or "code" in header_str:
                        account_col = idx
                    if "amount" in header_str or "$" in header_str or "period" in header_str:
                        amount_col = idx
                
                if account_col is not None and amount_col is not None:
                    for row in rows:
                        if len(row) > max(account_col, amount_col):
                            row_account = str(row[account_col]).strip()
                            row_amount = str(row[amount_col]).strip()
                            
                            if account_code in row_account:
                                normalized_row = self.normalizer.normalize(row_amount)
                                if normalized_row == normalized_value:
                                    return row_amount
        
        return None
    
    def _calculate_agreement(self, field_data: Dict) -> Dict:
        """
        Calculate agreement metrics for a field
        
        Args:
            field_data: {values: {model: value, ...}, display_name: "...", account_code: "..."}
            
        Returns:
            dict: Agreement metrics
        """
        values = field_data.get("values", {})
        
        # Filter out None values
        non_null_values = {k: v for k, v in values.items() if v is not None}
        
        if not non_null_values:
            return {
                "normalized_value": None,
                "agreement_count": 0,
                "total_models": len(values),
                "agreement_percentage": Decimal("0.0"),
                "has_consensus": False,
                "is_perfect_agreement": False,
                "conflicting_models": list(values.keys()),
                "final_value": None,
                "final_model": None
            }
        
        # Normalize all values for comparison
        normalized_values = {}
        for model, value in non_null_values.items():
            if value:
                normalized = self.normalizer.normalize(value)
                normalized_values[model] = normalized
        
        if not normalized_values:
            return {
                "normalized_value": None,
                "agreement_count": 0,
                "total_models": len(values),
                "agreement_percentage": Decimal("0.0"),
                "has_consensus": False,
                "is_perfect_agreement": False,
                "conflicting_models": list(values.keys()),
                "final_value": None,
                "final_model": None
            }
        
        # Find most common normalized value (consensus)
        from collections import Counter
        value_counts = Counter(normalized_values.values())
        most_common_value, agreement_count = value_counts.most_common(1)[0]
        
        total_models = len(normalized_values)
        agreement_percentage = (agreement_count / total_models * 100) if total_models > 0 else 0.0
        
        # Find conflicting models
        conflicting_models = [
            model for model, norm_val in normalized_values.items()
            if norm_val != most_common_value
        ]
        
        # Determine final value (use most common, or first if tie)
        final_value = most_common_value
        final_model = None
        for model, norm_val in normalized_values.items():
            if norm_val == most_common_value:
                final_model = model
                break
        
        # Consensus thresholds
        has_consensus = agreement_percentage >= 75.0
        is_perfect_agreement = agreement_percentage == 100.0
        
        return {
            "normalized_value": most_common_value,
            "agreement_count": agreement_count,
            "total_models": total_models,
            "agreement_percentage": Decimal(str(round(agreement_percentage, 2))),
            "has_consensus": has_consensus,
            "is_perfect_agreement": is_perfect_agreement,
            "conflicting_models": conflicting_models,
            "final_value": final_value,
            "final_model": final_model or "ensemble"
        }
    
    def get_concordance_table(
        self,
        upload_id: int
    ) -> Dict[str, Any]:
        """
        Get concordance table for an upload
        
        Args:
            upload_id: Document upload ID
            
        Returns:
            dict: Concordance table data
        """
        records = self.db.query(ConcordanceTable).filter(
            ConcordanceTable.upload_id == upload_id
        ).order_by(ConcordanceTable.field_name).all()
        
        concordance_table = []
        for record in records:
            concordance_table.append({
                "field": record.field_name,
                "field_name": record.field_name,  # Alias for consistency
                "field_display_name": record.field_display_name,
                "account_code": record.account_code,
                "values": record.model_values,
                "normalized_value": record.normalized_value,
                "agreement_count": record.agreement_count,
                "total_models": record.total_models,
                "agreement_percentage": float(record.agreement_percentage),
                "has_consensus": record.has_consensus,
                "is_perfect_agreement": record.is_perfect_agreement,
                "conflicting_models": record.conflicting_models or [],
                "final_value": record.final_value,
                "final_model": record.final_model
            })
        
        # Calculate summary
        total_fields = len(records)
        perfect_agreement = sum(1 for r in records if r.is_perfect_agreement)
        partial_agreement = sum(1 for r in records if r.has_consensus and not r.is_perfect_agreement)
        no_agreement = total_fields - perfect_agreement - partial_agreement
        
        overall_agreement = 0.0
        if records:
            overall_agreement = sum(float(r.agreement_percentage) for r in records) / len(records)
        
        return {
            "success": True,
            "upload_id": upload_id,
            "concordance_table": concordance_table,
            "summary": {
                "total_fields": total_fields,
                "perfect_agreement": perfect_agreement,
                "partial_agreement": partial_agreement,
                "no_agreement": no_agreement,
                "overall_agreement_percentage": round(overall_agreement, 2)
            }
        }
    
    def export_concordance_table_csv(
        self,
        upload_id: int
    ) -> str:
        """
        Export concordance table as CSV
        
        Args:
            upload_id: Document upload ID
            
        Returns:
            str: CSV content
        """
        import csv
        import io
        
        records = self.db.query(ConcordanceTable).filter(
            ConcordanceTable.upload_id == upload_id
        ).order_by(ConcordanceTable.field_name).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Field Name",
            "Display Name",
            "Account Code",
            "PyMuPDF",
            "PDFPlumber",
            "Camelot",
            "LayoutLMv3",
            "EasyOCR",
            "Tesseract",
            "Final Value",
            "Agreement %",
            "Consensus",
            "Conflicting Models"
        ])
        
        # Data rows
        for record in records:
            values = record.model_values or {}
            writer.writerow([
                record.field_name,
                record.field_display_name or "",
                record.account_code or "",
                values.get("pymupdf", "") or "",
                values.get("pdfplumber", "") or "",
                values.get("camelot", "") or "",
                values.get("layoutlm", "") or "",
                values.get("easyocr", "") or "",
                values.get("tesseract", "") or "",
                record.final_value or "",
                f"{float(record.agreement_percentage):.1f}%",
                "✅" if record.has_consensus else "⚠️",
                ", ".join(record.conflicting_models or [])
            ])
        
        return output.getvalue()

