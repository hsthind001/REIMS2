import fitz
from typing import Dict, List
import io


class PyMuPDFEngine:
    """PyMuPDF extraction engine - Fast and reliable for digital PDFs"""
    
    def __init__(self):
        self.name = "pymupdf"
        self.version = fitz.VersionBind
    
    def extract_text(self, pdf_data: bytes) -> Dict:
        """Extract text from PDF"""
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
                "engine": self.name,
                "text": full_text,
                "pages": pages,
                "total_pages": len(pages),
                "total_words": len(full_text.split()),
                "total_chars": len(full_text),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.name,
                "text": "",
                "pages": [],
                "total_pages": 0,
                "success": False,
                "error": str(e)
            }
    
    def extract_tables(self, pdf_data: bytes) -> Dict:
        """Extract tables from PDF (basic implementation)"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            tables = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text with positioning
                text_dict = page.get_text("dict")
                
                # Simple table detection (basic heuristic)
                # This is simplified - real table detection is complex
                page_tables = self._detect_tables(text_dict)
                
                if page_tables:
                    tables.extend(page_tables)
            
            doc.close()
            
            return {
                "engine": self.name,
                "tables": tables,
                "total_tables": len(tables),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.name,
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def _detect_tables(self, text_dict: Dict) -> List[Dict]:
        """Basic table detection heuristic"""
        # Simplified - PDFPlumber and Camelot are better for tables
        return []
    
    def get_metadata(self, pdf_data: bytes) -> Dict:
        """Extract PDF metadata"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            metadata = {
                "engine": self.name,
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
                "engine": self.name,
                "success": False,
                "error": str(e)
            }

