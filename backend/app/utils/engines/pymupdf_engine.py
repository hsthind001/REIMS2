import fitz
from typing import Dict, List, Any
from decimal import Decimal
from app.utils.engines.base_extractor import BaseExtractor, ExtractionResult


class PyMuPDFEngine(BaseExtractor):
    """PyMuPDF extraction engine - Fast and reliable for digital PDFs"""
    
    def __init__(self):
        super().__init__(engine_name="pymupdf")
        self.version = fitz.VersionBind
    
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract data from PDF using PyMuPDF.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Optional parameters (extract_tables, extract_metadata)
        
        Returns:
            ExtractionResult with text, confidence scores, and metadata
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
            
            # Extract tables if requested
            tables_result = None
            if kwargs.get("extract_tables", False):
                tables_result = self._extract_tables_internal(pdf_data)
            
            # Extract metadata if requested
            metadata = None
            if kwargs.get("extract_metadata", True):
                metadata = self._get_metadata_internal(pdf_data)
            
            # Prepare extracted data
            extracted_data = {
                "text": text_result["text"],
                "pages": text_result["pages"],
                "total_pages": text_result["total_pages"],
                "total_words": text_result["total_words"],
                "total_chars": text_result["total_chars"],
            }
            
            if tables_result:
                extracted_data["tables"] = tables_result["tables"]
                extracted_data["total_tables"] = tables_result["total_tables"]
            
            if metadata:
                extracted_data["metadata"] = metadata
            
            # Calculate confidence score
            confidence = self.calculate_confidence(extracted_data)
            
            # Calculate component scores
            text_quality = self._calculate_text_quality(
                text_result["text"],
                expected_min_length=100
            )
            
            table_confidence = None
            if tables_result and tables_result.get("tables"):
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
                "pymupdf_version": self.version,
                "page_count": text_result["total_pages"],
                "extraction_method": "digital" if text_result["total_chars"] > 0 else "ocr_needed"
            }
            
            if metadata:
                engine_metadata.update({
                    "pdf_title": metadata.get("title", ""),
                    "pdf_author": metadata.get("author", ""),
                    "is_encrypted": metadata.get("is_encrypted", False)
                })
            
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
                engine_metadata=engine_metadata
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
        Calculate confidence score for PyMuPDF extraction.
        
        Confidence is based on:
        - Text quality (presence, length, coherence)
        - Character/word count adequacy
        - Page coverage
        
        Args:
            extraction_data: Dictionary with extracted text and metadata
        
        Returns:
            Confidence score as Decimal (0.0 - 1.0)
        """
        text = extraction_data.get("text", "")
        total_pages = extraction_data.get("total_pages", 0)
        total_chars = extraction_data.get("total_chars", 0)
        
        # Calculate text quality
        text_quality = self._calculate_text_quality(text, expected_min_length=100)
        
        # Page coverage score (assumes ~1000 chars per page minimum)
        if total_pages > 0:
            expected_chars = total_pages * 1000
            if total_chars >= expected_chars:
                page_coverage = 1.0
            else:
                page_coverage = min(total_chars / expected_chars, 1.0)
        else:
            page_coverage = 0.0
        
        # Character adequacy (minimum 50 characters for valid extraction)
        if total_chars < 50:
            char_adequacy = total_chars / 50.0
        else:
            char_adequacy = 1.0
        
        # Aggregate confidence (weighted average)
        confidence = self._calculate_aggregate_confidence(
            text_confidence=text_quality,
            weights={'text': 0.5, 'table': 0.0, 'ocr': 0.0}
        )
        
        # Apply page coverage and character adequacy multipliers
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
    
    def get_metadata(self, pdf_data: bytes) -> Dict:
        """
        Extract PDF metadata (legacy method).
        
        NOTE: Use extract() method with extract_metadata=True instead.
        """
        return self._get_metadata_internal(pdf_data)
    
    # Internal implementation methods
    
    def _extract_text_internal(self, pdf_data: bytes) -> Dict:
        """Internal text extraction implementation"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            pages = []
            all_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                pages.append({
                    "page": page_num + 1,
                    "text": text,
                    "word_count": len(text.split()),
                    "char_count": len(text)
                })
                
                all_text.append(text)
            
            full_text = "\n\n".join(all_text)
            
            doc.close()
            
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
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            tables = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text with positioning
                text_dict = page.get_text("dict")
                
                # Simple table detection (basic heuristic)
                page_tables = self._detect_tables(text_dict)
                
                if page_tables:
                    tables.extend(page_tables)
            
            doc.close()
            
            return {
                "engine": self.engine_name,
                "tables": tables,
                "total_tables": len(tables),
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
    
    def _detect_tables(self, text_dict: Dict) -> List[Dict]:
        """
        Basic table detection heuristic.
        
        NOTE: PyMuPDF is not ideal for table extraction.
        Use PDFPlumber or Camelot for better table detection.
        """
        # Simplified - PDFPlumber and Camelot are better for tables
        return []
    
    def _get_metadata_internal(self, pdf_data: bytes) -> Dict:
        """Internal metadata extraction implementation"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            metadata = {
                "engine": self.engine_name,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "page_count": len(doc),
                "is_encrypted": doc.is_encrypted,
                "success": True
            }
            
            doc.close()
            
            return metadata
        
        except Exception as e:
            return {
                "engine": self.engine_name,
                "success": False,
                "error": str(e)
            }
