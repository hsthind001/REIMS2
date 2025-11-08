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
    
    def detect_year_and_period(self, pdf_data: bytes) -> Dict:
        """
        Detect year and period from PDF content
        
        Looks for:
        - Year (2020-2030)
        - Month names (January, Feb, etc.)
        - Month numbers (01-12)
        - Common period formats ("December 2024", "12/31/2024", "YE 2024")
        
        Returns:
            dict: {
                "year": int or None,
                "month": int or None,
                "period_text": str,
                "confidence": float
            }
        """
        try:
            import re
            from datetime import datetime
            
            # Quick extraction of first 2 pages
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"year": None, "month": None, "period_text": "", "confidence": 0}
            
            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:
                sample_text += page.get("text", "")
            
            # Extract years (2020-2030)
            years = re.findall(r'\b(202[0-9]|2030)\b', sample_text)
            
            # Extract months (names and numbers)
            month_names = {
                'january': 1, 'jan': 1,
                'february': 2, 'feb': 2,
                'march': 3, 'mar': 3,
                'april': 4, 'apr': 4,
                'may': 5,
                'june': 6, 'jun': 6,
                'july': 7, 'jul': 7,
                'august': 8, 'aug': 8,
                'september': 9, 'sep': 9, 'sept': 9,
                'october': 10, 'oct': 10,
                'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            
            found_months = []
            sample_lower = sample_text.lower()
            for month_name, month_num in month_names.items():
                if month_name in sample_lower:
                    found_months.append(month_num)
            
            # Get most common year and month
            detected_year = int(years[0]) if years else None
            detected_month = found_months[0] if found_months else None
            
            # Calculate confidence
            confidence = 0
            if detected_year:
                confidence += 50
            if detected_month:
                confidence += 50
            
            # Find period text for display
            period_text = ""
            if detected_month and detected_year:
                month_name = list(month_names.keys())[list(month_names.values()).index(detected_month)]
                period_text = f"{month_name.capitalize()} {detected_year}"
            elif detected_year:
                period_text = str(detected_year)
            
            return {
                "year": detected_year,
                "month": detected_month,
                "period_text": period_text,
                "confidence": confidence
            }
            
        except Exception as e:
            return {
                "year": None,
                "month": None,
                "period_text": "",
                "confidence": 0,
                "error": str(e)
            }
    
    def detect_document_type(self, pdf_data: bytes) -> Dict:
        """
        Quickly detect financial document type from PDF content
        
        Analyzes first 2 pages for keywords to determine if document is:
        - Balance Sheet
        - Income Statement  
        - Cash Flow Statement
        - Rent Roll
        
        Returns:
            dict: {
                "detected_type": str,
                "confidence": float,
                "keywords_found": list
            }
        """
        try:
            # Quick extraction of first 2 pages only for speed
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"detected_type": "unknown", "confidence": 0, "keywords_found": []}
            
            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:  # Only first 2 pages
                sample_text += page.get("text", "").lower()
            
            # Define keyword patterns for each document type
            keywords = {
                "balance_sheet": [
                    "assets", "liabilities", "equity", "current assets", "long-term assets",
                    "current liabilities", "stockholders equity", "total assets", "balance sheet"
                ],
                "income_statement": [
                    "revenue", "income statement", "profit and loss", "p&l", "operating income",
                    "net income", "operating expenses", "gross income", "income and expense", "statement of operations"
                ],
                "cash_flow": [
                    "cash flow", "operating activities", "investing activities", "financing activities",
                    "net cash", "cash from operations", "beginning cash", "ending cash"
                ],
                "rent_roll": [
                    "tenant", "unit", "rent roll", "lease", "sq ft", "square feet",
                    "lease expiration", "monthly rent", "annual rent", "occupancy"
                ]
            }
            
            # Count keywords for each type
            scores = {}
            found_keywords = {}
            
            for doc_type, keyword_list in keywords.items():
                count = 0
                found = []
                for keyword in keyword_list:
                    if keyword in sample_text:
                        count += 1
                        found.append(keyword)
                scores[doc_type] = count
                found_keywords[doc_type] = found
            
            # Determine most likely type
            if max(scores.values()) == 0:
                return {"detected_type": "unknown", "confidence": 0, "keywords_found": []}
            
            detected_type = max(scores, key=scores.get)
            total_keywords = len(keywords[detected_type])
            confidence = (scores[detected_type] / total_keywords) * 100
            
            return {
                "detected_type": detected_type,
                "confidence": round(confidence, 1),
                "keywords_found": found_keywords[detected_type]
            }
            
        except Exception as e:
            return {
                "detected_type": "unknown",
                "confidence": 0,
                "keywords_found": [],
                "error": str(e)
            }
    
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

