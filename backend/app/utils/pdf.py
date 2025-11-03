import fitz  # PyMuPDF
import io
from typing import List, Dict, Optional, Tuple
from PIL import Image


def extract_text_from_pdf(pdf_data: bytes) -> Dict:
    """
    Extract all text from a PDF file
    
    Args:
        pdf_data: PDF file as bytes
    
    Returns:
        dict: Extracted text and metadata
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        pages_text = []
        total_chars = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            pages_text.append({
                "page": page_num + 1,
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split())
            })
            
            total_chars += len(text)
        
        doc.close()
        
        full_text = "\n\n--- Page Break ---\n\n".join([p["text"] for p in pages_text])
        
        return {
            "text": full_text,
            "pages": pages_text,
            "total_pages": len(pages_text),
            "total_chars": total_chars,
            "total_words": len(full_text.split()),
            "success": True
        }
    
    except Exception as e:
        return {
            "text": "",
            "pages": [],
            "total_pages": 0,
            "total_chars": 0,
            "total_words": 0,
            "success": False,
            "error": str(e)
        }


def get_pdf_metadata(pdf_data: bytes) -> Dict:
    """
    Extract metadata from a PDF file
    
    Args:
        pdf_data: PDF file as bytes
    
    Returns:
        dict: PDF metadata
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
            "page_count": len(doc),
            "is_encrypted": doc.is_encrypted,
            "is_pdf": doc.is_pdf,
            "permissions": doc.permissions,
            "success": True
        }
        
        doc.close()
        
        return metadata
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def pdf_to_images(
    pdf_data: bytes,
    dpi: int = 150,
    fmt: str = "png"
) -> Dict:
    """
    Convert PDF pages to images
    
    Args:
        pdf_data: PDF file as bytes
        dpi: Resolution for image conversion
        fmt: Output format (png, jpg)
    
    Returns:
        dict: List of images as bytes
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        images = []
        zoom = dpi / 72  # PDF default is 72 DPI
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=fmt.upper())
            img_bytes = img_byte_arr.getvalue()
            
            images.append({
                "page": page_num + 1,
                "image": img_bytes,
                "width": pix.width,
                "height": pix.height,
                "size": len(img_bytes)
            })
        
        doc.close()
        
        return {
            "images": images,
            "total_pages": len(images),
            "format": fmt,
            "dpi": dpi,
            "success": True
        }
    
    except Exception as e:
        return {
            "images": [],
            "total_pages": 0,
            "success": False,
            "error": str(e)
        }


def extract_images_from_pdf(pdf_data: bytes) -> Dict:
    """
    Extract all embedded images from a PDF
    
    Args:
        pdf_data: PDF file as bytes
    
    Returns:
        dict: List of extracted images
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        images = []
        image_count = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                
                image_count += 1
                images.append({
                    "page": page_num + 1,
                    "image_index": img_index + 1,
                    "image_data": base_image["image"],
                    "extension": base_image["ext"],
                    "width": base_image["width"],
                    "height": base_image["height"],
                    "colorspace": base_image["colorspace"],
                    "size": len(base_image["image"])
                })
        
        doc.close()
        
        return {
            "images": images,
            "total_images": image_count,
            "success": True
        }
    
    except Exception as e:
        return {
            "images": [],
            "total_images": 0,
            "success": False,
            "error": str(e)
        }


