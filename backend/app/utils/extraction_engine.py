from typing import Dict, List, Optional
from app.utils.engines.pymupdf_engine import PyMuPDFEngine
from app.utils.engines.pdfplumber_engine import PDFPlumberEngine
from app.utils.engines.camelot_engine import CamelotEngine
from app.utils.engines.ocr_engine import OCREngine
from app.utils.pdf_classifier import PDFClassifier, DocumentType
from app.utils.quality_validator import QualityValidator
import time


class MultiEngineExtractor:
    """
    Multi-engine PDF extraction orchestrator
    
    Automatically selects and runs optimal extraction engines based on document type,
    validates results, and provides quality scores
    """
    
    def __init__(self):
        # Initialize engines
        self.pymupdf = PyMuPDFEngine()
        self.pdfplumber = PDFPlumberEngine()
        self.camelot = CamelotEngine()
        self.ocr = OCREngine()
        
        # Initialize utilities
        self.classifier = PDFClassifier()
        self.validator = QualityValidator()
    
    def extract_with_validation(
        self,
        pdf_data: bytes,
        strategy: str = "auto",
        lang: str = "eng"
    ) -> Dict:
        """
        Extract text with automatic validation
        
        Args:
            pdf_data: PDF file as bytes
            strategy: 'auto', 'fast', 'accurate', 'multi_engine'
            lang: Language code for OCR
        
        Returns:
            dict: Extraction results with quality validation
        """
        start_time = time.time()
        
        try:
            # Step 1: Classify document
            classification = self.classifier.classify(pdf_data)
            doc_type = classification.get("document_type", DocumentType.DIGITAL)
            
            # Step 2: Select extraction strategy
            if strategy == "auto":
                extraction = self._extract_auto(pdf_data, doc_type, lang)
            elif strategy == "fast":
                extraction = self._extract_fast(pdf_data)
            elif strategy == "accurate":
                extraction = self._extract_accurate(pdf_data, lang)
            elif strategy == "multi_engine":
                extraction = self._extract_multi_engine(pdf_data, lang)
            else:
                extraction = self._extract_auto(pdf_data, doc_type, lang)
            
            # Step 3: Validate extraction
            validation = self.validator.validate_extraction(extraction)
            
            # Step 4: Build final result
            processing_time = time.time() - start_time
            
            result = {
                "extraction": extraction,
                "validation": validation,
                "classification": classification,
                "processing_time_seconds": round(processing_time, 2),
                "strategy_used": strategy,
                "quality_level": validation["overall_quality"],
                "confidence_score": validation["confidence_score"],
                "needs_review": validation["confidence_score"] < 85,
                "success": True
            }
            
            return result
        
        except Exception as e:
            return {
                "extraction": {},
                "validation": {},
                "classification": {},
                "success": False,
                "error": str(e)
            }
    
    def _extract_auto(
        self,
        pdf_data: bytes,
        doc_type: DocumentType,
        lang: str
    ) -> Dict:
        """Automatic engine selection based on document type"""
        
        if doc_type == DocumentType.DIGITAL:
            # Use PyMuPDF (fastest and accurate for digital PDFs)
            return self.pymupdf.extract_text(pdf_data)
        
        elif doc_type == DocumentType.SCANNED:
            # Use OCR
            return self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
        
        elif doc_type == DocumentType.TABLE_HEAVY:
            # Use PDFPlumber for better table handling
            return self.pdfplumber.extract_text(pdf_data)
        
        elif doc_type == DocumentType.MIXED:
            # Try PyMuPDF first, fall back to OCR if quality is low
            result = self.pymupdf.extract_text(pdf_data)
            validation = self.validator.validate_extraction(result)
            
            if validation["confidence_score"] < 70:
                # Quality too low, try OCR
                result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
            
            return result
        
        else:
            # Default to PyMuPDF
            return self.pymupdf.extract_text(pdf_data)
    
    def _extract_fast(self, pdf_data: bytes) -> Dict:
        """Fast extraction - single engine (PyMuPDF)"""
        return self.pymupdf.extract_text(pdf_data)
    
    def _extract_accurate(self, pdf_data: bytes, lang: str) -> Dict:
        """Accurate extraction - best single engine based on document"""
        classification = self.classifier.classify(pdf_data)
        doc_type = classification.get("document_type", DocumentType.DIGITAL)
        
        return self._extract_auto(pdf_data, doc_type, lang)
    
    def _extract_multi_engine(self, pdf_data: bytes, lang: str) -> Dict:
        """
        Extract with multiple engines and return best result
        
        Most accurate but slowest method
        """
        results = []
        
        # Extract with PyMuPDF
        pymupdf_result = self.pymupdf.extract_text(pdf_data)
        if pymupdf_result["success"]:
            results.append(pymupdf_result)
        
        # Extract with PDFPlumber
        pdfplumber_result = self.pdfplumber.extract_text(pdf_data)
        if pdfplumber_result["success"]:
            results.append(pdfplumber_result)
        
        # If both failed or low quality, try OCR
        if len(results) < 2 or all(len(r.get("text", "")) < 100 for r in results):
            ocr_result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
            if ocr_result["success"]:
                results.append(ocr_result)
        
        # Select best result based on validation
        best_result = self._select_best_result(results)
        
        # Add multi-engine metadata
        best_result["engines_used"] = [r.get("engine", "unknown") for r in results]
        best_result["total_engines"] = len(results)
        
        return best_result
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """Select best extraction result from multiple engines"""
        if not results:
            return {"engine": "none", "text": "", "success": False, "error": "All engines failed"}
        
        if len(results) == 1:
            return results[0]
        
        # Validate each result
        scored_results = []
        
        for result in results:
            validation = self.validator.validate_extraction(result)
            scored_results.append({
                "result": result,
                "score": validation["confidence_score"]
            })
        
        # Sort by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return best result
        return scored_results[0]["result"]
    
    def extract_with_consensus(
        self,
        pdf_data: bytes,
        engines: Optional[List[str]] = None,
        lang: str = "eng"
    ) -> Dict:
        """
        Extract with multiple engines and calculate consensus
        
        Args:
            pdf_data: PDF file as bytes
            engines: List of engine names to use (None = all)
            lang: Language for OCR
        
        Returns:
            dict: All extraction results with consensus analysis
        """
        try:
            extractions = []
            
            # Determine which engines to use
            if engines is None:
                engines = ["pymupdf", "pdfplumber"]  # Default pair
            
            # Run each engine
            if "pymupdf" in engines:
                result = self.pymupdf.extract_text(pdf_data)
                if result["success"]:
                    extractions.append(result)
            
            if "pdfplumber" in engines:
                result = self.pdfplumber.extract_text(pdf_data)
                if result["success"]:
                    extractions.append(result)
            
            if "ocr" in engines:
                result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
                if result["success"]:
                    extractions.append(result)
            
            # Calculate consensus
            consensus = self.validator.calculate_consensus_score(extractions)
            
            # Select best extraction
            best_extraction = self._select_best_result(extractions)
            
            # Validate best extraction
            validation = self.validator.validate_extraction(best_extraction)
            
            return {
                "primary_extraction": best_extraction,
                "all_extractions": extractions,
                "consensus": consensus,
                "validation": validation,
                "total_engines_used": len(extractions),
                "confidence_score": validation["confidence_score"],
                "quality_level": validation["overall_quality"],
                "success": True
            }
        
        except Exception as e:
            return {
                "primary_extraction": {},
                "all_extractions": [],
                "consensus": {},
                "validation": {},
                "success": False,
                "error": str(e)
            }
    
    def extract_tables_comprehensive(self, pdf_data: bytes) -> Dict:
        """
        Extract tables using multiple engines for best accuracy
        
        Combines Camelot and PDFPlumber results
        """
        try:
            # Try Camelot first (best for bordered tables)
            camelot_lattice = self.camelot.extract_tables(pdf_data, flavor="lattice")
            camelot_stream = self.camelot.extract_tables(pdf_data, flavor="stream")
            
            # Try PDFPlumber
            pdfplumber_result = self.pdfplumber.extract_tables(pdf_data)
            
            # Combine results
            all_tables = []
            
            if camelot_lattice["success"]:
                all_tables.extend(camelot_lattice.get("tables", []))
            
            if camelot_stream["success"]:
                all_tables.extend(camelot_stream.get("tables", []))
            
            if pdfplumber_result["success"]:
                all_tables.extend(pdfplumber_result.get("tables", []))
            
            # Remove duplicates (basic heuristic)
            unique_tables = self._deduplicate_tables(all_tables)
            
            return {
                "tables": unique_tables,
                "total_tables": len(unique_tables),
                "engines_used": ["camelot_lattice", "camelot_stream", "pdfplumber"],
                "success": True
            }
        
        except Exception as e:
            return {
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def _deduplicate_tables(self, tables: List[Dict]) -> List[Dict]:
        """Remove duplicate tables (simple implementation)"""
        # In production, implement more sophisticated deduplication
        # For now, just return all tables
        return tables

