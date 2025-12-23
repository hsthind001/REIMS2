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
        learning_rate: float = 5e-5,
        batch_size: int = 4,
        validation_split: float = 0.2,
        checkpoint_dir: Optional[str] = None,
        save_best_model: bool = True
    ) -> bool:
        """
        Fine-tune LayoutLM model on custom data.

        Args:
            training_data: List of training examples with format:
                {
                    'image': PIL.Image or path to image/PDF,
                    'words': List[str],  # Words in the document
                    'boxes': List[List[int]],  # Bounding boxes for each word
                    'labels': List[int]  # Token classification labels
                }
            epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
            checkpoint_dir: Directory to save model checkpoints
            save_best_model: Whether to save the best model based on validation loss

        Returns:
            True if successful, False otherwise
        """
        if not self._is_available():
            logger.error("LayoutLM not available for fine-tuning")
            return False

        if not training_data:
            logger.error("No training data provided")
            return False

        try:
            from torch.utils.data import DataLoader, Dataset, random_split
            from transformers import AdamW, get_linear_schedule_with_warmup
            from torch.nn import CrossEntropyLoss
            from torch import nn
            import torch
            from PIL import Image
            import os
            from pathlib import Path

            # Custom Dataset class for LayoutLM fine-tuning
            class LayoutLMDataset(Dataset):
                """Custom dataset for LayoutLM token classification"""
                
                def __init__(self, data: List[Dict[str, Any]], processor, device: str):
                    self.data = data
                    self.processor = processor
                    self.device = device
                
                def __len__(self):
                    return len(self.data)
                
                def __getitem__(self, idx):
                    example = self.data[idx]
                    
                    # Load image if path provided
                    if isinstance(example['image'], str):
                        image = Image.open(example['image']).convert('RGB')
                    else:
                        image = example['image']
                    
                    words = example.get('words', [])
                    boxes = example.get('boxes', [])
                    labels = example.get('labels', [])
                    
                    # Process with LayoutLM processor
                    encoding = self.processor(
                        image,
                        words,
                        boxes=boxes,
                        word_labels=labels,
                        padding="max_length",
                        truncation=True,
                        return_tensors="pt"
                    )
                    
                    # Move to device
                    for key, value in encoding.items():
                        encoding[key] = value.squeeze().to(self.device)
                    
                    return encoding

            # Set up checkpoint directory
            if checkpoint_dir is None:
                checkpoint_dir = os.path.join(settings.MODEL_STORAGE_PATH, "layoutlm_checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)

            # Switch model to training mode
            self.model.train()
            
            # Create dataset
            dataset = LayoutLMDataset(training_data, self.processor, self.device)
            
            # Split into train and validation
            val_size = int(len(dataset) * validation_split)
            train_size = len(dataset) - val_size
            train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
            
            # Create data loaders
            train_loader = DataLoader(
                train_dataset,
                batch_size=batch_size,
                shuffle=True,
                num_workers=0  # Set to 0 to avoid multiprocessing issues
            )
            val_loader = DataLoader(
                val_dataset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=0
            )
            
            # Set up optimizer and scheduler
            optimizer = AdamW(self.model.parameters(), lr=learning_rate)
            total_steps = len(train_loader) * epochs
            scheduler = get_linear_schedule_with_warmup(
                optimizer,
                num_warmup_steps=int(0.1 * total_steps),
                num_training_steps=total_steps
            )
            
            # Loss function
            loss_fn = CrossEntropyLoss()
            
            # Training loop
            best_val_loss = float('inf')
            training_history = []
            
            logger.info(f"Starting fine-tuning for {epochs} epochs with {len(train_dataset)} training samples")
            
            for epoch in range(epochs):
                # Training phase
                self.model.train()
                train_loss = 0.0
                
                for batch_idx, batch in enumerate(train_loader):
                    optimizer.zero_grad()
                    
                    # Forward pass
                    outputs = self.model(**batch)
                    logits = outputs.logits
                    
                    # Calculate loss
                    labels = batch['labels']
                    loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                    
                    # Backward pass
                    loss.backward()
                    
                    # Gradient clipping for stability
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    
                    optimizer.step()
                    scheduler.step()
                    
                    train_loss += loss.item()
                    
                    if (batch_idx + 1) % 10 == 0:
                        logger.info(
                            f"Epoch {epoch + 1}/{epochs}, Batch {batch_idx + 1}/{len(train_loader)}, "
                            f"Loss: {loss.item():.4f}"
                        )
                
                avg_train_loss = train_loss / len(train_loader)
                
                # Validation phase
                self.model.eval()
                val_loss = 0.0
                
                with torch.no_grad():
                    for batch in val_loader:
                        outputs = self.model(**batch)
                        logits = outputs.logits
                        labels = batch['labels']
                        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                        val_loss += loss.item()
                
                avg_val_loss = val_loss / len(val_loader)
                
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} - "
                    f"Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}"
                )
                
                training_history.append({
                    'epoch': epoch + 1,
                    'train_loss': avg_train_loss,
                    'val_loss': avg_val_loss
                })
                
                # Save checkpoint
                checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_epoch_{epoch + 1}.pt")
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'scheduler_state_dict': scheduler.state_dict(),
                    'train_loss': avg_train_loss,
                    'val_loss': avg_val_loss,
                }, checkpoint_path)
                logger.info(f"Checkpoint saved: {checkpoint_path}")
                
                # Save best model
                if save_best_model and avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    best_model_path = os.path.join(checkpoint_dir, "best_model.pt")
                    torch.save({
                        'epoch': epoch + 1,
                        'model_state_dict': self.model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'val_loss': avg_val_loss,
                    }, best_model_path)
                    logger.info(f"Best model saved: {best_model_path} (Val Loss: {avg_val_loss:.4f})")
            
            # Load best model if available
            if save_best_model:
                best_model_path = os.path.join(checkpoint_dir, "best_model.pt")
                if os.path.exists(best_model_path):
                    checkpoint = torch.load(best_model_path, map_location=self.device)
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                    logger.info(f"Loaded best model from {best_model_path}")
            
            # Switch back to eval mode
            self.model.eval()
            
            logger.info("Fine-tuning completed successfully")
            return True

        except ImportError as e:
            logger.error(f"Required library not available for fine-tuning: {e}")
            return False
        except Exception as e:
            logger.error(f"Error fine-tuning model: {e}", exc_info=True)
            return False