def split_pdf(
    pdf_data: bytes,
    start_page: int,
    end_page: int
) -> Dict:
    """
    Extract pages from a PDF
    
    Args:
        pdf_data: PDF file as bytes
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed)
    
    Returns:
        dict: New PDF as bytes
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        # Validate page numbers
        if start_page < 1 or end_page > len(doc) or start_page > end_page:
            return {
                "success": False,
                "error": f"Invalid page range. PDF has {len(doc)} pages."
            }
        
        # Create new PDF with selected pages
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
        
        # Save to bytes
        pdf_bytes = new_doc.tobytes()
        
        doc.close()
        new_doc.close()
        
        return {
            "pdf": pdf_bytes,
            "original_pages": len(doc),
            "extracted_pages": end_page - start_page + 1,
            "size": len(pdf_bytes),
            "success": True
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def merge_pdfs(pdf_files: List[bytes]) -> Dict:
    """
    Merge multiple PDF files into one
    
    Args:
        pdf_files: List of PDF files as bytes
    
    Returns:
        dict: Merged PDF as bytes
    """
    try:
        if not pdf_files:
            return {
                "success": False,
                "error": "No PDF files provided"
            }
        
        merged_doc = fitz.open()
        total_pages = 0
        
        for pdf_data in pdf_files:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            merged_doc.insert_pdf(doc)
            total_pages += len(doc)
            doc.close()
        
        # Save to bytes
        pdf_bytes = merged_doc.tobytes()
        
        merged_doc.close()
        
        return {
            "pdf": pdf_bytes,
            "input_files": len(pdf_files),
            "total_pages": total_pages,
            "size": len(pdf_bytes),
            "success": True
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def compress_pdf(
    pdf_data: bytes,
    image_quality: int = 75
) -> Dict:
    """
    Compress PDF by reducing image quality
    
    Args:
        pdf_data: PDF file as bytes
        image_quality: JPEG quality (1-100)
    
    Returns:
        dict: Compressed PDF as bytes
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        # Compress images in PDF
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get images on page
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                # Extract and compress image
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                img_pil = Image.open(io.BytesIO(image_bytes))
                
                # Compress
                output = io.BytesIO()
                img_pil.save(output, format="JPEG", quality=image_quality, optimize=True)
                compressed_bytes = output.getvalue()
                
                # Replace image in PDF
                doc._deleteObject(xref)
                page.insert_image(
                    page.rect,
                    stream=compressed_bytes,
                    xref=xref
                )
        
        # Save compressed PDF
        pdf_bytes = doc.tobytes(
            garbage=4,
            deflate=True,
            clean=True
        )
        
        original_size = len(pdf_data)
        compressed_size = len(pdf_bytes)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        doc.close()
        
        return {
            "pdf": pdf_bytes,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(compression_ratio, 2),
            "success": True
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def add_watermark(
    pdf_data: bytes,
    watermark_text: str,
    opacity: float = 0.3
) -> Dict:
    """
    Add text watermark to all pages
    
    Args:
        pdf_data: PDF file as bytes
        watermark_text: Text to use as watermark
        opacity: Watermark opacity (0-1)
    
    Returns:
        dict: Watermarked PDF as bytes
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Calculate center position
            rect = page.rect
            center_x = rect.width / 2
            center_y = rect.height / 2
            
            # Add watermark
            text_point = fitz.Point(center_x, center_y)
            
            page.insert_text(
                text_point,
                watermark_text,
                fontsize=50,
                rotate=45,
                color=(0.5, 0.5, 0.5),
                overlay=True
            )
        
        # Save watermarked PDF
        pdf_bytes = doc.tobytes()
        
        doc.close()
        
        return {
            "pdf": pdf_bytes,
            "pages_watermarked": len(doc),
            "watermark_text": watermark_text,
            "size": len(pdf_bytes),
            "success": True
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_pdf_info(pdf_data: bytes) -> Dict:
    """
    Get comprehensive PDF information
    
    Args:
        pdf_data: PDF file as bytes
    
    Returns:
        dict: Detailed PDF information
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        # Count total images
        total_images = 0
        for page in doc:
            total_images += len(page.get_images())
        
        # Get page sizes
        page_sizes = []
        for page_num in range(min(5, len(doc))):  # First 5 pages
            page = doc[page_num]
            page_sizes.append({
                "page": page_num + 1,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2)
            })
        
        info = {
            "file_size": len(pdf_data),
            "page_count": len(doc),
            "total_images": total_images,
            "is_encrypted": doc.is_encrypted,
            "is_pdf": doc.is_pdf,
            "page_sizes": page_sizes,
            "metadata": {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", "")
            },
            "success": True
        }
        
        doc.close()
        
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

