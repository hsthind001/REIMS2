"""
PDF to Image Conversion Utility

Converts PDF pages to PIL Images for LayoutLMv3 processing.
"""

from typing import List, Dict, Any
from PIL import Image
import pdf2image
import io
import tempfile
import os


class PDFToImageConverter:
    """Convert PDF pages to images for AI model processing"""
    
    def __init__(self, dpi: int = 200):
        """
        Initialize the PDF to Image converter.
        
        Args:
            dpi: Dots per inch for image quality (default: 200)
                 Higher DPI = better quality but slower processing
                 LayoutLMv3 works well with 150-300 DPI
        """
        self.dpi = dpi
    
    def convert_pdf_to_images(
        self,
        pdf_data: bytes,
        first_page: int = 1,
        last_page: int = None
    ) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images.
        
        Args:
            pdf_data: PDF file as bytes
            first_page: First page to convert (1-indexed)
            last_page: Last page to convert (None = all pages)
        
        Returns:
            List of PIL Image objects
        """
        try:
            # Save PDF temporarily (pdf2image requires file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            # Convert pages to images
            images = pdf2image.convert_from_path(
                tmp_path,
                dpi=self.dpi,
                first_page=first_page,
                last_page=last_page,
                fmt='PIL'  # Return as PIL Images
            )
            
            # Cleanup temp file
            os.unlink(tmp_path)
            
            return images
        
        except Exception as e:
            # Cleanup on error
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            raise Exception(f"PDF to image conversion failed: {str(e)}")
    
    def convert_page_to_image(
        self,
        pdf_data: bytes,
        page_number: int
    ) -> Image.Image:
        """
        Convert a single PDF page to PIL Image.
        
        Args:
            pdf_data: PDF file as bytes
            page_number: Page number to convert (1-indexed)
        
        Returns:
            PIL Image object
        """
        images = self.convert_pdf_to_images(
            pdf_data,
            first_page=page_number,
            last_page=page_number
        )
        
        if images and len(images) > 0:
            return images[0]
        else:
            raise Exception(f"Failed to convert page {page_number}")
    
    def convert_with_metadata(
        self,
        pdf_data: bytes,
        max_pages: int = None
    ) -> List[Dict[str, Any]]:
        """
        Convert PDF to images with metadata.
        
        Args:
            pdf_data: PDF file as bytes
            max_pages: Maximum pages to convert (None = all)
        
        Returns:
            List of dicts with image and metadata
        """
        try:
            # Convert pages
            last_page = max_pages if max_pages else None
            images = self.convert_pdf_to_images(pdf_data, last_page=last_page)
            
            # Build result with metadata
            results = []
            for idx, image in enumerate(images, 1):
                results.append({
                    "page_number": idx,
                    "image": image,
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "dpi": self.dpi
                })
            
            return results
        
        except Exception as e:
            raise Exception(f"PDF conversion with metadata failed: {str(e)}")
    
    def get_page_count(self, pdf_data: bytes) -> int:
        """
        Get number of pages in PDF without full conversion.
        
        Args:
            pdf_data: PDF file as bytes
        
        Returns:
            Number of pages
        """
        try:
            import fitz  # PyMuPDF for quick page count
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            page_count = len(doc)
            doc.close()
            return page_count
        except:
            # Fallback: convert and count
            images = self.convert_pdf_to_images(pdf_data)
            return len(images)

