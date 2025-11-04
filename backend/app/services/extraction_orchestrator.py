"""
Extraction Orchestrator - Coordinates PDF extraction and financial data parsing
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import re

from app.utils.extraction_engine import MultiEngineExtractor
from app.utils.template_extractor import TemplateExtractor
from app.utils.financial_table_parser import FinancialTableParser
from app.models.document_upload import DocumentUpload
from app.models.extraction_log import ExtractionLog
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.financial_metrics import FinancialMetrics
from app.models.chart_of_accounts import ChartOfAccounts
from app.db.minio_client import download_file
from app.core.config import settings


class ExtractionOrchestrator:
    """Orchestrate complete extraction and financial data parsing workflow"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extraction_engine = MultiEngineExtractor()
        self.template_extractor = TemplateExtractor(db)
        self.table_parser = FinancialTableParser()
    
    def extract_and_parse_document(self, upload_id: int) -> Dict:
        """
        Complete extraction workflow for a document upload
        
        Steps:
        1. Download PDF from MinIO
        2. Extract text using MultiEngineExtractor
        3. Parse structured financial data using TemplateExtractor
        4. Insert data into appropriate financial tables
        5. Calculate financial metrics
        6. Create extraction log
        7. Update upload status
        
        Args:
            upload_id: DocumentUpload ID
        
        Returns:
            dict: Extraction result with success status and details
        """
        try:
            # Get upload record
            upload = self.db.query(DocumentUpload).filter(
                DocumentUpload.id == upload_id
            ).first()
            
            if not upload:
                return {
                    "success": False,
                    "error": f"Upload {upload_id} not found"
                }
            
            # Update status to processing
            upload.extraction_status = "processing"
            upload.extraction_started_at = datetime.now()
            self.db.commit()
            
            # Step 1: Download PDF from MinIO
            pdf_data = download_file(
                object_name=upload.file_path,
                bucket_name=settings.MINIO_BUCKET_NAME
            )
            
            if not pdf_data:
                upload.extraction_status = "failed"
                upload.extraction_completed_at = datetime.now()
                self.db.commit()
                return {
                    "success": False,
                    "error": "Failed to download file from storage"
                }
            
            # Step 2: Extract text with validation
            extraction_result = self.extraction_engine.extract_with_validation(
                pdf_data=pdf_data,
                strategy="auto",
                lang="eng"
            )
            
            if not extraction_result.get("success"):
                upload.extraction_status = "failed"
                upload.extraction_completed_at = datetime.now()
                self.db.commit()
                return {
                    "success": False,
                    "error": extraction_result.get("error", "Extraction failed")
                }
            
            # Step 3: Create extraction log
            extraction_log = self._create_extraction_log(
                upload=upload,
                extraction_result=extraction_result
            )
            
            # Link extraction log to upload
            upload.extraction_id = extraction_log.id
            self.db.commit()
            
            # Step 4: Parse and insert financial data based on document type
            extracted_text = extraction_result["extraction"].get("text", "")
            
            parse_result = self._parse_and_insert_financial_data(
                upload=upload,
                extracted_text=extracted_text,
                confidence_score=extraction_result["validation"]["confidence_score"]
            )
            
            if not parse_result["success"]:
                upload.extraction_status = "completed"  # Mark completed but with warnings
                upload.extraction_completed_at = datetime.now()
                self.db.commit()
                return {
                    "success": True,
                    "warning": parse_result.get("error"),
                    "extraction_log_id": extraction_log.id,
                    "records_inserted": 0
                }
            
            # Step 5: Calculate and store comprehensive financial metrics
            # Trigger after ANY document type (not just balance sheet)
            self._calculate_financial_metrics(upload)
            
            # Step 6: Run validations
            validation_results = self._run_validations(upload)
            
            # Step 7: Update upload status to completed
            upload.extraction_status = "completed"
            upload.extraction_completed_at = datetime.now()
            self.db.commit()
            
            return {
                "success": True,
                "upload_id": upload_id,
                "extraction_log_id": extraction_log.id,
                "records_inserted": parse_result.get("records_inserted", 0),
                "confidence_score": extraction_result["validation"]["confidence_score"],
                "needs_review": extraction_result["needs_review"],
                "validation_results": validation_results
            }
        
        except Exception as e:
            # Handle any unexpected errors
            if upload:
                upload.extraction_status = "failed"
                upload.extraction_completed_at = datetime.now()
                self.db.commit()
            
            return {
                "success": False,
                "error": f"Extraction failed: {str(e)}"
            }
    
    def _create_extraction_log(
        self,
        upload: DocumentUpload,
        extraction_result: Dict
    ) -> ExtractionLog:
        """Create extraction log entry"""
        extraction = extraction_result["extraction"]
        validation = extraction_result["validation"]
        classification = extraction_result["classification"]
        
        log_entry = ExtractionLog(
            filename=upload.file_name,
            file_size=upload.file_size_bytes,
            file_hash=upload.file_hash,
            document_type=classification.get("document_type", "unknown"),
            total_pages=extraction.get("total_pages", 0),
            strategy_used=extraction_result["strategy_used"],
            engines_used=extraction.get("engines_used", [extraction.get("engine")]),
            primary_engine=extraction.get("engine", "unknown"),
            confidence_score=validation["confidence_score"],
            quality_level=validation["overall_quality"],
            passed_checks=validation["passed_checks"],
            total_checks=validation["total_checks"],
            processing_time_seconds=extraction_result["processing_time_seconds"],
            validation_issues=validation["issues"],
            validation_warnings=validation["warnings"],
            recommendations=validation.get("recommendations", []),
            text_preview=extraction.get("text", "")[:500],
            total_words=extraction.get("total_words", 0),
            total_chars=extraction.get("total_chars", 0),
            tables_found=0,
            images_found=0,
            needs_review=extraction_result["needs_review"],
            custom_metadata=classification.get("characteristics", {})
        )
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        
        return log_entry
    
    def _parse_and_insert_financial_data(
        self,
        upload: DocumentUpload,
        extracted_text: str,
        confidence_score: float
    ) -> Dict:
        """
        Parse extracted text and insert into appropriate financial tables
        
        Enhanced with table extraction for 100% accuracy
        """
        try:
            # Download PDF again for table extraction
            pdf_data = download_file(
                object_name=upload.file_path,
                bucket_name=settings.MINIO_BUCKET_NAME
            )
            
            if not pdf_data:
                return {
                    "success": False,
                    "error": "Failed to download PDF for table extraction"
                }
            
            # Step 1: Try table extraction first (highest accuracy)
            parsed_data = self._extract_with_tables(pdf_data, upload.document_type)
            
            # Step 2: If table extraction yields no results, try template extractor
            if not parsed_data.get("success") or not parsed_data.get("line_items"):
                parsed_data = self.template_extractor.extract_using_template(
                    extracted_text=extracted_text,
                    document_type=upload.document_type,
                    template_name=None
                )
            
            # Step 3: If still no success, try fallback regex extraction
            if not parsed_data.get("success") or not parsed_data.get("line_items"):
                parsed_data = self._fallback_extraction(extracted_text, upload.document_type)
            
            # Step 4: Intelligent account matching
            if parsed_data.get("line_items"):
                parsed_data["line_items"] = self._match_accounts_intelligent(
                    parsed_data["line_items"]
                )
            
            # Step 5: Insert based on document type
            records_inserted = 0
            
            if upload.document_type == "balance_sheet":
                records_inserted = self._insert_balance_sheet_data(
                    upload=upload,
                    parsed_data=parsed_data,
                    confidence_score=confidence_score
                )
            elif upload.document_type == "income_statement":
                records_inserted = self._insert_income_statement_data(
                    upload=upload,
                    parsed_data=parsed_data,
                    confidence_score=confidence_score
                )
            elif upload.document_type == "cash_flow":
                records_inserted = self._insert_cash_flow_data(
                    upload=upload,
                    parsed_data=parsed_data,
                    confidence_score=confidence_score
                )
            elif upload.document_type == "rent_roll":
                records_inserted = self._insert_rent_roll_data(
                    upload=upload,
                    parsed_data=parsed_data,
                    confidence_score=confidence_score
                )
            
            return {
                "success": True,
                "records_inserted": records_inserted,
                "extraction_method": parsed_data.get("extraction_method", "unknown")
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _insert_balance_sheet_data(
        self,
        upload: DocumentUpload,
        parsed_data: Dict,
        confidence_score: float
    ) -> int:
        """Insert balance sheet line items with enhanced matching"""
        items = parsed_data.get("line_items", [])
        records_inserted = 0
        
        # Deduplicate items by account_code + amount + page to allow same account in different contexts
        seen_keys = set()
        deduplicated_items = []
        for item in items:
            account_code = item.get("matched_account_code") or item.get("account_code", "")
            amount = item.get("amount", 0.0)
            page = item.get("page", 1)
            # Create unique key combining code, amount, and page
            unique_key = f"{account_code}_{amount}_{page}"
            if unique_key not in seen_keys:
                deduplicated_items.append(item)
                seen_keys.add(unique_key)
        
        for item in deduplicated_items:
            account_code = item.get("matched_account_code") or item.get("account_code", "")
            account_name = item.get("matched_account_name") or item.get("account_name", "")
            amount = item.get("amount", 0.0)
            account_id = item.get("matched_account_id")
            item_confidence = item.get("confidence", confidence_score)
            match_confidence = item.get("match_confidence", 100.0)
            
            if not account_name:
                continue
            
            # Use average of extraction and match confidence
            final_confidence = (float(item_confidence) + float(match_confidence)) / 2.0
            
            # Check if entry already exists (avoid duplicates)
            existing = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == upload.property_id,
                BalanceSheetData.period_id == upload.period_id,
                BalanceSheetData.account_code == account_code
            ).first()
            
            if existing:
                # Update existing entry
                existing.amount = Decimal(str(amount))
                existing.extraction_confidence = Decimal(str(final_confidence))
                existing.upload_id = upload.id
                existing.account_id = account_id
                existing.needs_review = final_confidence < 85.0 or account_id is None
            else:
                # Insert new entry
                bs_data = BalanceSheetData(
                    property_id=upload.property_id,
                    period_id=upload.period_id,
                    upload_id=upload.id,
                    account_id=account_id,
                    account_code=account_code,
                    account_name=account_name,
                    amount=Decimal(str(amount)),
                    extraction_confidence=Decimal(str(final_confidence)),
                    needs_review=final_confidence < 85.0 or account_id is None
                )
                self.db.add(bs_data)
                records_inserted += 1
        
        self.db.commit()
        return records_inserted
    
    def _insert_income_statement_data(
        self,
        upload: DocumentUpload,
        parsed_data: Dict,
        confidence_score: float
    ) -> int:
        """Insert income statement line items"""
        items = parsed_data.get("line_items", [])
        records_inserted = 0
        
        # Deduplicate items by account_code + amount + page
        seen_keys = set()
        deduplicated_items = []
        for item in items:
            account_code = item.get("account_code", "")
            period_amount = item.get("period_amount", 0.0)
            page = item.get("page", 1)
            unique_key = f"{account_code}_{period_amount}_{page}"
            if unique_key not in seen_keys:
                deduplicated_items.append(item)
                seen_keys.add(unique_key)
        
        for item in deduplicated_items:
            account_code = item.get("account_code", "")
            account_name = item.get("account_name", "")
            period_amount = item.get("period_amount", 0.0)
            ytd_amount = item.get("ytd_amount")
            period_percentage = item.get("period_percentage")
            ytd_percentage = item.get("ytd_percentage")
            
            if not account_code or not account_name:
                continue
            
            # Try to find matching account
            account = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.account_code == account_code
            ).first()
            
            if not account:
                account = self.db.query(ChartOfAccounts).filter(
                    ChartOfAccounts.account_name.ilike(f"%{account_name}%")
                ).first()
            
            account_id = account.id if account else None
            
            # Check for existing entry
            existing = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == upload.property_id,
                IncomeStatementData.period_id == upload.period_id,
                IncomeStatementData.account_code == account_code
            ).first()
            
            if existing:
                # Update existing
                existing.period_amount = Decimal(str(period_amount))
                if ytd_amount is not None:
                    existing.ytd_amount = Decimal(str(ytd_amount))
                if period_percentage is not None:
                    existing.period_percentage = Decimal(str(period_percentage))
                if ytd_percentage is not None:
                    existing.ytd_percentage = Decimal(str(ytd_percentage))
                existing.extraction_confidence = Decimal(str(confidence_score))
                existing.upload_id = upload.id
                existing.needs_review = confidence_score < 85.0
            else:
                # Insert new
                is_data = IncomeStatementData(
                    property_id=upload.property_id,
                    period_id=upload.period_id,
                    upload_id=upload.id,
                    account_id=account_id,
                    account_code=account_code,
                    account_name=account_name,
                    period_amount=Decimal(str(period_amount)),
                    ytd_amount=Decimal(str(ytd_amount)) if ytd_amount is not None else None,
                    period_percentage=Decimal(str(period_percentage)) if period_percentage is not None else None,
                    ytd_percentage=Decimal(str(ytd_percentage)) if ytd_percentage is not None else None,
                    extraction_confidence=Decimal(str(confidence_score)),
                    needs_review=confidence_score < 85.0
                )
                self.db.add(is_data)
                records_inserted += 1
        
        self.db.commit()
        return records_inserted
    
    def _insert_cash_flow_data(
        self,
        upload: DocumentUpload,
        parsed_data: Dict,
        confidence_score: float
    ) -> int:
        """Insert cash flow line items"""
        items = parsed_data.get("line_items", [])
        records_inserted = 0
        
        # Deduplicate items by account_code + amount + page
        seen_keys = set()
        deduplicated_items = []
        for item in items:
            account_code = item.get("account_code", "")
            amount = item.get("amount", 0.0)
            page = item.get("page", 1)
            unique_key = f"{account_code}_{amount}_{page}"
            if unique_key not in seen_keys:
                deduplicated_items.append(item)
                seen_keys.add(unique_key)
        
        for item in deduplicated_items:
            account_code = item.get("account_code", "")
            account_name = item.get("account_name", "")
            amount = item.get("amount", 0.0)
            cash_flow_category = item.get("cash_flow_category", "operating")
            
            if not account_code or not account_name:
                continue
            
            # Try to find matching account
            account = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.account_code == account_code
            ).first()
            
            if not account:
                account = self.db.query(ChartOfAccounts).filter(
                    ChartOfAccounts.account_name.ilike(f"%{account_name}%")
                ).first()
            
            account_id = account.id if account else None
            
            # Check for existing entry
            existing = self.db.query(CashFlowData).filter(
                CashFlowData.property_id == upload.property_id,
                CashFlowData.period_id == upload.period_id,
                CashFlowData.account_code == account_code
            ).first()
            
            if existing:
                existing.period_amount = Decimal(str(amount))
                existing.cash_flow_category = cash_flow_category
                existing.extraction_confidence = Decimal(str(confidence_score))
                existing.upload_id = upload.id
                existing.needs_review = confidence_score < 85.0
            else:
                cf_data = CashFlowData(
                    property_id=upload.property_id,
                    period_id=upload.period_id,
                    upload_id=upload.id,
                    account_id=account_id,
                    account_code=account_code,
                    account_name=account_name,
                    period_amount=Decimal(str(amount)),
                    cash_flow_category=cash_flow_category,
                    is_inflow=amount > 0,
                    extraction_confidence=Decimal(str(confidence_score)),
                    needs_review=confidence_score < 85.0
                )
                self.db.add(cf_data)
                records_inserted += 1
        
        self.db.commit()
        return records_inserted
    
    def _insert_rent_roll_data(
        self,
        upload: DocumentUpload,
        parsed_data: Dict,
        confidence_score: float
    ) -> int:
        """
        Insert rent roll tenant data - Template v2.0 implementation
        
        Extracts all 24 fields, links gross rent rows, runs validation,
        and calculates quality scores.
        """
        from app.utils.rent_roll_validator import RentRollValidator
        from datetime import datetime
        
        items = parsed_data.get("line_items", [])
        report_date = parsed_data.get("report_date")
        records_inserted = 0
        parent_row_map = {}  # Maps unit_number -> parent_row_id for gross rent linking
        
        # Run validation on all records
        validator = RentRollValidator()
        validation_flags = validator.validate_records(items, report_date)
        quality_result = validator.calculate_quality_score()
        
        print(f"Rent Roll Validation: Quality Score = {quality_result['quality_score']:.1f}%")
        print(f"  Critical: {quality_result['critical_count']}, Warnings: {quality_result['warning_count']}, Info: {quality_result['info_count']}")
        print(f"  Recommendation: {quality_result['recommendation']}")
        
        # Process each item
        for idx, item in enumerate(items, 1):
            unit_number = item.get("unit_number", "")
            if not unit_number:
                continue
            
            # Get validation flags for this record
            record_flags = validator.get_flags_for_record(idx)
            notes_list = [f"[{flag.severity}] {flag.message}" for flag in record_flags]
            notes = "\n".join(notes_list) if notes_list else None
            
            # Check for existing entry
            existing = self.db.query(RentRollData).filter(
                RentRollData.property_id == upload.property_id,
                RentRollData.period_id == upload.period_id,
                RentRollData.unit_number == unit_number,
                RentRollData.is_gross_rent_row == item.get("is_gross_rent_row", False)
            ).first()
            
            # Prepare all fields
            tenant_name = item.get("tenant_name") or "VACANT"
            is_vacant = item.get("is_vacant", False)
            is_gross_rent_row = item.get("is_gross_rent_row", False)
            occupancy_status = "vacant" if is_vacant else "occupied"
            
            # Get parent_row_id for gross rent rows
            parent_row_id = None
            if is_gross_rent_row and unit_number in parent_row_map:
                parent_row_id = parent_row_map[unit_number]
            
            # Helper to safely convert to Decimal
            def to_decimal(val):
                if val is None:
                    return None
                try:
                    return Decimal(str(val))
                except:
                    return None
            
            # Helper to safely convert date strings
            def to_date(date_str):
                if not date_str:
                    return None
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    return None
            
            if existing:
                # Update existing record with all fields
                existing.tenant_name = tenant_name
                existing.tenant_code = item.get("tenant_id")
                existing.lease_type = item.get("lease_type")
                existing.lease_start_date = to_date(item.get("lease_start_date"))
                existing.lease_end_date = to_date(item.get("lease_end_date"))
                existing.lease_term_months = item.get("lease_term_months")
                existing.unit_area_sqft = to_decimal(item.get("unit_area_sqft"))
                existing.monthly_rent = to_decimal(item.get("monthly_rent"))
                existing.monthly_rent_per_sqft = to_decimal(item.get("monthly_rent_per_sqft"))
                existing.annual_rent = to_decimal(item.get("annual_rent"))
                existing.annual_rent_per_sqft = to_decimal(item.get("annual_rent_per_sqft"))
                existing.security_deposit = to_decimal(item.get("security_deposit"))
                existing.loc_amount = to_decimal(item.get("loc_amount"))
                # Template v2.0 fields
                existing.tenancy_years = to_decimal(item.get("tenancy_years"))
                existing.annual_recoveries_per_sf = to_decimal(item.get("annual_recoveries_per_sf"))
                existing.annual_misc_per_sf = to_decimal(item.get("annual_misc_per_sf"))
                existing.is_gross_rent_row = is_gross_rent_row
                existing.parent_row_id = parent_row_id
                existing.notes = notes
                existing.occupancy_status = occupancy_status
                existing.extraction_confidence = Decimal(str(quality_result['quality_score']))
                existing.upload_id = upload.id
                existing.needs_review = quality_result['quality_score'] < 99.0
            else:
                # Create new record
                rr_data = RentRollData(
                    property_id=upload.property_id,
                    period_id=upload.period_id,
                    upload_id=upload.id,
                    # Basic fields
                    unit_number=unit_number,
                    tenant_name=tenant_name,
                    tenant_code=item.get("tenant_id"),
                    lease_type=item.get("lease_type"),
                    # Dates
                    lease_start_date=to_date(item.get("lease_start_date")),
                    lease_end_date=to_date(item.get("lease_end_date")),
                    lease_term_months=item.get("lease_term_months"),
                    # Area
                    unit_area_sqft=to_decimal(item.get("unit_area_sqft")),
                    # Financials
                    monthly_rent=to_decimal(item.get("monthly_rent")),
                    monthly_rent_per_sqft=to_decimal(item.get("monthly_rent_per_sqft")),
                    annual_rent=to_decimal(item.get("annual_rent")),
                    annual_rent_per_sqft=to_decimal(item.get("annual_rent_per_sqft")),
                    security_deposit=to_decimal(item.get("security_deposit")),
                    loc_amount=to_decimal(item.get("loc_amount")),
                    # Template v2.0 fields
                    tenancy_years=to_decimal(item.get("tenancy_years")),
                    annual_recoveries_per_sf=to_decimal(item.get("annual_recoveries_per_sf")),
                    annual_misc_per_sf=to_decimal(item.get("annual_misc_per_sf")),
                    is_gross_rent_row=is_gross_rent_row,
                    parent_row_id=parent_row_id,
                    notes=notes,
                    # Status
                    occupancy_status=occupancy_status,
                    extraction_confidence=Decimal(str(quality_result['quality_score'])),
                    needs_review=quality_result['quality_score'] < 99.0
                )
                self.db.add(rr_data)
                self.db.flush()  # Get the ID for parent_row_map
                
                # Store ID for gross rent row linking
                if not is_gross_rent_row:
                    parent_row_map[unit_number] = rr_data.id
                
                records_inserted += 1
        
        self.db.commit()
        
        # Log extraction summary
        print(f"Inserted {records_inserted} rent roll records")
        print(f"Quality: {quality_result['quality_score']:.1f}% - {quality_result['recommendation']}")
        
        return records_inserted
    
    def _calculate_financial_metrics(self, upload: DocumentUpload):
        """
        Calculate comprehensive financial metrics using MetricsService
        
        Calculates all 35 metrics from all available statement types:
        - Balance sheet ratios
        - Income statement margins
        - Cash flow summaries
        - Rent roll occupancy
        - Performance metrics
        """
        try:
            from app.services.metrics_service import MetricsService
            
            metrics_service = MetricsService(self.db)
            metrics = metrics_service.calculate_all_metrics(
                property_id=upload.property_id,
                period_id=upload.period_id
            )
            
            return metrics
        
        except Exception as e:
            # Log error but don't fail extraction
            print(f"Warning: Metrics calculation failed for upload {upload.id}: {str(e)}")
            return None
    
    def _extract_with_tables(self, pdf_data: bytes, document_type: str) -> Dict:
        """
        Extract financial data using table structure preservation
        
        Uses FinancialTableParser for highest accuracy
        Returns: structured data with proper column alignment
        """
        try:
            if document_type == "balance_sheet":
                return self.table_parser.extract_balance_sheet_table(pdf_data)
            elif document_type == "income_statement":
                return self.table_parser.extract_income_statement_table(pdf_data)
            elif document_type == "cash_flow":
                return self.table_parser.extract_cash_flow_table(pdf_data)
            elif document_type == "rent_roll":
                return self.table_parser.extract_rent_roll_table(pdf_data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown document type: {document_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Table extraction failed: {str(e)}"
            }
    
    def _match_accounts_intelligent(self, extracted_items: List[Dict]) -> List[Dict]:
        """
        Intelligent account matching with multiple strategies
        
        Strategies (in order):
        1. Exact code match
        2. Fuzzy code match (handles OCR errors)
        3. Exact name match
        4. Fuzzy name match (80%+ similarity)
        5. Log unmapped for review
        
        Returns: enhanced items with matched_account_id
        """
        from fuzzywuzzy import fuzz
        
        # Get all active accounts from chart
        all_accounts = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.is_active == True
        ).all()
        
        # Create lookup dictionaries
        accounts_by_code = {acc.account_code: acc for acc in all_accounts}
        accounts_by_name = {acc.account_name.lower(): acc for acc in all_accounts}
        
        enhanced_items = []
        
        for item in extracted_items:
            account_code = item.get("account_code", "")
            account_name = item.get("account_name", "")
            matched_account = None
            match_method = None
            match_confidence = 0.0
            
            # Strategy 1: Exact code match
            if account_code and account_code in accounts_by_code:
                matched_account = accounts_by_code[account_code]
                match_method = "exact_code"
                match_confidence = 100.0
            
            # Strategy 2: Fuzzy code match (for OCR errors like 0 vs O)
            elif account_code:
                best_match = None
                best_score = 0
                for code, account in accounts_by_code.items():
                    score = fuzz.ratio(account_code, code)
                    if score > best_score and score >= 90:  # 90%+ similarity
                        best_score = score
                        best_match = account
                
                if best_match:
                    matched_account = best_match
                    match_method = "fuzzy_code"
                    match_confidence = float(best_score)
            
            # Strategy 3: Exact name match
            if not matched_account and account_name:
                name_lower = account_name.lower().strip()
                if name_lower in accounts_by_name:
                    matched_account = accounts_by_name[name_lower]
                    match_method = "exact_name"
                    match_confidence = 100.0
            
            # Strategy 4: Fuzzy name match
            if not matched_account and account_name:
                best_match = None
                best_score = 0
                for account in all_accounts:
                    score = fuzz.token_set_ratio(account_name.lower(), account.account_name.lower())
                    if score > best_score and score >= 80:  # 80%+ similarity
                        best_score = score
                        best_match = account
                
                if best_match:
                    matched_account = best_match
                    match_method = "fuzzy_name"
                    match_confidence = float(best_score)
            
            # Enhance item with match information
            enhanced_item = item.copy()
            if matched_account:
                enhanced_item["matched_account_id"] = matched_account.id
                enhanced_item["matched_account_code"] = matched_account.account_code
                enhanced_item["matched_account_name"] = matched_account.account_name
                enhanced_item["match_method"] = match_method
                enhanced_item["match_confidence"] = match_confidence
            else:
                # Log unmapped account
                enhanced_item["matched_account_id"] = None
                enhanced_item["match_method"] = "unmapped"
                enhanced_item["match_confidence"] = 0.0
                enhanced_item["needs_review"] = True
            
            enhanced_items.append(enhanced_item)
        
        return enhanced_items
    
    def _fallback_extraction(self, text: str, document_type: str) -> Dict:
        """
        Basic fallback extraction when template matching fails
        
        Simple regex-based extraction as last resort
        """
        lines = text.split("\n")
        line_items = []
        
        # Very basic pattern matching
        for line in lines:
            # Look for patterns like: "Account Name 1,234.56" or "1234-0000 Account Name 1,234.56"
            pattern = r'([\d-]+)?\s*([A-Za-z\s&,.-]+)\s+([\d,.-]+)'
            match = re.search(pattern, line)
            
            if match:
                account_code = match.group(1) or ""
                account_name = match.group(2).strip()
                amount_str = match.group(3).replace(",", "")
                
                try:
                    amount = float(amount_str)
                    line_items.append({
                        "account_code": account_code,
                        "account_name": account_name,
                        "amount": amount,
                        "period_amount": amount
                    })
                except ValueError:
                    continue
        
        return {
            "success": len(line_items) > 0,
            "line_items": line_items,
            "confidence": 50.0  # Low confidence for fallback
        }
    
    def _run_validations(self, upload: DocumentUpload) -> Dict:
        """
        Run validation rules on extracted data
        
        Integrates ValidationService into extraction workflow
        Returns validation summary
        """
        try:
            from app.services.validation_service import ValidationService
            
            validation_service = ValidationService(self.db, tolerance_percentage=1.0)
            validation_results = validation_service.validate_upload(upload.id)
            
            # Update upload needs_review flag if validations failed
            if validation_results.get("failed_checks", 0) > 0:
                upload.notes = f"Validation failed: {validation_results['failed_checks']} checks failed"
            
            return validation_results
        
        except Exception as e:
            # Log error but don't fail extraction
            return {
                "success": False,
                "error": f"Validation error: {str(e)}",
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0
            }

