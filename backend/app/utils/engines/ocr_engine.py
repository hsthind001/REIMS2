import pytesseract
from PIL import Image
import io
from typing import Dict, List
import pdf2image


class OCREngine:
    """Tesseract OCR engine - For scanned documents"""
    
    def __init__(self):
        self.name = "tesseract_ocr"
        try:
            self.version = str(pytesseract.get_tesseract_version())
        except:
            self.version = "5.5.0"
    
    def extract_text_from_image(
        self,
        image_data: bytes,
        lang: str = "eng"
    ) -> Dict:
        """Extract text from an image using OCR"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=lang)
            
            # Get detailed data with confidence
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "engine": self.name,
                "text": text.strip(),
                "language": lang,
                "confidence": round(avg_confidence, 2),
                "word_count": len(text.split()),
                "char_count": len(text),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.name,
                "text": "",
                "confidence": 0,
                "success": False,
                "error": str(e)
            }
    
    def extract_text_from_pdf(
        self,
        pdf_data: bytes,
        lang: str = "eng",
        dpi: int = 300
    ) -> Dict:
        """Extract text from PDF by converting to images first"""
        try:
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            # Convert PDF to images
            images = pdf2image.convert_from_path(tmp_path, dpi=dpi)
            
            pages = []
            all_text = []
            total_confidence = 0
            
            for page_num, image in enumerate(images, 1):
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Extract text
                result = self.extract_text_from_image(img_bytes, lang=lang)
                
                pages.append({
                    "page": page_num,
                    "text": result["text"],
                    "confidence": result["confidence"],
                    "word_count": result["word_count"]
                })
                
                all_text.append(result["text"])
                total_confidence += result["confidence"]
            
            # Cleanup
            os.unlink(tmp_path)
            
            full_text = "\n\n".join(all_text)
            
            return {
                "engine": self.name,
                "text": full_text,
                "pages": pages,
                "total_pages": len(pages),
                "total_words": len(full_text.split()),
                "total_chars": len(full_text),
                "avg_confidence": round(total_confidence / len(pages), 2) if pages else 0,
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.name,
                "text": "",
                "pages": [],
                "total_pages": 0,
                "avg_confidence": 0,
                "success": False,
                "error": str(e)
            }


import tempfile
import os

