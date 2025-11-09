import camelot
from typing import Dict, List, Any
from decimal import Decimal
import io
import tempfile
import os
from app.utils.engines.base_extractor import BaseExtractor, ExtractionResult


class CamelotEngine(BaseExtractor):
    """Camelot extraction engine - Best for complex table extraction with high accuracy"""
    
    def __init__(self):
        super().__init__(engine_name="camelot")
        self.version = "1.0.9"
    
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract data from PDF using Camelot.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Optional parameters
                - flavor: 'lattice' (bordered) or 'stream' (borderless) or 'both'
                - pages: Page numbers to extract (default: "all")
        
        Returns:
            ExtractionResult with tables, confidence scores, and metadata
        """
        self._start_timer()
        
        flavor = kwargs.get("flavor", "both")
        pages = kwargs.get("pages", "all")
        
        try:
            # Extract tables
            if flavor == "both":
                tables_result = self._extract_tables_both_methods_internal(pdf_data, pages)
            else:
                tables_result = self._extract_tables_internal(pdf_data, flavor, pages)
            
            if not tables_result["success"]:
                return ExtractionResult(
                    engine_name=self.engine_name,
                    extracted_data={},
                    success=False,
                    error_message=tables_result.get("error", "Unknown error"),
                    processing_time_ms=self._get_processing_time_ms()
                )
            
            # Prepare extracted data
            extracted_data = {
                "tables": tables_result["tables"],
                "total_tables": tables_result["total_tables"],
                "flavor": tables_result.get("flavor", flavor),
            }
            
            # Calculate confidence score
            confidence = self.calculate_confidence(extracted_data)
            
            # Calculate table confidence using Camelot's accuracy scores
            table_confidence = self._calculate_camelot_table_confidence(
                tables_result["tables"]
            )
            
            # Build confidence breakdown
            confidence_breakdown = {
                "table_detection": table_confidence,
                "parsing_accuracy": self._get_average_accuracy(tables_result["tables"]),
            }
            
            # Prepare engine metadata
            engine_metadata = {
                "camelot_version": self.version,
                "table_count": tables_result["total_tables"],
                "extraction_flavor": tables_result.get("flavor", flavor),
                "parsing_method": "lattice" if "lattice" in str(flavor) else "stream",
                "handles_merged_cells": True
            }
            
            # Add accuracy stats to metadata
            if tables_result["tables"]:
                accuracies = [t.get("accuracy", 0) for t in tables_result["tables"]]
                engine_metadata["avg_accuracy"] = sum(accuracies) / len(accuracies) if accuracies else 0
                engine_metadata["min_accuracy"] = min(accuracies) if accuracies else 0
                engine_metadata["max_accuracy"] = max(accuracies) if accuracies else 0
            
            # Add warnings for low accuracy tables
            warnings = []
            for table in tables_result["tables"]:
                accuracy = table.get("accuracy", 0)
                if accuracy < 80:
                    warnings.append(
                        f"Table {table.get('table_index')} on page {table.get('page')} "
                        f"has low accuracy: {accuracy:.1f}%"
                    )
            
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data=extracted_data,
                success=True,
                confidence_score=confidence,
                confidence_breakdown=confidence_breakdown,
                processing_time_ms=self._get_processing_time_ms(),
                page_count=self._count_pages_from_tables(tables_result["tables"]),
                table_detection_score=table_confidence,
                engine_metadata=engine_metadata,
                warnings=warnings
            )
        
        except Exception as e:
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data={},
                success=False,
                error_message=str(e),
                processing_time_ms=self._get_processing_time_ms()
            )
    
    def calculate_confidence(self, extraction_data: Dict[str, Any]) -> Decimal:
        """
        Calculate confidence score for Camelot extraction.
        
        Camelot provides its own accuracy scores in parsing_report,
        which we use as the primary confidence indicator.
        
        Args:
            extraction_data: Dictionary with extracted tables and metadata
        
        Returns:
            Confidence score as Decimal (0.0 - 1.0)
        """
        tables = extraction_data.get("tables", [])
        
        if not tables or len(tables) == 0:
            return Decimal('0.0')
        
        # Get Camelot's accuracy scores
        accuracies = []
        for table in tables:
            accuracy = table.get("accuracy", 0)
            # Camelot accuracy is 0-100, convert to 0.0-1.0
            accuracies.append(accuracy / 100.0)
        
        # Calculate average accuracy
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        # Adjust based on number of tables (more tables = more reliable extraction)
        table_count_factor = min(1.0, 0.5 + (len(tables) * 0.1))  # 0.5-1.0 scale
        
        # Adjust for merged cells (if detected, lower confidence slightly)
        merged_cell_penalty = 0.0
        for table in tables:
            if table.get("has_merged_cells", False):
                merged_cell_penalty += 0.05  # 5% penalty per table with merged cells
        
        # Calculate final confidence
        final_confidence = avg_accuracy * table_count_factor * (1 - min(merged_cell_penalty, 0.3))
        
        return Decimal(str(round(final_confidence, 4)))
    
    # Helper methods for Camelot-specific confidence calculations
    
    def _calculate_camelot_table_confidence(self, tables: List[Dict]) -> float:
        """
        Calculate table confidence using Camelot's accuracy scores.
        
        Args:
            tables: List of extracted tables with accuracy scores
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not tables:
            return 0.0
        
        # Use Camelot's built-in accuracy metric
        accuracies = [t.get("accuracy", 0) / 100.0 for t in tables]
        
        if not accuracies:
            return 0.0
        
        # Weighted average (favor higher accuracies)
        sorted_acc = sorted(accuracies, reverse=True)
        weights = [1.0 / (i + 1) for i in range(len(sorted_acc))]
        total_weight = sum(weights)
        
        weighted_avg = sum(a * w for a, w in zip(sorted_acc, weights)) / total_weight
        
        return weighted_avg
    
    def _get_average_accuracy(self, tables: List[Dict]) -> float:
        """Get average accuracy score from tables"""
        if not tables:
            return 0.0
        
        accuracies = [t.get("accuracy", 0) for t in tables]
        return sum(accuracies) / len(accuracies) if accuracies else 0.0
    
    def _count_pages_from_tables(self, tables: List[Dict]) -> int:
        """Count unique pages from table list"""
        if not tables:
            return 0
        
        pages = set(t.get("page", 0) for t in tables)
        return len(pages)
    
    def _detect_merged_cells(self, table_data: List[List]) -> bool:
        """
        Detect if table contains merged cells.
        
        Heuristic: Check for repeated values across adjacent cells
        or empty cells that might indicate spanning.
        
        Args:
            table_data: 2D list of table cells
        
        Returns:
            True if merged cells suspected
        """
        if not table_data or len(table_data) < 2:
            return False
        
        # Check for repeated values in consecutive rows (vertical merge indicator)
        for col_idx in range(len(table_data[0])):
            prev_value = None
            repeat_count = 0
            
            for row in table_data:
                if col_idx < len(row):
                    current_value = row[col_idx]
                    if current_value == prev_value and current_value != "" and current_value is not None:
                        repeat_count += 1
                        if repeat_count >= 2:
                            return True
                    else:
                        repeat_count = 0
                    prev_value = current_value
        
        # Check for unusual empty cell patterns (horizontal merge indicator)
        for row in table_data:
            empty_count = sum(1 for cell in row if cell == "" or cell is None)
            # If more than 30% cells empty in a row, might indicate merging
            if len(row) > 0 and (empty_count / len(row)) > 0.3:
                return True
        
        return False
    
    # Legacy methods (kept for backwards compatibility)
    
    def extract_tables(self, pdf_data: bytes, flavor: str = "lattice") -> Dict:
        """
        Extract tables from PDF (legacy method).
        
        NOTE: Use extract() method instead for new code.
        """
        return self._extract_tables_internal(pdf_data, flavor, "all")
    
    def extract_tables_both_methods(self, pdf_data: bytes) -> Dict:
        """
        Try both lattice and stream methods (legacy method).
        
        NOTE: Use extract() method with flavor="both" instead.
        """
        return self._extract_tables_both_methods_internal(pdf_data, "all")
    
    # Internal implementation methods
    
    def _extract_tables_internal(self, pdf_data: bytes, flavor: str, pages: str) -> Dict:
        """Internal table extraction implementation"""
        try:
            # Camelot requires a file path, so save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            # Extract tables
            tables = camelot.read_pdf(tmp_path, flavor=flavor, pages=pages)
            
            all_tables = []
            
            for table_num, table in enumerate(tables, 1):
                # Convert table to list of lists
                data = table.df.values.tolist()
                headers = table.df.columns.tolist()
                
                # Detect merged cells
                has_merged = self._detect_merged_cells(data)
                
                all_tables.append({
                    "table_index": table_num,
                    "page": table.page,
                    "headers": headers,
                    "data": data,
                    "rows": len(data),
                    "columns": len(headers),
                    "accuracy": table.parsing_report.get("accuracy", 0),
                    "whitespace": table.parsing_report.get("whitespace", 0),
                    "has_merged_cells": has_merged
                })
            
            # Cleanup
            os.unlink(tmp_path)
            
            return {
                "engine": self.engine_name,
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
                "engine": self.engine_name,
                "flavor": flavor,
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def _extract_tables_both_methods_internal(self, pdf_data: bytes, pages: str) -> Dict:
        """Internal implementation trying both lattice and stream methods"""
        lattice_result = self._extract_tables_internal(pdf_data, "lattice", pages)
        stream_result = self._extract_tables_internal(pdf_data, "stream", pages)
        
        # Compare results and choose best
        if not lattice_result["success"] and not stream_result["success"]:
            return lattice_result  # Return error from lattice
        
        if not lattice_result["success"]:
            stream_result["flavor"] = "stream (fallback)"
            return stream_result
        
        if not stream_result["success"]:
            lattice_result["flavor"] = "lattice (fallback)"
            return lattice_result
        
        # Both succeeded - choose based on accuracy
        lattice_avg_acc = self._get_average_accuracy(lattice_result["tables"])
        stream_avg_acc = self._get_average_accuracy(stream_result["tables"])
        
        if lattice_avg_acc >= stream_avg_acc:
            lattice_result["flavor"] = "lattice (best)"
            return lattice_result
        else:
            stream_result["flavor"] = "stream (best)"
            return stream_result
