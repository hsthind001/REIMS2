"""
PDF Field Locator Service

Locates fields in PDF documents and highlights anomalies visually.
Works with LayoutLM coordinator for ML-based predictions.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.layoutlm_coordinator import LayoutLMCoordinator

logger = logging.getLogger(__name__)


class PDFFieldLocator:
    """
    Locates and highlights fields in PDF documents.

    Features:
    - ML-based coordinate prediction (LayoutLM)
    - Fallback to OCR-based search
    - Multi-page support
    - Coordinate caching
    - Anomaly highlighting
    """

    def __init__(self, db: Session):
        self.db = db
        self.layoutlm_coordinator = LayoutLMCoordinator(db)

    def locate_field(
        self,
        pdf_path: str,
        field_name: str,
        page_number: Optional[int] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Locate a field in a PDF document.

        Args:
            pdf_path: Path to PDF file
            field_name: Name of field to locate (e.g., "Total Revenue", "NOI")
            page_number: Specific page to search (None = search all pages)
            use_cache: Whether to use cached coordinates

        Returns:
            Dictionary with field location and metadata
        """
        try:
            # Try cache first if enabled
            if use_cache and page_number:
                cached = self.layoutlm_coordinator.get_cached_coordinates(
                    pdf_path, field_name, page_number
                )
                if cached:
                    logger.info(f"Found cached coordinates for {field_name}")
                    cached['page'] = page_number
                    return cached

            # If no page specified, search all pages
            if page_number is None:
                return self._locate_field_all_pages(pdf_path, field_name)

            # Predict coordinates using LayoutLM or fallback
            coordinates = self.layoutlm_coordinator.predict_field_coordinates(
                pdf_path=pdf_path,
                field_name=field_name,
                page_number=page_number,
                confidence_threshold=settings.LAYOUTLM_CONFIDENCE_THRESHOLD
            )

            if coordinates:
                coordinates['page'] = page_number
                return coordinates

            return None

        except Exception as e:
            logger.error(f"Error locating field {field_name}: {e}")
            return None

    def _locate_field_all_pages(
        self,
        pdf_path: str,
        field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Search for field across all pages of PDF."""
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    coordinates = self.layoutlm_coordinator.predict_field_coordinates(
                        pdf_path=pdf_path,
                        field_name=field_name,
                        page_number=page_num,
                        confidence_threshold=settings.LAYOUTLM_CONFIDENCE_THRESHOLD
                    )

                    if coordinates:
                        coordinates['page'] = page_num
                        logger.info(f"Found {field_name} on page {page_num}")
                        return coordinates

            logger.warning(f"Field {field_name} not found in any page")
            return None

        except Exception as e:
            logger.error(f"Error searching all pages: {e}")
            return None

    def locate_multiple_fields(
        self,
        pdf_path: str,
        field_names: List[str],
        page_number: Optional[int] = None
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Locate multiple fields in a PDF document.

        Args:
            pdf_path: Path to PDF file
            field_names: List of field names to locate
            page_number: Specific page to search (None = search all pages)

        Returns:
            Dictionary mapping field names to their coordinates
        """
        results = {}

        for field_name in field_names:
            coordinates = self.locate_field(pdf_path, field_name, page_number)
            results[field_name] = coordinates

        return results

    def highlight_anomaly_field(
        self,
        pdf_path: str,
        field_name: str,
        anomaly_value: Any,
        expected_value: Optional[Any] = None,
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Locate and prepare highlighting data for an anomalous field.

        Args:
            pdf_path: Path to PDF file
            field_name: Name of anomalous field
            anomaly_value: Detected anomalous value
            expected_value: Expected value (optional)
            page_number: Page number to search

        Returns:
            Dictionary with highlighting information
        """
        try:
            # Locate the field
            coordinates = self.locate_field(pdf_path, field_name, page_number)

            if not coordinates:
                logger.warning(f"Could not locate field {field_name} for highlighting")
                return {
                    'field_name': field_name,
                    'located': False,
                    'anomaly_value': anomaly_value,
                    'expected_value': expected_value
                }

            # Determine highlight color based on severity
            highlight_info = {
                'field_name': field_name,
                'located': True,
                'page': coordinates['page'],
                'coordinates': {
                    'x': coordinates['x'],
                    'y': coordinates['y'],
                    'width': coordinates['width'],
                    'height': coordinates['height']
                },
                'confidence': coordinates['confidence'],
                'method': coordinates['method'],
                'anomaly_value': anomaly_value,
                'expected_value': expected_value,
                'highlight_color': self._get_highlight_color(anomaly_value, expected_value)
            }

            return highlight_info

        except Exception as e:
            logger.error(f"Error highlighting anomaly field: {e}")
            return {
                'field_name': field_name,
                'located': False,
                'error': str(e)
            }

    def _get_highlight_color(
        self,
        anomaly_value: Any,
        expected_value: Optional[Any] = None
    ) -> str:
        """
        Determine highlight color based on severity.

        Returns:
            Hex color code for highlighting
        """
        if expected_value is None:
            return "#FF6B6B"  # Red for unknown severity

        try:
            # Calculate percentage deviation
            anomaly_val = float(anomaly_value)
            expected_val = float(expected_value)

            if expected_val == 0:
                deviation = abs(anomaly_val)
            else:
                deviation = abs((anomaly_val - expected_val) / expected_val) * 100

            # Color based on deviation
            if deviation >= 50:
                return "#FF0000"  # Bright red - critical
            elif deviation >= 25:
                return "#FF6B6B"  # Red - high
            elif deviation >= 10:
                return "#FFA500"  # Orange - medium
            else:
                return "#FFFF00"  # Yellow - low

        except (ValueError, TypeError):
            return "#FF6B6B"  # Default red

    def get_pdf_page_dimensions(self, pdf_path: str, page_number: int = 1) -> Dict[str, float]:
        """
        Get dimensions of a PDF page.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)

        Returns:
            Dictionary with width and height
        """
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                if page_number > len(pdf.pages):
                    raise ValueError(f"Page {page_number} does not exist")

                page = pdf.pages[page_number - 1]
                return {
                    'width': page.width,
                    'height': page.height,
                    'page': page_number
                }

        except Exception as e:
            logger.error(f"Error getting page dimensions: {e}")
            return {'width': 612, 'height': 792, 'page': page_number}  # Default US Letter

    def create_highlight_overlay(
        self,
        pdf_path: str,
        highlights: List[Dict[str, Any]]
    ) -> Optional[bytes]:
        """
        Create PDF overlay with highlighted fields.

        Args:
            pdf_path: Path to original PDF
            highlights: List of highlight information dictionaries

        Returns:
            PDF bytes with overlays, or None if error
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from io import BytesIO
            import PyPDF2

            # TODO: Implement PDF overlay creation
            # This is a placeholder for future implementation

            logger.warning("PDF overlay creation not yet implemented - placeholder")
            return None

        except Exception as e:
            logger.error(f"Error creating highlight overlay: {e}")
            return None

    def extract_field_value(
        self,
        pdf_path: str,
        field_name: str,
        page_number: Optional[int] = None
    ) -> Optional[str]:
        """
        Extract the value of a field from PDF.

        Args:
            pdf_path: Path to PDF file
            field_name: Name of field
            page_number: Page number to search

        Returns:
            Extracted value as string, or None
        """
        try:
            # Locate the field first
            coordinates = self.locate_field(pdf_path, field_name, page_number)

            if not coordinates:
                return None

            # Extract text near the coordinates
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[coordinates['page'] - 1]

                # Define extraction area (slightly expanded)
                x0 = coordinates['x'] - 10
                y0 = coordinates['y'] - 5
                x1 = coordinates['x'] + coordinates['width'] + 100  # Extend right for value
                y1 = coordinates['y'] + coordinates['height'] + 5

                # Crop and extract
                crop = page.crop((x0, y0, x1, y1))
                text = crop.extract_text()

                if text:
                    # Clean and return
                    return text.strip()

            return None

        except Exception as e:
            logger.error(f"Error extracting field value: {e}")
            return None

    def batch_locate_fields(
        self,
        pdf_paths: List[str],
        field_names: List[str]
    ) -> Dict[str, Dict[str, Optional[Dict[str, Any]]]]:
        """
        Batch locate fields across multiple PDFs.

        Args:
            pdf_paths: List of PDF file paths
            field_names: List of field names to locate

        Returns:
            Nested dictionary: {pdf_path: {field_name: coordinates}}
        """
        results = {}

        for pdf_path in pdf_paths:
            results[pdf_path] = self.locate_multiple_fields(pdf_path, field_names)

        return results
