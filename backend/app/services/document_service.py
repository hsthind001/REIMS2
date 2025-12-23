"""
Document Service - Business logic for document upload workflow
"""
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import hashlib
import os

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.db.minio_client import upload_file, get_minio_client
from app.core.config import settings
from app.services.document_type_detector import DocumentTypeDetector
# Lazy import to avoid circular dependency
# from app.tasks.extraction_tasks import extract_document


# Property name mapping for MinIO folder structure
PROPERTY_NAME_MAPPING = {
    'ESP001': 'Eastern-Shore-Plaza',
    'HMND001': 'Hammond-Aire',
    'TCSH001': 'The-Crossings',
    'WEND001': 'Wendover-Commons'
}


class DocumentService:
    """Handle document upload workflow and storage"""
    
    def __init__(self, db: Session):
        self.db = db
        self.minio_client = get_minio_client()
    
    async def upload_document(
        self,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str,
        file: UploadFile,
        uploaded_by: Optional[int] = None,
        force_overwrite: bool = False
    ) -> Dict:
        """
        Complete document upload workflow
        
        Steps:
        1. Validate property exists
        2. Get/create financial period
        3. Calculate file hash for deduplication
        4. Check for duplicate uploads
        5. Upload to MinIO
        6. Create DocumentUpload record
        
        Args:
            property_code: Property code (e.g., WEND001)
            period_year: Financial period year
            period_month: Financial period month (1-12)
            document_type: Type of document (balance_sheet, income_statement, etc.)
            file: Uploaded PDF file
            uploaded_by: User ID (optional)
        
        Returns:
            dict: Upload result with upload_id and file_path
        
        Raises:
            HTTPException: If validation fails or upload errors occur
        """
        # Step 1: Validate property exists
        property_obj = self.get_property_by_code(property_code)
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_code}' not found"
            )
        
        # Step 2: Get or create period
        period = self.get_or_create_period(
            property_obj.id,
            period_year,
            period_month
        )
        
        # Step 3: Read file and calculate hash
        file_content = await file.read()
        file_hash = self.calculate_file_hash(file_content)
        file_size = len(file_content)
        
        # Step 3.5: Intelligent document validation (property, type, year)
        print(f"🔍 Validating property, document type, and year from PDF content...")
        from app.utils.extraction_engine import MultiEngineExtractor
        detector = MultiEngineExtractor()
        
        # Get all properties for property detection
        all_properties = self.db.query(Property).all()
        available_props = [{
            'property_code': p.property_code,
            'property_name': p.property_name,
            'city': p.city
        } for p in all_properties]
        
        # Detect property
        property_detection = detector.detect_property_name(file_content, available_props)
        detected_property_code = property_detection.get("detected_property_code")
        property_confidence = property_detection.get("confidence", 0)
        
        # Property validation DISABLED - caused false positives with A/R cross-references
        # Financial documents often reference multiple properties in A/R accounts
        # This was incorrectly flagging valid documents
        # Users should ensure they select correct property manually
        
        print(f"ℹ️  Property detected: {detected_property_code or 'N/A'} (confidence: {property_confidence}%) - validation disabled")
        
        # Detect document type
        type_detection = detector.detect_document_type(file_content)
        detected_type = type_detection.get("detected_type", "unknown")
        type_confidence = type_detection.get("confidence", 0)
        
        # Detect year and period
        period_detection = detector.detect_year_and_period(file_content)
        detected_year = period_detection.get("year")
        detected_month = period_detection.get("month")
        period_confidence = period_detection.get("confidence", 0)
        
        # Check document type mismatch
        # Only flag mismatch if confidence is high enough (>= 50%) to avoid false positives
        # Lower confidence detections are often incorrect, especially for cash flow vs income statement
        if detected_type != "unknown" and detected_type != document_type and type_confidence >= 50:
            type_names = {
                "balance_sheet": "Balance Sheet",
                "income_statement": "Income Statement",
                "cash_flow": "Cash Flow Statement",
                "rent_roll": "Rent Roll"
            }
            
            print(f"⚠️  Document type mismatch detected!")
            print(f"   Selected: {document_type} | Detected: {detected_type} (confidence: {type_confidence}%)")
            
            return {
                "type_mismatch": True,
                "selected_type": document_type,
                "detected_type": detected_type,
                "confidence": type_confidence,
                "keywords_found": type_detection.get("keywords_found", []),
                "message": f"Document type mismatch! You selected '{type_names.get(document_type, document_type)}' but the PDF appears to be a '{type_names.get(detected_type, detected_type)}' (confidence: {type_confidence}%)."
            }
        
        # Check year mismatch
        # SKIP for rent_roll: contains future lease dates that interfere with year detection
        # The year detection now prioritizes "From Date" for rent roll, but still skip warnings
        # to avoid false positives from lease expiration dates in the data
        if (document_type != "rent_roll" and 
            detected_year and detected_year != period_year and period_confidence >= 50):
            print(f"⚠️  Year mismatch detected!")
            print(f"   Selected: {period_year} | Detected: {detected_year} (confidence: {period_confidence}%)")
            
            return {
                "year_mismatch": True,
                "selected_year": period_year,
                "detected_year": detected_year,
                "period_text": period_detection.get("period_text", ""),
                "confidence": period_confidence,
                "message": f"Year mismatch! You selected {period_year} but the PDF appears to be for {detected_year}. Period found: {period_detection.get('period_text', 'unknown')}"
            }
        
        # Month validation DISABLED per user request
        # Users can select any month - only year and type are validated
        
        print(f"✅ Document validated: {detected_type} | Year: {detected_year or 'N/A'} | Month: {detected_month or 'N/A'} (month check disabled)")
        
        # Step 4: Check for duplicate and auto-replace
        existing_upload = self.check_duplicate(
            property_obj.id,
            period.id,
            document_type,
            file_hash
        )
        if existing_upload:
            # Auto-replace: Delete old upload (cascade deletes all related data)
            print(f"🔄 Duplicate detected (ID {existing_upload.id}). Auto-replacing with new upload...")
            
            # Delete old file from MinIO if exists
            if existing_upload.file_path:
                try:
                    from app.db.minio_client import delete_file
                    delete_file(existing_upload.file_path, settings.MINIO_BUCKET_NAME)
                    print(f"🗑️  Deleted old file from MinIO: {existing_upload.file_path}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not delete old file from MinIO: {e}")
            
            # Delete old database record (cascades to all related financial data)
            self.db.delete(existing_upload)
            self.db.commit()
            print(f"✅ Old upload deleted. Proceeding with new upload...")
        
        # Step 5: Generate file path and check if exists
        file_path = await self.generate_file_path(
            property_obj,
            period_year,
            document_type,
            file.filename,
            period_month=period_month
        )
        
        # Check if file already exists at this path (not hash duplicate)
        if not force_overwrite:
            existing_file = self.check_file_exists(file_path)
            if existing_file:
                return {
                    "file_exists": True,
                    "existing_file": existing_file,
                    "message": "File already exists at this location",
                    "requires_confirmation": True
                }
        
        # Upload to MinIO
        print(f"📤 Uploading to MinIO: {file_path}")
        success = upload_file(
            file_data=file_content,
            object_name=file_path,
            content_type="application/pdf",
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        print(f"✅ File uploaded to MinIO successfully")
        
        # Step 6: Create document_uploads record with status: uploaded_to_minio
        upload = DocumentUpload(
            property_id=property_obj.id,
            period_id=period.id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            uploaded_by=uploaded_by,
            extraction_status='uploaded_to_minio',  # Granular status
            version=self._get_next_version(property_obj.id, period.id, document_type),
            is_active=True
        )
        
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        
        # Step 7: Automatically trigger extraction with error handling
        try:
            from app.tasks.extraction_tasks import extract_document
            task = extract_document.delay(upload.id)
            upload.extraction_status = 'pending'
            upload.extraction_task_id = task.id
            self.db.commit()
            print(f"✅ Extraction task queued: task_id={task.id} for upload_id={upload.id}")
        except Exception as e:
            # If Celery unavailable, mark for background processing
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to queue extraction for upload_id={upload.id}: {e}")
            upload.extraction_status = 'pending'  # Will be picked up by background task
            upload.notes = f"Extraction queuing failed, will retry: {str(e)}"
            self.db.commit()
            print(f"⚠️  Extraction queuing failed for upload_id={upload.id}, will be recovered by background task")
        
        return {
            "is_duplicate": False,
            "upload_id": upload.id,
            "file_path": file_path,
            "message": "Document uploaded successfully"
        }
    
    def get_property_by_code(self, property_code: str) -> Optional[Property]:
        """
        Get property by code or ID.
        
        Intelligently handles both property_code (e.g., "WEND001") and numeric ID.
        """
        # Try as property_code first
        property_obj = self.db.query(Property).filter(
            Property.property_code == property_code
        ).first()
        
        # If not found and looks like a numeric ID, try as ID
        if not property_obj and property_code.isdigit():
            try:
                property_id = int(property_code)
                property_obj = self.db.query(Property).filter(
                    Property.id == property_id
                ).first()
            except ValueError:
                pass
        
        return property_obj
    
    def get_or_create_period(
        self,
        property_id: int,
        period_year: int,
        period_month: int
    ) -> FinancialPeriod:
        """
        Get existing period or create new one
        
        Args:
            property_id: Property ID
            period_year: Year (e.g., 2024)
            period_month: Month (1-12)
        
        Returns:
            FinancialPeriod: Existing or newly created period
        """
        # Try to find existing period
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == period_year,
            FinancialPeriod.period_month == period_month
        ).first()
        
        if period:
            return period
        
        # Create new period
        period_start_date = date(period_year, period_month, 1)
        
        # Calculate end date (last day of month)
        if period_month == 12:
            period_end_date = date(period_year, 12, 31)
        else:
            # First day of next month minus one day
            from calendar import monthrange
            last_day = monthrange(period_year, period_month)[1]
            period_end_date = date(period_year, period_month, last_day)
        
        # Calculate fiscal quarter
        fiscal_quarter = ((period_month - 1) // 3) + 1
        
        period = FinancialPeriod(
            property_id=property_id,
            period_year=period_year,
            period_month=period_month,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            fiscal_year=period_year,
            fiscal_quarter=fiscal_quarter,
            is_closed=False
        )
        
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        
        return period
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate MD5 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def check_duplicate(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        file_hash: str
    ) -> Optional[DocumentUpload]:
        """
        Check if duplicate file already exists
        
        Checks for same property, period, document type, and file hash
        """
        return self.db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.document_type == document_type,
            DocumentUpload.file_hash == file_hash,
            DocumentUpload.is_active == True
        ).first()
    
    async def generate_file_path(
        self,
        property_obj: Property,
        period_year: int,
        document_type: str,
        original_filename: str,
        period_month: Optional[int] = None
    ) -> str:
        """
        Generate MinIO file path using new organized structure
        
        Path format: {property_code}-{property_name}/{year}/{doc_type}/{filename}
        Example: ESP001-Eastern-Shore-Plaza/2025/balance-sheet/ESP_2025_12_Balance_Sheet.pdf
        Example (no month): ESP001-Eastern-Shore-Plaza/2025/balance-sheet/ESP_2025_Balance_Sheet.pdf
        
        Args:
            property_obj: Property object (includes code and name)
            period_year: Year
            document_type: Document type
            original_filename: Original filename (preserves extension)
            period_month: Month (optional, defaults to 1 if not provided)
        
        Returns:
            str: Standardized file path for MinIO
        """
        # Default month to 1 if not provided
        if period_month is None:
            period_month = 1
        
        # Get property folder name
        property_code = property_obj.property_code
        prop_folder = PROPERTY_NAME_MAPPING.get(property_code, property_obj.property_name.replace(' ', '-'))
        
        # Map document types to folder names (with hyphens)
        doc_type_folders = {
            'balance_sheet': 'balance-sheet',
            'income_statement': 'income-statement',
            'cash_flow': 'cash-flow',
            'rent_roll': 'rent-roll',
            'mortgage_statement': 'mortgage-statement'
        }
        doc_folder = doc_type_folders.get(document_type, document_type)
        
        # Get file extension from original filename
        import os
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.pdf'  # Default to PDF if no extension
        
        # Generate standardized filename
        prop_abbr = property_code[:property_code.find('0')] if '0' in property_code else property_code[:4]

        # Get month name for all document types to ensure unique filenames
        month_name = datetime(period_year, period_month, 1).strftime('%B')

        # Format filename with month to prevent overwrites
        if document_type == 'rent_roll':
            filename = f"{prop_abbr}_{period_year}_Rent_Roll_{month_name}{ext}"
        else:
            doc_type_map = {
                'balance_sheet': 'Balance_Sheet',
                'income_statement': 'Income_Statement',
                'cash_flow': 'Cash_Flow_Statement',
                'mortgage_statement': 'Mortgage_Statement'
            }
            type_name = doc_type_map.get(document_type, document_type)
            # Include month in filename to avoid overwrites (month number format: 01-12)
            month_num = f"{period_month:02d}"
            filename = f"{prop_abbr}_{period_year}_{month_num}_{type_name}{ext}"
        
        # Build structured path
        file_path = f"{property_code}-{prop_folder}/{period_year}/{doc_folder}/{filename}"
        
        return file_path
    
    def check_file_exists(self, file_path: str) -> Optional[Dict]:
        """
        Check if file already exists in MinIO at the given path
        
        Args:
            file_path: MinIO object path to check
        
        Returns:
            dict with file info if exists, None if not found
        """
        try:
            stat = self.minio_client.stat_object(settings.MINIO_BUCKET_NAME, file_path)
            return {
                'exists': True,
                'path': file_path,
                'size': stat.size,
                'last_modified': stat.last_modified.isoformat(),
                'etag': stat.etag
            }
        except:
            return None
    
    def _get_next_version(
        self,
        property_id: int,
        period_id: int,
        document_type: str
    ) -> int:
        """Get next version number for document type in this period"""
        max_version = self.db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.document_type == document_type
        ).count()
        
        return max_version + 1
    
    def get_upload_by_id(self, upload_id: int) -> Optional[DocumentUpload]:
        """Get upload by ID"""
        return self.db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
    
    def update_extraction_status(
        self,
        upload_id: int,
        status: str,
        extraction_id: Optional[int] = None
    ):
        """Update extraction status for an upload"""
        upload = self.get_upload_by_id(upload_id)
        if not upload:
            return False
        
        upload.extraction_status = status
        
        if status == "processing":
            upload.extraction_started_at = datetime.now()
        elif status in ["completed", "failed"]:
            upload.extraction_completed_at = datetime.now()
        
        if extraction_id:
            upload.extraction_id = extraction_id
        
        self.db.commit()
        return True
    
    def _validate_file_format(self, file: UploadFile) -> Dict[str, Any]:
        """
        Validate file format and return file type.
        
        Returns:
            {
                "valid": bool,
                "file_type": "pdf" | "csv" | "excel" | "doc" | None,
                "error": str | None
            }
        """
        filename_lower = file.filename.lower() if file.filename else ""
        content_type = file.content_type or ""
        
        # Check by extension
        if filename_lower.endswith('.pdf'):
            return {"valid": True, "file_type": "pdf", "error": None}
        elif filename_lower.endswith(('.csv',)):
            return {"valid": True, "file_type": "csv", "error": None}
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return {"valid": True, "file_type": "excel", "error": None}
        elif filename_lower.endswith(('.doc', '.docx')):
            return {"valid": True, "file_type": "doc", "error": None}
        
        # Check by content type
        if 'pdf' in content_type:
            return {"valid": True, "file_type": "pdf", "error": None}
        elif 'csv' in content_type or 'text/csv' in content_type:
            return {"valid": True, "file_type": "csv", "error": None}
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return {"valid": True, "file_type": "excel", "error": None}
        elif 'msword' in content_type or 'wordprocessingml' in content_type:
            return {"valid": True, "file_type": "doc", "error": None}
        
        return {
            "valid": False,
            "file_type": None,
            "error": f"Unsupported file format. Supported: PDF, CSV, Excel (.xlsx, .xls), DOC (.doc, .docx)"
        }
    
    async def bulk_upload_documents(
        self,
        property_code: str,
        year: int,
        files: List[UploadFile],
        uploaded_by: Optional[int] = None,
        duplicate_strategy: str = "skip"
    ) -> Dict:
        """
        Bulk upload multiple documents for a year with intelligent duplicate handling.

        For each file:
        1. Detect document type from filename
        2. Detect month from filename (or default to 1)
        3. Validate file format
        4. Check for duplicates and apply strategy
        5. Generate MinIO path
        6. Upload to MinIO
        7. Create DocumentUpload record
        8. Queue extraction/import task

        Args:
            property_code: Property code (e.g., WEND001)
            year: Year for all documents
            files: List of files to upload
            uploaded_by: User ID (optional)
            duplicate_strategy: How to handle duplicates:
                - "skip": Skip files that already exist (default)
                - "replace": Replace existing files with new ones
                - "version": Create new version (keep both)

        Returns:
            {
                "success": bool,
                "total_files": int,
                "uploaded": int,
                "skipped": int,
                "replaced": int,
                "failed": int,
                "duplicates_found": int,
                "results": [
                    {
                        "filename": str,
                        "document_type": str,
                        "month": int | None,
                        "file_type": str,
                        "status": "success" | "skipped" | "replaced" | "failed",
                        "upload_id": int | None,
                        "file_path": str | None,
                        "error": str | None,
                        "message": str | None
                    }
                ]
            }
        """
        detector = DocumentTypeDetector()
        results = []
        uploaded_count = 0
        skipped_count = 0
        replaced_count = 0
        failed_count = 0
        duplicates_found = 0

        # Validate duplicate_strategy
        valid_strategies = ["skip", "replace", "version"]
        if duplicate_strategy not in valid_strategies:
            return {
                "success": False,
                "total_files": len(files),
                "uploaded": 0,
                "skipped": 0,
                "replaced": 0,
                "failed": len(files),
                "duplicates_found": 0,
                "error": f"Invalid duplicate_strategy '{duplicate_strategy}'. Valid options: {', '.join(valid_strategies)}",
                "results": []
            }

        # Validate property exists
        property_obj = self.get_property_by_code(property_code)
        if not property_obj:
            return {
                "success": False,
                "total_files": len(files),
                "uploaded": 0,
                "skipped": 0,
                "replaced": 0,
                "failed": len(files),
                "duplicates_found": 0,
                "error": f"Property '{property_code}' not found",
                "results": []
            }
        
        for file in files:
            result = {
                "filename": file.filename or "unknown",
                "document_type": "unknown",
                "month": None,
                "file_type": None,
                "status": "failed",
                "upload_id": None,
                "file_path": None,
                "error": None
            }
            
            try:
                # Step 1: Validate file format
                format_validation = self._validate_file_format(file)
                if not format_validation["valid"]:
                    result["error"] = format_validation["error"]
                    results.append(result)
                    failed_count += 1
                    continue
                
                result["file_type"] = format_validation["file_type"]
                
                # Step 2: Detect document type from filename
                type_detection = detector.detect_from_filename(file.filename or "")
                detected_type = type_detection.get("document_type", "unknown")
                
                if detected_type == "unknown":
                    result["error"] = "Could not detect document type from filename"
                    results.append(result)
                    failed_count += 1
                    continue
                
                result["document_type"] = detected_type
                
                # Step 2.5: Pre-flight check for known issues
                try:
                    from app.services.preflight_check_service import PreflightCheckService
                    preflight_service = PreflightCheckService(self.db)
                    preflight_result = preflight_service.check_before_upload(
                        document_type=detected_type,
                        property_code=property_code,
                        filename=file.filename,
                        file_size=None,  # Will be available after reading
                        context={"year": year}
                    )
                    
                    # Apply auto-fixes
                    if preflight_result.get("auto_fixes"):
                        for auto_fix in preflight_result["auto_fixes"]:
                            if auto_fix.get("type") == "skip_validation":
                                # Skip specific validation
                                print(f"ℹ️  Auto-fix: Skipping {auto_fix.get('validation_rule')} based on learned pattern")
                    
                    # Log warnings
                    if preflight_result.get("warnings"):
                        for warning in preflight_result["warnings"]:
                            print(f"⚠️  Pre-flight warning: {warning}")
                except Exception as e:
                    print(f"⚠️  Pre-flight check failed: {e}")
                
                # Step 3: Detect month from filename (initial guess)
                filename_month = detector.detect_month_from_filename(file.filename or "", year)
                
                # Step 4: Read file content early to detect month from PDF for mortgage statements
                file_content = await file.read()
                file.file.seek(0)  # Reset for potential reuse

                # Step 5: INTELLIGENT PDF CONTENT ANALYSIS (if PDF)
                # For mortgage statements, prioritize statement date over filename date
                anomalies = []
                pdf_detected_type = None
                pdf_detected_year = None
                pdf_detected_month = None
                pdf_period_confidence = 0

                if format_validation["file_type"] == "pdf":
                    try:
                        from app.utils.extraction_engine import MultiEngineExtractor
                        content_detector = MultiEngineExtractor()

                        # Detect document type from PDF content
                        pdf_type_detection = content_detector.detect_document_type(file_content)
                        pdf_detected_type = pdf_type_detection.get("detected_type")
                        pdf_type_confidence = pdf_type_detection.get("confidence", 0)

                        # Detect year and period from PDF content
                        pdf_period_detection = content_detector.detect_year_and_period(file_content)
                        pdf_detected_year = pdf_period_detection.get("year")
                        pdf_detected_month = pdf_period_detection.get("month")
                        pdf_period_confidence = pdf_period_detection.get("confidence", 0)
                        
                        # For mortgage statements, prioritize statement date over filename
                        # Statement date is the actual document period, filename date might be generation date
                        # Also prioritize statement date for other documents if found with high confidence (>= 70%)
                        if pdf_detected_month and pdf_period_confidence >= 50:
                            # Always use statement date for mortgage statements
                            # For other documents, use if confidence is very high (>= 70%)
                            if detected_type == "mortgage_statement" or pdf_period_confidence >= 70:
                                detected_month = pdf_detected_month
                                if detected_type == "mortgage_statement":
                                    print(f"✅ Using PDF statement date for mortgage statement: month {detected_month} (confidence: {pdf_period_confidence}%)")
                                else:
                                    print(f"✅ Using PDF statement date: month {detected_month} (confidence: {pdf_period_confidence}%)")
                            elif filename_month is None:
                                # Use PDF month if no filename month detected
                                detected_month = pdf_detected_month
                        elif filename_month is not None:
                            detected_month = filename_month
                        else:
                            detected_month = 1  # Default to January

                        # ANOMALY DETECTION: Compare filename vs PDF content
                        # Type mismatch - only flag if confidence is high (>= 50%) to avoid false positives
                        # Cash flow statements often contain income/expense keywords that can be misclassified
                        if pdf_detected_type and pdf_detected_type != detected_type and pdf_type_confidence >= 50:
                            anomaly_msg = f"Document type mismatch: Filename suggests '{detected_type}' but PDF content indicates '{pdf_detected_type}' (confidence: {pdf_type_confidence}%)"
                            anomalies.append(anomaly_msg)
                            
                            # Capture issue for learning (will update upload_id after upload is created)
                            # Store for later capture
                            pass  # Will capture after upload_id is available

                        # Year mismatch - SKIP for rent_roll to avoid false positives from lease dates
                        if (detected_type != "rent_roll" and 
                            pdf_detected_year and pdf_detected_year != year):
                            anomalies.append(f"Year mismatch: Expected {year} but PDF content shows {pdf_detected_year}")

                        # Month mismatch - only flag if confidence is high and not already corrected
                        # For mortgage statements, we already use statement date, so skip this warning
                        # For other documents, only warn if confidence is high (>= 50%) to avoid false positives
                        if (detected_type != "mortgage_statement" and 
                            filename_month is not None and
                            pdf_detected_month and 
                            pdf_detected_month != filename_month and 
                            pdf_period_confidence >= 50):
                            anomaly_msg = f"Month mismatch: Filename suggests month {filename_month} but PDF content indicates month {pdf_detected_month} (confidence: {pdf_period_confidence}%)"
                            anomalies.append(anomaly_msg)
                            
                            # Capture issue for learning
                            try:
                                from app.services.issue_capture_service import IssueCaptureService
                                capture_service = IssueCaptureService(self.db)
                                capture_service.capture_validation_issue(
                                    validation_type="month_mismatch",
                                    expected_value=filename_month,
                                    detected_value=pdf_detected_month,
                                    confidence=pdf_period_confidence,
                                    upload_id=None,  # Will be set after upload is created
                                    document_type=detected_type,
                                    property_id=property_obj.id,
                                    period_id=period.id if period else None,
                                    context={
                                        "filename": file.filename,
                                        "detected_type": detected_type,
                                        "expected_type": detected_type
                                    }
                                )
                            except Exception as e:
                                print(f"⚠️  Failed to capture issue: {e}")

                        # Use PDF content detection if higher confidence
                        if pdf_detected_type and pdf_type_confidence > 60:
                            detected_type = pdf_detected_type
                            result["document_type"] = detected_type
                            print(f"✅ Using PDF content detection for type: {detected_type} (confidence: {pdf_type_confidence}%)")

                        # For non-mortgage documents, use PDF content if confidence is high
                        # (Mortgage statements already handled above)
                        if (detected_type != "mortgage_statement" and 
                            pdf_detected_month and 
                            pdf_period_confidence > 50):
                            detected_month = pdf_detected_month
                            result["month"] = detected_month
                            print(f"✅ Using PDF content detection for month: {detected_month} (confidence: {pdf_period_confidence}%)")

                        # Add anomalies to result
                        if anomalies:
                            result["anomalies"] = anomalies
                            result["warning"] = " | ".join(anomalies)
                            print(f"⚠️  Anomalies detected for {file.filename}: {anomalies}")

                    except Exception as e:
                        print(f"⚠️  PDF content analysis failed for {file.filename}: {e}")
                        # Continue with filename-based detection
                        if detected_month is None:
                            if filename_month is not None:
                                detected_month = filename_month
                            else:
                                detected_month = 1  # Default to January
                
                # Set final month in result (if not already set)
                if detected_month is None:
                    if filename_month is not None:
                        detected_month = filename_month
                    else:
                        detected_month = 1  # Default to January
                
                result["month"] = detected_month
                
                # Step 6: Get or create period (after month is finalized)
                period = self.get_or_create_period(
                    property_obj.id,
                    year,
                    detected_month
                )

                # Step 7: Calculate file hash
                file_hash = hashlib.md5(file_content).hexdigest()

                # Step 7: Intelligent duplicate handling with strategy
                # Check for exact duplicate (same file hash)
                duplicate_by_hash = self.check_duplicate(
                    property_obj.id,
                    period.id,
                    detected_type,
                    file_hash
                )

                # Check for existing upload for same property/period/type (any version)
                existing_upload = self.db.query(DocumentUpload).filter(
                    DocumentUpload.property_id == property_obj.id,
                    DocumentUpload.period_id == period.id,
                    DocumentUpload.document_type == detected_type,
                    DocumentUpload.is_active == True
                ).order_by(DocumentUpload.version.desc()).first()

                # Handle duplicate scenarios based on strategy
                if duplicate_by_hash:
                    # Exact same file (same hash) - always skip
                    duplicates_found += 1
                    result["status"] = "skipped"
                    result["upload_id"] = duplicate_by_hash.id
                    result["message"] = f"Identical file already exists (upload_id: {duplicate_by_hash.id})"
                    results.append(result)
                    skipped_count += 1
                    continue

                elif existing_upload:
                    # Different file for same property/period/type
                    duplicates_found += 1

                    if duplicate_strategy == "skip":
                        # Skip this upload
                        result["status"] = "skipped"
                        result["upload_id"] = existing_upload.id
                        result["message"] = f"Document already exists (upload_id: {existing_upload.id}). Use 'replace' strategy to overwrite."
                        results.append(result)
                        skipped_count += 1
                        continue

                    elif duplicate_strategy == "replace":
                        # Replace existing upload
                        try:
                            from app.db.minio_client import delete_file
                            # Delete old file from MinIO
                            if existing_upload.file_path:
                                try:
                                    delete_file(existing_upload.file_path, settings.MINIO_BUCKET_NAME)
                                except Exception as e:
                                    print(f"⚠️  Warning: Could not delete old MinIO file: {e}")

                            old_upload_id = existing_upload.id
                            # Delete associated data (cascades via relationships)
                            self.db.delete(existing_upload)
                            self.db.commit()
                            print(f"✅ Replacing existing upload (id: {old_upload_id}) with new file")
                            # Continue with upload - will mark as "replaced" later

                        except Exception as e:
                            result["error"] = f"Failed to replace existing upload: {str(e)}"
                            result["status"] = "failed"
                            results.append(result)
                            failed_count += 1
                            continue

                    elif duplicate_strategy == "version":
                        # Create new version (not implemented yet - future enhancement)
                        result["error"] = "Version strategy not yet implemented. Use 'skip' or 'replace'."
                        result["status"] = "failed"
                        results.append(result)
                        failed_count += 1
                        continue
                
                # Step 8: Generate file path
                file_path = await self.generate_file_path(
                    property_obj,
                    year,
                    detected_type,
                    file.filename or "document",
                    period_month=detected_month
                )
                
                # Step 9: Determine content type
                content_type_map = {
                    "pdf": "application/pdf",
                    "csv": "text/csv",
                    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "doc": "application/msword"
                }
                content_type = content_type_map.get(format_validation["file_type"], "application/octet-stream")
                
                # Step 10: Upload to MinIO
                upload_success = upload_file(
                    file_data=file_content,
                    object_name=file_path,
                    content_type=content_type,
                    bucket_name=settings.MINIO_BUCKET_NAME
                )
                
                if not upload_success:
                    result["error"] = "Failed to upload file to MinIO"
                    results.append(result)
                    failed_count += 1
                    continue
                
                # Step 11: Create DocumentUpload record
                upload_record = DocumentUpload(
                    property_id=property_obj.id,
                    period_id=period.id,
                    document_type=detected_type,
                    file_name=file.filename or "unknown",
                    file_path=file_path,
                    file_hash=file_hash,
                    file_size_bytes=len(file_content),
                    uploaded_by=uploaded_by,
                    upload_date=datetime.now(),
                    extraction_status='uploaded_to_minio'
                )
                
                self.db.add(upload_record)
                self.db.commit()
                self.db.refresh(upload_record)
                
                result["upload_id"] = upload_record.id
                result["file_path"] = file_path

                # Mark as replaced if we deleted an existing upload
                if existing_upload and duplicate_strategy == "replace":
                    result["status"] = "replaced"
                    result["message"] = f"Replaced existing document (old upload_id: {old_upload_id})"
                    replaced_count += 1
                else:
                    result["status"] = "success"
                    uploaded_count += 1

                # Step 12: Queue extraction/import task
                try:
                    if format_validation["file_type"] in ["pdf", "doc"]:
                        # Queue extraction task for PDF/DOC
                        from app.tasks.extraction_tasks import extract_document
                        task = extract_document.delay(upload_record.id)
                        upload_record.extraction_status = 'pending'
                        upload_record.extraction_task_id = task.id
                    elif format_validation["file_type"] in ["csv", "excel"]:
                        # For CSV/Excel, mark as ready for import
                        # The bulk import service will handle these
                        upload_record.extraction_status = 'pending'
                    self.db.commit()
                except Exception as e:
                    print(f"⚠️  Warning: Failed to queue extraction task: {e}")
                    upload_record.extraction_status = 'pending'
                    upload_record.notes = f"Extraction queuing failed, will retry: {str(e)}"
                    self.db.commit()
                
            except Exception as e:
                result["error"] = str(e)
                failed_count += 1
                print(f"❌ Error processing file {file.filename}: {e}")
            
            results.append(result)
        
        return {
            "success": (uploaded_count + replaced_count + skipped_count) > 0,
            "total_files": len(files),
            "uploaded": uploaded_count,
            "skipped": skipped_count,
            "replaced": replaced_count,
            "failed": failed_count,
            "duplicates_found": duplicates_found,
            "duplicate_strategy": duplicate_strategy,
            "results": results
        }

