import pdfplumber
from typing import Dict, List
import io


class PDFPlumberEngine:
    """PDFPlumber extraction engine - Excellent for tables and structured data"""
    
    def __init__(self):
        self.name = "pdfplumber"
        self.version = pdfplumber.__version__
    
    def extract_text(self, pdf_data: bytes) -> Dict:
        """Extract text from PDF with layout preservation"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            pages = []
            all_text = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                
                pages.append({
                    "page": page_num,
                    "text": text,
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "width": page.width,
                    "height": page.height
                })
                
                all_text.append(text)
            
            full_text = "\n\n".join(all_text)
            
            pdf.close()
            
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
        """Extract tables from PDF - PDFPlumber's strength"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            all_tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                for table_index, table in enumerate(tables, 1):
                    if table:
                        # Convert table to dict format
                        table_dict = {
                            "page": page_num,
                            "table_index": table_index,
                            "rows": len(table),
                            "columns": len(table[0]) if table else 0,
                            "data": table
                        }
                        all_tables.append(table_dict)
            
            pdf.close()
            
            return {
                "engine": self.name,
                "tables": all_tables,
                "total_tables": len(all_tables),
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
    
    def extract_words_with_positions(self, pdf_data: bytes) -> Dict:
        """Extract words with exact positioning"""
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            
            all_words = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words()
                
                for word in words:
                    all_words.append({
                        "page": page_num,
                        "text": word.get("text", ""),
                        "x0": word.get("x0", 0),
                        "y0": word.get("y0", 0),
                        "x1": word.get("x1", 0),
                        "y1": word.get("y1", 0),
                        "top": word.get("top", 0),
                        "bottom": word.get("bottom", 0)
                    })
            
            pdf.close()
            
            return {
                "engine": self.name,
                "words": all_words,
                "total_words": len(all_words),
                "success": True
            }
        
        except Exception as e:
            return {
                "engine": self.name,
                "words": [],
                "total_words": 0,
                "success": False,
                "error": str(e)
            }

