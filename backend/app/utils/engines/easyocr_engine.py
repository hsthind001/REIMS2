"""
EasyOCR Extraction Engine

Enhanced OCR engine for scanned documents with GPU acceleration.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from PIL import Image
import cv2
import numpy as np
import easyocr
from app.utils.engines.base_extractor import BaseExtractor, ExtractionResult
from app.utils.pdf_to_image import PDFToImageConverter


class EasyOCREngine(BaseExtractor):
    """
    EasyOCR extraction engine - Enhanced OCR for scanned documents
    
    Best for: Scanned PDFs, low-quality scans, handwritten text
    """
    
    def __init__(self, languages: List[str] = ['en'], gpu: bool = True):
        """
        Initialize EasyOCR engine.
        
        Args:
            languages: List of language codes (default: ['en'])
            gpu: Use GPU acceleration if available
        """
        super().__init__(engine_name="easyocr")
        self.languages = languages
        self.gpu = gpu
        self.reader = None
        self.pdf_converter = PDFToImageConverter(dpi=300)  # Higher DPI for OCR
        self._reader_loaded = False
    
    def _load_reader(self):
        """Lazy load EasyOCR reader"""
        if self._reader_loaded:
            return
        
        print(f"🤖 Loading EasyOCR reader (languages: {self.languages})")
        self.reader = easyocr.Reader(self.languages, gpu=self.gpu)
        self._reader_loaded = True
        print(f"✅ EasyOCR reader loaded")
    
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract text from PDF using EasyOCR.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Optional parameters
                - max_pages: Maximum pages to process
                - preprocess: Apply image preprocessing (default: True)
        
        Returns:
            ExtractionResult with OCR text and confidence scores
        """
        self._start_timer()
        
        try:
            self._load_reader()
            
            max_pages = kwargs.get("max_pages", None)
            preprocess = kwargs.get("preprocess", True)
            
            # Convert PDF to images
            page_images = self.pdf_converter.convert_with_metadata(pdf_data, max_pages)
            
            # Process each page
            page_results = []
            all_text = []
            
            for page_info in page_images:
                result = self._process_page(page_info["image"], page_info["page_number"], preprocess)
                page_results.append(result)
                all_text.append(result["text"])
            
            full_text = "\n\n".join(all_text)
            avg_confidence = sum(p["confidence"] for p in page_results) / len(page_results) if page_results else 0.0
            
            extracted_data = {
                "text": full_text,
                "pages": page_results,
                "total_pages": len(page_results),
                "total_words": sum(p["word_count"] for p in page_results),
                "total_chars": len(full_text)
            }
            
            confidence = self.calculate_confidence(extracted_data)
            
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data=extracted_data,
                success=True,
                confidence_score=confidence,
                processing_time_ms=self._get_processing_time_ms(),
                page_count=len(page_results),
                ocr_confidence=avg_confidence,
                engine_metadata={
                    "languages": self.languages,
                    "gpu_enabled": self.gpu,
                    "dpi": self.pdf_converter.dpi,
                    "preprocessing": preprocess
                }
            )
        
        except Exception as e:
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data={},
                success=False,
                error_message=str(e),
                processing_time_ms=self._get_processing_time_ms()
            )
    
    def _process_page(self, image: Image.Image, page_number: int, preprocess: bool) -> Dict:
        """Process single page with EasyOCR"""
        # Convert PIL to numpy
        img_array = np.array(image)
        
        # Preprocess if enabled
        if preprocess:
            img_array = self._preprocess_image(img_array)
        
        # Run OCR
        results = self.reader.readtext(img_array)
        
        # Extract text and confidence
        texts = []
        confidences = []
        
        for (bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)
        
        full_text = " ".join(texts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "page": page_number,
            "text": full_text,
            "confidence": avg_conf,
            "word_count": len(texts),
            "char_count": len(full_text)
        }
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Pipeline:
        1. Convert to grayscale
        2. Denoise
        3. Increase contrast
        4. Binarize (Otsu's method)
        """
        # Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Increase contrast (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)
        
        # Binarize (Otsu's threshold)
        _, binary = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def calculate_confidence(self, extraction_data: Dict[str, Any]) -> Decimal:
        """Calculate confidence from EasyOCR results"""
        pages = extraction_data.get("pages", [])
        
        if not pages:
            return Decimal('0.0')
        
        # EasyOCR provides word-level confidence
        avg_ocr_conf = sum(p.get("confidence", 0.0) for p in pages) / len(pages)
        
        # Also check text quality
        text = extraction_data.get("text", "")
        text_quality = self._calculate_text_quality(text, expected_min_length=50)
        
        # Combine OCR confidence with text quality
        final_conf = (avg_ocr_conf * 0.8) + (text_quality * 0.2)
        
        return Decimal(str(round(final_conf, 4)))

