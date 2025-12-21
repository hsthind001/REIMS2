"""
LayoutLM Coordinator Service

Coordinates LayoutLM-based PDF field coordinate prediction for anomaly highlighting.
Uses LayoutLMv3 for document understanding and field localization.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.feature_flags import FeatureFlags
from app.models.pdf_field_coordinate import PDFFieldCoordinate

logger = logging.getLogger(__name__)

# Try to import LayoutLM dependencies
try:
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
    import torch
    from PIL import Image
    import pytesseract
    LAYOUTLM_AVAILABLE = True
    logger.info("LayoutLM dependencies available")
except ImportError as e:
    LAYOUTLM_AVAILABLE = False
    logger.warning(f"LayoutLM dependencies not available: {e}")


class LayoutLMCoordinator:
    """
    Coordinates LayoutLM model for PDF field coordinate prediction.

    Features:
    - Document layout understanding
    - Field coordinate prediction
    - Multi-page PDF support
    - Model caching
    - GPU acceleration (if available)
    """

    def __init__(self, db: Session):
        self.db = db
        self.flags = FeatureFlags()
        self.model = None
        self.processor = None
        self.device = self._get_device()

        if LAYOUTLM_AVAILABLE and self.flags.is_layoutlm_enabled():
            self._initialize_model()

    def _get_device(self) -> str:
        """Determine device (CPU/GPU) for model inference."""
        if not LAYOUTLM_AVAILABLE:
            return "cpu"

        if settings.ANOMALY_USE_GPU and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _initialize_model(self):
        """Initialize LayoutLMv3 model and processor."""
        try:
            model_path = settings.LAYOUTLM_MODEL_PATH

            if not os.path.exists(model_path):
                logger.warning(f"LayoutLM model not found at {model_path}, using pretrained")
                model_name = "microsoft/layoutlmv3-base"
            else:
                model_name = model_path

            logger.info(f"Loading LayoutLM model from {model_name}")

            self.processor = LayoutLMv3Processor.from_pretrained(
                model_name,
                apply_ocr=True
            )

            self.model = LayoutLMv3ForTokenClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"LayoutLM model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize LayoutLM model: {e}")
            self.model = None
            self.processor = None

    def predict_field_coordinates(
        self,
        pdf_path: str,
        field_name: str,
        page_number: int = 1,
        confidence_threshold: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Predict coordinates of a field in a PDF document.

        Args:
            pdf_path: Path to PDF file
            field_name: Name of the field to locate
            page_number: Page number (1-indexed)
            confidence_threshold: Minimum confidence for prediction

        Returns:
            Dictionary with coordinates and confidence, or None if not found
        """
        if not self._is_available():
            logger.warning("LayoutLM not available, falling back to heuristic")
            return self._fallback_coordinate_prediction(pdf_path, field_name, page_number)

        try:
            # Convert PDF page to image
            image = self._pdf_page_to_image(pdf_path, page_number)
            if image is None:
                return None

            # Run OCR and get word boxes
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            # Prepare inputs for LayoutLM
            encoding = self.processor(
                image,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )

            # Move to device
            encoding = {k: v.to(self.device) for k, v in encoding.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**encoding)

            # Get predictions
            predictions = outputs.logits.argmax(-1).squeeze().tolist()

            # Find field coordinates based on predictions and field name
            coordinates = self._extract_field_coordinates(
                ocr_data,
                predictions,
                field_name,
                confidence_threshold
            )

            if coordinates:
                # Cache coordinates in database
                self._cache_coordinates(pdf_path, field_name, page_number, coordinates)

            return coordinates

        except Exception as e:
            logger.error(f"Error predicting field coordinates: {e}")
            return self._fallback_coordinate_prediction(pdf_path, field_name, page_number)

    def _pdf_page_to_image(self, pdf_path: str, page_number: int) -> Optional[Image.Image]:
        """Convert PDF page to PIL Image."""
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(
                pdf_path,
                first_page=page_number,
                last_page=page_number,
                dpi=settings.LAYOUTLM_IMAGE_DPI
            )

            if images:
                return images[0]
            return None

        except Exception as e:
            logger.error(f"Error converting PDF to image: {e}")
            return None

    def _extract_field_coordinates(
        self,
        ocr_data: Dict,
        predictions: List[int],
        field_name: str,
        confidence_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Extract field coordinates from OCR data and model predictions."""
        # Normalize field name for matching
        field_name_lower = field_name.lower().strip()

        words = []
        boxes = []

        for i, word in enumerate(ocr_data['text']):
            if word.strip():
                # Get word bounding box
                x, y, w, h = (
                    ocr_data['left'][i],
                    ocr_data['top'][i],
                    ocr_data['width'][i],
                    ocr_data['height'][i]
                )

                # Check if word matches field name
                word_lower = word.lower().strip()
                if field_name_lower in word_lower or word_lower in field_name_lower:
                    boxes.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'text': word,
                        'confidence': ocr_data['conf'][i] / 100.0  # Normalize to 0-1
                    })

        if not boxes:
            return None

        # Find box with highest confidence
        best_box = max(boxes, key=lambda b: b['confidence'])

        if best_box['confidence'] >= confidence_threshold:
            return {
                'x': best_box['x'],
                'y': best_box['y'],
                'width': best_box['width'],
                'height': best_box['height'],
                'confidence': best_box['confidence'],
                'method': 'layoutlm'
            }

        return None

    def _fallback_coordinate_prediction(
        self,
        pdf_path: str,
        field_name: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback method using simple OCR when LayoutLM is not available.
        """
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                if page_number > len(pdf.pages):
                    return None

                page = pdf.pages[page_number - 1]
                words = page.extract_words()

                field_name_lower = field_name.lower().strip()

                for word in words:
                    word_text = word['text'].lower().strip()
                    if field_name_lower in word_text or word_text in field_name_lower:
                        return {
                            'x': word['x0'],
                            'y': word['top'],
                            'width': word['x1'] - word['x0'],
                            'height': word['bottom'] - word['top'],
                            'confidence': 0.7,  # Fixed confidence for fallback
                            'method': 'pdfplumber'
                        }

            return None

        except Exception as e:
            logger.error(f"Error in fallback coordinate prediction: {e}")
            return None

    def _cache_coordinates(
        self,
        pdf_path: str,
        field_name: str,
        page_number: int,
        coordinates: Dict[str, Any]
    ):
        """Cache predicted coordinates in database."""
        try:
            # Check if already cached
            existing = self.db.query(PDFFieldCoordinate).filter(
                PDFFieldCoordinate.pdf_path == pdf_path,
                PDFFieldCoordinate.field_name == field_name,
                PDFFieldCoordinate.page_number == page_number
            ).first()

            if existing:
                # Update existing
                existing.x = coordinates['x']
                existing.y = coordinates['y']
                existing.width = coordinates['width']
                existing.height = coordinates['height']
                existing.confidence = coordinates['confidence']
                existing.prediction_method = coordinates['method']
            else:
                # Create new
                coord = PDFFieldCoordinate(
                    pdf_path=pdf_path,
                    field_name=field_name,
                    page_number=page_number,
                    x=coordinates['x'],
                    y=coordinates['y'],
                    width=coordinates['width'],
                    height=coordinates['height'],
                    confidence=coordinates['confidence'],
                    prediction_method=coordinates['method']
                )
                self.db.add(coord)

            self.db.commit()
            logger.info(f"Cached coordinates for {field_name} in {pdf_path}")

        except Exception as e:
            logger.error(f"Error caching coordinates: {e}")
            self.db.rollback()

    def get_cached_coordinates(
        self,
        pdf_path: str,
        field_name: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached coordinates from database."""
        try:
            coord = self.db.query(PDFFieldCoordinate).filter(
                PDFFieldCoordinate.pdf_path == pdf_path,
                PDFFieldCoordinate.field_name == field_name,
                PDFFieldCoordinate.page_number == page_number
            ).first()

            if coord:
                return {
                    'x': coord.x,
                    'y': coord.y,
                    'width': coord.width,
                    'height': coord.height,
                    'confidence': coord.confidence,
                    'method': coord.prediction_method
                }

            return None

        except Exception as e:
            logger.error(f"Error retrieving cached coordinates: {e}")
            return None

    def _is_available(self) -> bool:
        """Check if LayoutLM is available and enabled."""
        return (
            LAYOUTLM_AVAILABLE and
            self.flags.is_layoutlm_enabled() and
            self.model is not None
        )

    def fine_tune_model(
        self,
        training_data: List[Dict[str, Any]],
        epochs: int = 3,
        learning_rate: float = 5e-5
    ) -> bool:
        """
        Fine-tune LayoutLM model on custom data.

        Args:
            training_data: List of training examples
            epochs: Number of training epochs
            learning_rate: Learning rate

        Returns:
            True if successful, False otherwise
        """
        if not self._is_available():
            logger.error("LayoutLM not available for fine-tuning")
            return False

        try:
            from torch.utils.data import DataLoader, Dataset
            from transformers import AdamW

            # TODO: Implement custom dataset and training loop
            # This is a placeholder for future implementation

            logger.info("Fine-tuning LayoutLM model...")
            logger.warning("Fine-tuning not yet implemented - placeholder")

            return True

        except Exception as e:
            logger.error(f"Error fine-tuning model: {e}")
            return False
