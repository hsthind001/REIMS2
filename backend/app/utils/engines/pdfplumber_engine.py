import pdfplumber
from typing import Dict, List, Any
from decimal import Decimal
import io
from app.utils.engines.base_extractor import BaseExtractor, ExtractionResult


class PDFPlumberEngine(BaseExtractor):
    """PDFPlumber extraction engine - Excellent for tables and structured data"""
    
    def __init__(self):
        super().__init__(engine_name="pdfplumber")
        self.version = pdfplumber.__version__
    
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract data from PDF using PDFPlumber.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Optional parameters (extract_tables, extract_words_positions)
        
        Returns:
            ExtractionResult with text, tables, confidence scores, and metadata
        """
        self._start_timer()
        
        try:
            # Extract text
            text_result = self._extract_text_internal(pdf_data)
            
            if not text_result["success"]:
                return ExtractionResult(
                    engine_name=self.engine_name,
                    extracted_data={},
                    success=False,
                    error_message=text_result.get("error", "Unknown error"),
                    processing_time_ms=self._get_processing_time_ms()
                )
            
            # Extract tables (PDFPlumber's strength!)
            tables_result = None
            if kwargs.get("extract_tables", True):  # Default True for PDFPlumber
                tables_result = self._extract_tables_internal(pdf_data)
            
            # Extract word positions if requested
            words_result = None
            if kwargs.get("extract_word_positions", False):
                words_result = self._extract_words_with_positions_internal(pdf_data)
            
            # Prepare extracted data
            extracted_data = {
                "text": text_result["text"],
                "pages": text_result["pages"],
                "total_pages": text_result["total_pages"],
                "total_words": text_result["total_words"],
                "total_chars": text_result["total_chars"],
            }
            
            if tables_result and tables_result["success"]:
                extracted_data["tables"] = tables_result["tables"]
                extracted_data["total_tables"] = tables_result["total_tables"]
            
            if words_result and words_result["success"]:
                extracted_data["words"] = words_result["words"]
                extracted_data["total_words_positioned"] = words_result["total_words"]
            
            # Calculate confidence score
            confidence = self.calculate_confidence(extracted_data)
            
            # Calculate component scores
            text_quality = self._calculate_text_quality(
                text_result["text"],
                expected_min_length=100
            )
            
            table_confidence = None
            if tables_result and tables_result.get("tables"):
                # PDFPlumber excels at table detection
                table_confidence = self._calculate_table_confidence(
                    tables_result["tables"]
                )
            
            # Build confidence breakdown
            confidence_breakdown = {
                "text_quality": text_quality,
            }
            if table_confidence is not None:
                confidence_breakdown["table_detection"] = table_confidence
            
            # Prepare engine metadata
            engine_metadata = {
                "pdfplumber_version": self.version,
                "page_count": text_result["total_pages"],
                "table_count": tables_result["total_tables"] if tables_result else 0,
                "extraction_method": "layout_aware",
                "table_extraction": "native"  # PDFPlumber has native table support
            }
            
            # Add warnings if needed
            warnings = []
            if tables_result and tables_result["total_tables"] > 0:
                # High confidence for tables with PDFPlumber
                warnings.append(f"Detected {tables_result['total_tables']} tables - PDFPlumber's strength")
            
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data=extracted_data,
                success=True,
                confidence_score=confidence,
                confidence_breakdown=confidence_breakdown,
                processing_time_ms=self._get_processing_time_ms(),
                page_count=text_result["total_pages"],
                text_quality_score=text_quality,
                table_detection_score=table_confidence,
                engine_metadata=engine_metadata,
                warnings=warnings
            )
        
        except Exception as e:
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data={},
                success=False,
                error_message=str(e),
                processing_time_ms=self._get_processing_time_ms()
            )
    
    def calculate_confidence(self, extraction_data: Dict[str, Any]) -> Decimal:
        """
        Calculate confidence score for PDFPlumber extraction.
        
        PDFPlumber confidence is higher when tables are detected,
        as this is its primary strength.
        
        Args:
            extraction_data: Dictionary with extracted text and metadata
        
        Returns:
            Confidence score as Decimal (0.0 - 1.0)
        """
        text = extraction_data.get("text", "")
        total_pages = extraction_data.get("total_pages", 0)
        total_chars = extraction_data.get("total_chars", 0)
        tables = extraction_data.get("tables", [])
        
        # Calculate text quality
        text_quality = self._calculate_text_quality(text, expected_min_length=100)
        
        # Calculate table confidence (PDFPlumber's strength)
        table_confidence = None
        if tables and len(tables) > 0:
            table_confidence = self._calculate_table_confidence(tables)
        
        # Page coverage score
        if total_pages > 0:
            expected_chars = total_pages * 1000
            if total_chars >= expected_chars:
                page_coverage = 1.0
            else:
                page_coverage = min(total_chars / expected_chars, 1.0)
        else:
            page_coverage = 0.0
        
        # Character adequacy
        if total_chars < 50:
            char_adequacy = total_chars / 50.0
        else:
            char_adequacy = 1.0
        
        # Calculate aggregate confidence
        # For PDFPlumber, weight tables more heavily if detected
        if table_confidence is not None:
            # Tables detected - use higher weight for tables
            confidence = self._calculate_aggregate_confidence(
                text_confidence=text_quality,
                table_confidence=table_confidence,
                weights={'text': 0.3, 'table': 0.7, 'ocr': 0.0}  # Favor tables
            )
        else:
            # No tables - rely on text quality
            confidence = self._calculate_aggregate_confidence(
                text_confidence=text_quality,
                weights={'text': 1.0, 'table': 0.0, 'ocr': 0.0}
            )
        
        # Apply multipliers
        final_confidence = float(confidence) * page_coverage * char_adequacy
        
        return Decimal(str(round(final_confidence, 4)))
    
    # Legacy methods (kept for backwards compatibility)
    
    def extract_text(self, pdf_data: bytes) -> Dict:
        """
        Extract text from PDF (legacy method).
        
        NOTE: Use extract() method instead for new code.
        """
        return self._extract_text_internal(pdf_data)
    
    def extract_tables(self, pdf_data: bytes) -> Dict:
        """
        Extract tables from PDF (legacy method).
        
        NOTE: Use extract() method instead for new code.
        """
        return self._extract_tables_internal(pdf_data)
    
    def extract_words_with_positions(self, pdf_data: bytes) -> Dict:
        """
        Extract words with positioning (legacy method).
        
        NOTE: Use extract() method with extract_word_positions=True instead.
        """
        return self._extract_words_with_positions_internal(pdf_data)
    
    # Internal implementation methods
    
    def _extract_text_internal(self, pdf_data: bytes) -> Dict:
        """Internal text extraction implementation"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            pages = []
            all_text = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                
                pages.append({
                    "page": page_num,
                    "text": text,
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "width": page.width,
                    "height": page.height
                })
                
                all_text.append(text)
            
            full_text = "\n\n".join(all_text)
            
            pdf.close()
            
            return {
                "engine": self.engine_name,
                "text": full_text,
                "pages": pages,
                "total_pages": len(pages),
                "total_words": len(full_text.split()),
                "total_chars": len(full_text),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.engine_name,
                "text": "",
                "pages": [],
                "total_pages": 0,
                "success": False,
                "error": str(e)
            }
    
    def _extract_tables_internal(self, pdf_data: bytes) -> Dict:
        """Internal table extraction implementation"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            all_tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                for table_index, table in enumerate(tables, 1):
                    if table:
                        # Convert table to dict format with headers
                        headers = table[0] if table else []
                        rows = table[1:] if len(table) > 1 else []
                        
                        table_dict = {
                            "page": page_num,
                            "table_index": table_index,
                            "headers": headers,
                            "rows": rows,
                            "row_count": len(table),
                            "column_count": len(table[0]) if table else 0,
                            "data": table  # Full raw data
                        }
                        all_tables.append(table_dict)
            
            pdf.close()
            
            return {
                "engine": self.engine_name,
                "tables": all_tables,
                "total_tables": len(all_tables),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.engine_name,
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def _extract_words_with_positions_internal(self, pdf_data: bytes) -> Dict:
        """Internal word position extraction implementation"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            all_words = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words()
                
                for word in words:
                    all_words.append({
                        "page": page_num,
                        "text": word.get("text", ""),
                        "x0": word.get("x0", 0),
                        "y0": word.get("y0", 0),
                        "x1": word.get("x1", 0),
                        "y1": word.get("y1", 0),
                        "top": word.get("top", 0),
                        "bottom": word.get("bottom", 0)
                    })
            
            pdf.close()
            
            return {
                "engine": self.engine_name,
                "words": all_words,
                "total_words": len(all_words),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.engine_name,
                "words": [],
                "total_words": 0,
                "success": False,
                "error": str(e)
            }
