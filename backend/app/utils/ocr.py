import pytesseract
from PIL import Image
import io
from typing import Optional, List, Dict
import pdf2image
import os


def extract_text_from_image(
    image_data: bytes,
    lang: str = "eng",
    config: str = ""
) -> Dict:
    """
    Extract text from an image using Tesseract OCR
    
    Args:
        image_data: Image file as bytes
        lang: Language code (eng, fra, deu, etc.)
        config: Tesseract configuration options
    
    Returns:
        dict: Extracted text and metadata
    """
    try:
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        
        # Get detailed data
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        
        # Calculate confidence
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "text": text.strip(),
            "language": lang,
            "confidence": round(avg_confidence, 2),
            "word_count": len(text.split()),
            "char_count": len(text),
            "success": True
        }
    
    except Exception as e:
        return {
            "text": "",
            "language": lang,
            "confidence": 0,
            "word_count": 0,
            "char_count": 0,
            "success": False,
            "error": str(e)
        }


def extract_text_with_boxes(
    image_data: bytes,
    lang: str = "eng"
) -> Dict:
    """
    Extract text with bounding box coordinates
    
    Args:
        image_data: Image file as bytes
        lang: Language code
    
    Returns:
        dict: Text with bounding box information
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get bounding boxes
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        
        # Extract words with bounding boxes
        words = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:  # Only include confident detections
                word_info = {
                    "text": data['text'][i],
                    "confidence": int(data['conf'][i]),
                    "left": data['left'][i],
                    "top": data['top'][i],
                    "width": data['width'][i],
                    "height": data['height'][i],
                    "block_num": data['block_num'][i],
                    "line_num": data['line_num'][i],
                    "word_num": data['word_num'][i]
                }
                words.append(word_info)
        
        return {
            "words": words,
            "total_words": len(words),
            "image_width": data['width'][0] if data['width'] else 0,
            "image_height": data['height'][0] if data['height'] else 0,
            "success": True
        }
    
    except Exception as e:
        return {
            "words": [],
            "total_words": 0,
            "success": False,
            "error": str(e)
        }


def extract_text_from_pdf(
    pdf_data: bytes,
    lang: str = "eng",
    dpi: int = 300
) -> Dict:
    """
    Extract text from PDF by converting to images first
    
    Args:
        pdf_data: PDF file as bytes
        lang: Language code
        dpi: DPI for PDF to image conversion
    
    Returns:
        dict: Extracted text from all pages
    """
    try:
        # Save PDF temporarily
        temp_pdf_path = "/tmp/temp_ocr.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_data)
        
        # Convert PDF to images
        images = pdf2image.convert_from_path(temp_pdf_path, dpi=dpi)
        
        # Extract text from each page
        pages_text = []
        total_confidence = 0
        
        for page_num, image in enumerate(images, 1):
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Extract text
            result = extract_text_from_image(img_bytes, lang=lang)
            
            pages_text.append({
                "page": page_num,
                "text": result["text"],
                "confidence": result["confidence"],
                "word_count": result["word_count"]
            })
            
            total_confidence += result["confidence"]
        
        # Cleanup
        os.remove(temp_pdf_path)
        
        # Combine all text
        full_text = "\n\n--- Page Break ---\n\n".join([p["text"] for p in pages_text])
        
        return {
            "text": full_text,
            "pages": pages_text,
            "total_pages": len(pages_text),
            "avg_confidence": round(total_confidence / len(pages_text), 2) if pages_text else 0,
            "success": True
        }
    
    except Exception as e:
        return {
            "text": "",
            "pages": [],
            "total_pages": 0,
            "avg_confidence": 0,
            "success": False,
            "error": str(e)
        }


def get_supported_languages() -> List[str]:
    """
    Get list of installed Tesseract languages
    
    Returns:
        list: Available language codes
    """
    try:
        langs = pytesseract.get_languages()
        return sorted(langs)
    except Exception as e:
        return ["eng"]  # Default to English


def get_tesseract_version() -> str:
    """
    Get Tesseract version
    
    Returns:
        str: Version string
    """
    try:
        return pytesseract.get_tesseract_version()
    except Exception:
        return "Unknown"

