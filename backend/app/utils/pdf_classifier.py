import fitz
import pdfplumber
import io
from typing import Dict, List
from enum import Enum


class DocumentType(str, Enum):
    DIGITAL = "digital"  # Text-based PDF
    SCANNED = "scanned"  # Image-based PDF
    MIXED = "mixed"  # Mix of text and images
    TABLE_HEAVY = "table_heavy"  # Lots of tables
    FORM = "form"  # Form-like structure
    IMAGE_HEAVY = "image_heavy"  # Mostly images


class PDFClassifier:
    """Classify PDF documents to select optimal extraction strategy"""
    
    def __init__(self):
        pass
    
    def classify(self, pdf_data: bytes) -> Dict:
        """
        Classify PDF document type
        
        Returns:
            dict: Document classification and characteristics
        """
        try:
            # Open with PyMuPDF for analysis
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            total_pages = len(doc)
            total_text_chars = 0
            total_images = 0
            has_text_layers = []
            
            # Analyze first 5 pages (or all if less than 5)
            sample_pages = min(5, total_pages)
            
            for page_num in range(sample_pages):
                page = doc[page_num]
                
                # Get text
                text = page.get_text()
                total_text_chars += len(text)
                
                # Check if page has text
                has_text = len(text.strip()) > 50
                has_text_layers.append(has_text)
                
                # Count images
                images = page.get_images()
                total_images += len(images)
            
            doc.close()
            
            # Calculate metrics
            avg_text_per_page = total_text_chars / sample_pages
            avg_images_per_page = total_images / sample_pages
            text_coverage = sum(has_text_layers) / len(has_text_layers)
            
            # Classify document
            doc_type = self._determine_type(
                avg_text_per_page,
                avg_images_per_page,
                text_coverage,
                total_pages
            )
            
            # Check for tables using PDFPlumber on first page
            table_count = self._count_tables(pdf_data)
            
            if table_count > 2:
                doc_type = DocumentType.TABLE_HEAVY
            
            return {
                "document_type": doc_type,
                "characteristics": {
                    "total_pages": total_pages,
                    "avg_text_per_page": round(avg_text_per_page, 2),
                    "avg_images_per_page": round(avg_images_per_page, 2),
                    "text_coverage": round(text_coverage * 100, 2),
                    "table_count": table_count,
                    "has_text_layer": text_coverage > 0.5
                },
                "recommended_engines": self._get_recommended_engines(doc_type),
                "confidence": self._calculate_classification_confidence(
                    avg_text_per_page,
                    text_coverage,
                    avg_images_per_page
                ),
                "success": True
            }
        
        except Exception as e:
            return {
                "document_type": DocumentType.MIXED,
                "characteristics": {},
                "recommended_engines": ["pymupdf", "pdfplumber", "ocr"],
                "confidence": 0,
                "success": False,
                "error": str(e)
            }
    
    def _determine_type(
        self,
        avg_text: float,
        avg_images: float,
        text_coverage: float,
        total_pages: int
    ) -> DocumentType:
        """Determine document type based on metrics"""
        
        # Scanned: Little to no text layer, high image count
        if text_coverage < 0.3 and avg_images >= 0.5:
            return DocumentType.SCANNED
        
        # Digital: Good text layer, few images
        if text_coverage > 0.8 and avg_text > 500:
            return DocumentType.DIGITAL
        
        # Image heavy: Lots of images
        if avg_images > 3:
            return DocumentType.IMAGE_HEAVY
        
        # Mixed: Some text, some images
        if 0.3 <= text_coverage <= 0.8:
            return DocumentType.MIXED
        
        # Default to digital
        return DocumentType.DIGITAL
    
    def _count_tables(self, pdf_data: bytes) -> int:
        """Count tables in first page"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            if pdf.pages:
                tables = pdf.pages[0].extract_tables()
                pdf.close()
                return len(tables) if tables else 0
            pdf.close()
            return 0
        except:
            return 0
    
    def _get_recommended_engines(self, doc_type: DocumentType) -> List[str]:
        """Get recommended extraction engines based on document type"""
        
        recommendations = {
            DocumentType.DIGITAL: ["pymupdf", "pdfplumber"],
            DocumentType.SCANNED: ["ocr", "pymupdf"],
            DocumentType.MIXED: ["pymupdf", "pdfplumber", "ocr"],
            DocumentType.TABLE_HEAVY: ["camelot", "pdfplumber", "pymupdf"],
            DocumentType.FORM: ["pdfplumber", "pymupdf"],
            DocumentType.IMAGE_HEAVY: ["pymupdf", "ocr"]
        }
        
        return recommendations.get(doc_type, ["pymupdf", "pdfplumber"])
    
    def _calculate_classification_confidence(
        self,
        avg_text: float,
        text_coverage: float,
        avg_images: float
    ) -> float:
        """Calculate confidence in classification"""
        
        # High confidence if metrics are clear
        if (text_coverage > 0.9 or text_coverage < 0.1) and avg_text > 100:
            return 95.0
        elif (text_coverage > 0.7 or text_coverage < 0.3):
            return 85.0
        else:
            return 70.0

