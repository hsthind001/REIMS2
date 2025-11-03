import camelot
from typing import Dict, List
import io
import tempfile
import os


class CamelotEngine:
    """Camelot extraction engine - Best for table extraction"""
    
    def __init__(self):
        self.name = "camelot"
        self.version = "1.0.9"
    
    def extract_tables(self, pdf_data: bytes, flavor: str = "lattice") -> Dict:
        """
        Extract tables from PDF
        
        Args:
            pdf_data: PDF file as bytes
            flavor: 'lattice' (bordered tables) or 'stream' (borderless tables)
        
        Returns:
            dict: Extracted tables
        """
        try:
            # Camelot requires a file path, so save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            # Extract tables
            tables = camelot.read_pdf(tmp_path, flavor=flavor, pages="all")
            
            all_tables = []
            
            for table_num, table in enumerate(tables, 1):
                # Convert table to list of lists
                data = table.df.values.tolist()
                headers = table.df.columns.tolist()
                
                all_tables.append({
                    "table_index": table_num,
                    "page": table.page,
                    "headers": headers,
                    "data": data,
                    "rows": len(data),
                    "columns": len(headers),
                    "accuracy": table.parsing_report.get("accuracy", 0),
                    "whitespace": table.parsing_report.get("whitespace", 0)
                })
            
            # Cleanup
            os.unlink(tmp_path)
            
            return {
                "engine": self.name,
                "flavor": flavor,
                "tables": all_tables,
                "total_tables": len(all_tables),
                "success": True
            }
        
        except Exception as e:
            # Cleanup on error
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return {
                "engine": self.name,
                "flavor": flavor,
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def extract_tables_both_methods(self, pdf_data: bytes) -> Dict:
        """Try both lattice and stream methods and return best results"""
        lattice_result = self.extract_tables(pdf_data, flavor="lattice")
        stream_result = self.extract_tables(pdf_data, flavor="stream")
        
        # Use whichever found more tables
        if lattice_result["total_tables"] >= stream_result["total_tables"]:
            return lattice_result
        else:
            return stream_result

