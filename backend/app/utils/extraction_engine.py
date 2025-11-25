from typing import Dict, List, Optional
import logging
from app.utils.engines.pymupdf_engine import PyMuPDFEngine
from app.utils.engines.pdfplumber_engine import PDFPlumberEngine
from app.utils.engines.base_extractor import ExtractionResult
from app.utils.pdf_classifier import PDFClassifier, DocumentType
from app.utils.quality_validator import QualityValidator
from app.services.model_scoring_service import ModelScoringService, ScoringFactors
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Optional engines with heavy dependencies - import gracefully
logger = logging.getLogger(__name__)

try:
    from app.utils.engines.camelot_engine import CamelotEngine
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.warning("Camelot engine not available")

try:
    from app.utils.engines.ocr_engine import OCREngine
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR engine not available")

try:
    from app.utils.engines.layoutlm_engine import LayoutLMEngine
    LAYOUTLM_AVAILABLE = True
except ImportError:
    LAYOUTLM_AVAILABLE = False
    logger.warning("LayoutLM engine not available")

try:
    from app.utils.engines.easyocr_engine import EasyOCREngine
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR engine not available")


class MultiEngineExtractor:
    """
    Multi-engine PDF extraction orchestrator
    
    Automatically selects and runs optimal extraction engines based on document type,
    validates results, and provides quality scores
    """
    
    def __init__(self, scoring_factors: Optional[ScoringFactors] = None):
        # Initialize core engines (always available)
        self.pymupdf = PyMuPDFEngine()
        self.pdfplumber = PDFPlumberEngine()

        # Initialize optional engines if available
        self.camelot = CamelotEngine() if CAMELOT_AVAILABLE else None
        self.ocr = OCREngine() if OCR_AVAILABLE else None
        self.layoutlm = LayoutLMEngine() if LAYOUTLM_AVAILABLE else None
        self.easyocr = EasyOCREngine() if EASYOCR_AVAILABLE else None

        # Initialize utilities
        self.classifier = PDFClassifier()
        self.validator = QualityValidator()
        
        # Initialize external scoring service (models don't calculate their own confidence)
        self.scoring_service = ModelScoringService(scoring_factors=scoring_factors)

        # Log available engines
        available_engines = ['PyMuPDF', 'PDFPlumber']
        if self.camelot:
            available_engines.append('Camelot')
        if self.ocr:
            available_engines.append('OCR')
        if self.layoutlm:
            available_engines.append('LayoutLM')
        if self.easyocr:
            available_engines.append('EasyOCR')
        logger.info(f"MultiEngineExtractor initialized with {len(available_engines)} engines: {available_engines}")
    
    def detect_property_name(self, pdf_data: bytes, available_properties: list) -> Dict:
        """
        Detect property name from PDF content
        
        Searches for property names, codes, and addresses in first 2 pages
        
        Args:
            pdf_data: PDF file bytes
            available_properties: List of dicts with property_code, property_name, address
        
        Returns:
            dict: {
                "detected_property_code": str or None,
                "detected_property_name": str or None,
                "confidence": float,
                "matches_found": list
            }
        """
        try:
            # Quick extraction of first 2 pages
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"detected_property_code": None, "detected_property_name": None, "confidence": 0, "matches_found": []}
            
            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:
                sample_text += page.get("text", "")
            
            sample_lower = sample_text.lower()
            
            # Search for each property
            matches = []
            best_match = None
            best_score = 0
            
            for prop in available_properties:
                score = 0
                prop_matches = []
                
                # Check property code (e.g., ESP001, HMND001)
                if prop.get('property_code') and prop['property_code'].lower() in sample_lower:
                    score += 40
                    prop_matches.append(f"Code: {prop['property_code']}")
                
                # Check property name (e.g., "Eastern Shore Plaza", "Hammond Aire")
                if prop.get('property_name'):
                    # Split name into words and check each
                    name_words = prop['property_name'].lower().split()
                    matched_words = sum(1 for word in name_words if len(word) > 3 and word in sample_lower)
                    if matched_words > 0:
                        word_score = (matched_words / len(name_words)) * 30
                        score += word_score
                        prop_matches.append(f"Name: {matched_words}/{len(name_words)} words")
                
                # Check address/city if available
                if prop.get('city') and prop['city'].lower() in sample_lower:
                    score += 20
                    prop_matches.append(f"City: {prop['city']}")
                
                if score > best_score:
                    best_score = score
                    best_match = prop
                    matches = prop_matches
            
            if best_match and best_score >= 30:
                return {
                    "detected_property_code": best_match.get('property_code'),
                    "detected_property_name": best_match.get('property_name'),
                    "confidence": round(best_score, 1),
                    "matches_found": matches
                }
            
            return {
                "detected_property_code": None,
                "detected_property_name": None,
                "confidence": 0,
                "matches_found": []
            }
            
        except Exception as e:
            return {
                "detected_property_code": None,
                "detected_property_name": None,
                "confidence": 0,
                "matches_found": [],
                "error": str(e)
            }
    
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
            
            # Get most common year (not just first one)
            detected_year = None
            if years:
                # Count occurrences of each year
                from collections import Counter
                year_counts = Counter(years)
                # Get most common year
                detected_year = int(year_counts.most_common(1)[0][0])
            
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
    
    def _convert_confidence_to_score(self, confidence: float) -> float:
        """
        Convert confidence score (0.0-1.0) to extraction score (1-10).
        
        Formula: score = 1 + (confidence * 9)
        - confidence 0.0 → score 1.0
        - confidence 0.5 → score 5.5
        - confidence 1.0 → score 10.0
        
        Args:
            confidence: Confidence score between 0.0 and 1.0
            
        Returns:
            Score between 1.0 and 10.0
        """
        if confidence < 0:
            return 1.0
        if confidence > 1.0:
            return 10.0
        
        score = 1.0 + (confidence * 9.0)
        return round(score, 1)
    
    def extract_with_all_models_scored(
        self,
        pdf_data: bytes,
        lang: str = "eng"
    ) -> Dict[str, Any]:
        """
        Extract using ALL available models and score each on 1-10 scale.
        
        This method runs all available extraction engines (including AI models)
        and returns a scored comparison of their results.
        
        Args:
            pdf_data: Binary PDF data
            lang: Language code for OCR engines (default: "eng")
        
        Returns:
            dict: {
                "results": [
                    {
                        "model": "PyMuPDF",
                        "score": 8.5,
                        "confidence": 0.85,
                        "success": True,
                        "text_length": 5000,
                        "processing_time_ms": 120,
                        "extracted_data": {...},
                        "error": None
                    },
                    ...
                ],
                "best_model": "LayoutLM",
                "best_score": 9.2,
                "total_models": 6,
                "successful_models": 5
            }
        """
        all_results = []
        
        # List of all available engines with their display names
        engines_to_run = [
            ("PyMuPDF", self.pymupdf),
            ("PDFPlumber", self.pdfplumber),
        ]
        
        # Add optional engines if available
        if self.camelot:
            engines_to_run.append(("Camelot", self.camelot))
        if self.ocr:
            engines_to_run.append(("Tesseract OCR", self.ocr))
        if self.layoutlm:
            engines_to_run.append(("LayoutLMv3", self.layoutlm))
        if self.easyocr:
            engines_to_run.append(("EasyOCR", self.easyocr))
        
        logger.info(f"Running {len(engines_to_run)} extraction engines for scoring...")
        
        # Run all engines
        for engine_name, engine in engines_to_run:
            try:
                logger.info(f"Running {engine_name}...")
                
                # Handle different engine types
                # Most engines have extract() method returning ExtractionResult
                # OCR engine has extract_text_from_pdf() returning Dict
                extracted_data = {}
                processing_time_ms = 0.0
                success = True
                error = None
                
                try:
                    if hasattr(engine, 'extract'):
                        result = engine.extract(pdf_data, lang=lang)
                        
                        # Extract data (NOT confidence - models don't calculate it)
                        if hasattr(result, 'extracted_data') and result.extracted_data:
                            extracted_data = result.extracted_data
                        
                        # Get processing time
                        if hasattr(result, 'processing_time_ms') and result.processing_time_ms:
                            processing_time_ms = float(result.processing_time_ms)
                        
                        success = result.success if hasattr(result, 'success') else True
                        if not success:
                            error = getattr(result, 'error_message', 'Extraction failed')
                    elif hasattr(engine, 'extract_text_from_pdf'):
                        # OCR engine uses extract_text_from_pdf()
                        result = engine.extract_text_from_pdf(pdf_data, lang=lang)
                        
                        # Convert dict result to extracted_data format
                        extracted_data = {
                            'text': result.get('text', ''),
                            'pages': result.get('pages', []),
                            'total_pages': result.get('total_pages', 0),
                            'total_words': result.get('total_words', 0),
                            'total_chars': result.get('total_chars', 0)
                        }
                        processing_time_ms = 0.0  # OCR doesn't track time
                        success = result.get('success', False)
                        if not success:
                            error = result.get('error', 'Extraction failed')
                    else:
                        # Fallback: try extract_text() method
                        result = engine.extract_text(pdf_data)
                        
                        # Convert dict result to extracted_data format
                        extracted_data = {
                            'text': result.get('text', ''),
                            'pages': result.get('pages', []),
                            'total_pages': result.get('total_pages', 0),
                            'total_words': result.get('total_words', 0),
                            'total_chars': result.get('total_chars', 0)
                        }
                        processing_time_ms = 0.0
                        success = result.get('success', False)
                        if not success:
                            error = result.get('error', 'Extraction failed')
                except Exception as e:
                    success = False
                    error = str(e)
                    extracted_data = {}
                
                # Score externally using client-defined factors (NOT model's internal confidence)
                scoring_result = self.scoring_service.score_extraction_result(
                    model_name=engine_name,
                    extracted_data=extracted_data,
                    processing_time_ms=processing_time_ms,
                    success=success,
                    error=error
                )
                
                score = scoring_result['score']
                confidence = scoring_result['confidence']
                
                # Extract text length from extracted_data
                text_length = len(extracted_data.get('text', '')) if extracted_data else 0
                
                # Prepare result dict
                result_dict = {
                    "model": engine_name,
                    "score": score,
                    "confidence": confidence,
                    "success": success,
                    "text_length": text_length,
                    "processing_time_ms": round(processing_time_ms, 2),
                    "extracted_data": extracted_data,
                    "score_breakdown": scoring_result.get('score_breakdown', {}),
                    "error": error
                }
                
                # Add page count if available
                if extracted_data and 'total_pages' in extracted_data:
                    result_dict["page_count"] = extracted_data['total_pages']
                
                all_results.append(result_dict)
                logger.info(f"{engine_name} completed: score={score}, confidence={confidence:.3f}, text_length={text_length}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"{engine_name} failed: {error_msg}")
                all_results.append({
                    "model": engine_name,
                    "score": 0.0,
                    "confidence": 0.0,
                    "success": False,
                    "text_length": 0,
                    "processing_time_ms": 0.0,
                    "extracted_data": {},
                    "error": error_msg
                })
        
        # Find best model
        successful_results = [r for r in all_results if r['success']]
        if successful_results:
            best = max(successful_results, key=lambda x: x['score'])
            best_model = best['model']
            best_score = best['score']
        else:
            best_model = None
            best_score = 0.0
        
        # Calculate average score
        avg_score = 0.0
        if successful_results:
            avg_score = sum(r['score'] for r in successful_results) / len(successful_results)
        
        logger.info(f"All models completed. Best: {best_model} (score: {best_score})")
        
        return {
            "results": all_results,
            "best_model": best_model,
            "best_score": round(best_score, 1),
            "total_models": len(all_results),
            "successful_models": len(successful_results),
            "average_score": round(avg_score, 1)
        }
    
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
    
    def extract_with_confidence(
        self,
        pdf_data: bytes,
        run_all_engines: bool = True
    ) -> List[ExtractionResult]:
        """
        NEW METHOD: Extract using all engines and return ExtractionResult objects.
        
        This method uses the new BaseExtractor framework and returns
        ExtractionResult objects with confidence scores for metadata tracking.
        
        Args:
            pdf_data: PDF file as bytes
            run_all_engines: If True, runs all 3 engines. If False, runs based on doc type
        
        Returns:
            List of ExtractionResult objects from each engine
        """
        results = []
        
        if run_all_engines:
            # Run all three main engines for maximum confidence
            
            # PyMuPDF - Good for text
            try:
                pymupdf_result = self.pymupdf.extract(
                    pdf_data,
                    extract_tables=False,
                    extract_metadata=True
                )
                results.append(pymupdf_result)
            except Exception as e:
                # Add failed result
                results.append(ExtractionResult(
                    engine_name="pymupdf",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
            
            # PDFPlumber - Best for tables
            try:
                pdfplumber_result = self.pdfplumber.extract(
                    pdf_data,
                    extract_tables=True
                )
                results.append(pdfplumber_result)
            except Exception as e:
                results.append(ExtractionResult(
                    engine_name="pdfplumber",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
            
            # Camelot - Best for complex tables
            try:
                camelot_result = self.camelot.extract(
                    pdf_data,
                    flavor="both"  # Try both lattice and stream
                )
                results.append(camelot_result)
            except Exception as e:
                results.append(ExtractionResult(
                    engine_name="camelot",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
        
        else:
            # Run engines based on document type (optimized)
            classification = self.classifier.classify(pdf_data)
            doc_type = classification.get("document_type", DocumentType.DIGITAL)
            recommended = self._get_recommended_engines(doc_type)
            
            if "pymupdf" in recommended:
                try:
                    results.append(self.pymupdf.extract(pdf_data, extract_metadata=True))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="pymupdf",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
            
            if "pdfplumber" in recommended:
                try:
                    results.append(self.pdfplumber.extract(pdf_data, extract_tables=True))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="pdfplumber",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
            
            if "camelot" in recommended:
                try:
                    results.append(self.camelot.extract(pdf_data, flavor="both"))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="camelot",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
        
        return results

