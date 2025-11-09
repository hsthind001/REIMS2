"""
LayoutLMv3 Extraction Engine

Uses Microsoft's LayoutLMv3 for AI-powered document understanding.
Excels at understanding document layout and structure.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from PIL import Image
import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from app.utils.engines.base_extractor import BaseExtractor, ExtractionResult
from app.utils.pdf_to_image import PDFToImageConverter


class LayoutLMEngine(BaseExtractor):
    """
    LayoutLMv3 extraction engine - AI-powered document understanding
    
    Best for: Complex layouts, forms, structured documents
    """
    
    def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
        """
        Initialize LayoutLM engine.
        
        Args:
            model_name: Hugging Face model identifier
        """
        super().__init__(engine_name="layoutlm")
        self.model_name = model_name
        self.processor = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pdf_converter = PDFToImageConverter(dpi=200)
        
        # Lazy loading - model loaded on first use
        self._model_loaded = False
    
    def _load_model(self):
        """Load LayoutLMv3 model and processor (lazy loading)"""
        if self._model_loaded:
            return
        
        print(f"🤖 Loading LayoutLMv3 model: {self.model_name}")
        print(f"   Device: {self.device}")
        
        self.processor = LayoutLMv3Processor.from_pretrained(self.model_name)
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode
        
        self._model_loaded = True
        print(f"✅ Model loaded successfully")
    
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract data from PDF using LayoutLMv3.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Optional parameters
                - max_pages: Maximum pages to process (default: None = all)
                - confidence_threshold: Minimum confidence for predictions (default: 0.5)
        
        Returns:
            ExtractionResult with extracted text, layout info, and confidence
        """
        self._start_timer()
        
        try:
            # Load model if not already loaded
            self._load_model()
            
            max_pages = kwargs.get("max_pages", None)
            confidence_threshold = kwargs.get("confidence_threshold", 0.5)
            
            # Convert PDF to images
            page_images = self.pdf_converter.convert_with_metadata(
                pdf_data,
                max_pages=max_pages
            )
            
            if not page_images:
                return ExtractionResult(
                    engine_name=self.engine_name,
                    extracted_data={},
                    success=False,
                    error_message="No pages converted from PDF",
                    processing_time_ms=self._get_processing_time_ms()
                )
            
            # Process each page
            all_text = []
            page_results = []
            total_confidence = 0.0
            
            for page_info in page_images:
                page_result = self._process_page(
                    page_info["image"],
                    page_info["page_number"],
                    confidence_threshold
                )
                
                page_results.append(page_result)
                all_text.append(page_result["text"])
                total_confidence += page_result["confidence"]
            
            # Aggregate results
            full_text = "\n\n".join(all_text)
            avg_confidence = total_confidence / len(page_results) if page_results else 0.0
            
            extracted_data = {
                "text": full_text,
                "pages": page_results,
                "total_pages": len(page_results),
                "total_words": len(full_text.split()),
                "total_chars": len(full_text),
                "layout_info": [p["layout_info"] for p in page_results]
            }
            
            # Calculate final confidence
            confidence = self.calculate_confidence(extracted_data)
            
            # Prepare metadata
            engine_metadata = {
                "model_name": self.model_name,
                "device": self.device,
                "dpi": self.pdf_converter.dpi,
                "pages_processed": len(page_results),
                "avg_page_confidence": round(avg_confidence, 4)
            }
            
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data=extracted_data,
                success=True,
                confidence_score=confidence,
                processing_time_ms=self._get_processing_time_ms(),
                page_count=len(page_results),
                text_quality_score=avg_confidence,
                engine_metadata=engine_metadata
            )
        
        except Exception as e:
            return ExtractionResult(
                engine_name=self.engine_name,
                extracted_data={},
                success=False,
                error_message=str(e),
                processing_time_ms=self._get_processing_time_ms()
            )
    
    def _process_page(
        self,
        image: Image.Image,
        page_number: int,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """
        Process a single page with LayoutLMv3.
        
        Args:
            image: PIL Image of the page
            page_number: Page number (1-indexed)
            confidence_threshold: Minimum confidence for predictions
        
        Returns:
            Dict with extracted text, confidence, and layout info
        """
        try:
            # Prepare inputs
            encoding = self.processor(
                image,
                return_tensors="pt",
                truncation=True,
                padding="max_length"
            )
            
            # Move to device
            encoding = {k: v.to(self.device) for k, v in encoding.items()}
            
            # Run inference
            with torch.no_grad():
                outputs = self.model(**encoding)
            
            # Get predictions
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_ids = predictions.argmax(dim=-1)
            
            # Extract text and confidence
            tokens = encoding["input_ids"][0]
            confidences = predictions[0].max(dim=-1).values
            
            # Decode tokens to text
            text_tokens = []
            token_confidences = []
            
            for token_id, conf in zip(tokens, confidences):
                if token_id not in [0, 1, 2]:  # Skip special tokens
                    token_text = self.processor.tokenizer.decode([token_id])
                    if token_text and token_text.strip():
                        text_tokens.append(token_text)
                        token_confidences.append(float(conf))
            
            # Build full text
            full_text = " ".join(text_tokens)
            avg_confidence = sum(token_confidences) / len(token_confidences) if token_confidences else 0.0
            
            # Get layout information from bbox (if available)
            layout_info = {
                "page": page_number,
                "token_count": len(text_tokens),
                "avg_token_confidence": round(avg_confidence, 4),
                "min_confidence": round(min(token_confidences), 4) if token_confidences else 0.0,
                "max_confidence": round(max(token_confidences), 4) if token_confidences else 0.0
            }
            
            return {
                "page": page_number,
                "text": full_text,
                "confidence": avg_confidence,
                "layout_info": layout_info,
                "word_count": len(text_tokens),
                "char_count": len(full_text)
            }
        
        except Exception as e:
            return {
                "page": page_number,
                "text": "",
                "confidence": 0.0,
                "layout_info": {},
                "word_count": 0,
                "char_count": 0,
                "error": str(e)
            }
    
    def calculate_confidence(self, extraction_data: Dict[str, Any]) -> Decimal:
        """
        Calculate confidence score for LayoutLM extraction.
        
        LayoutLM provides token-level confidence from softmax outputs.
        We aggregate these for overall document confidence.
        
        Args:
            extraction_data: Dictionary with extracted text and metadata
        
        Returns:
            Confidence score as Decimal (0.0 - 1.0)
        """
        pages = extraction_data.get("pages", [])
        
        if not pages:
            return Decimal('0.0')
        
        # Get average confidence across all pages
        page_confidences = [p.get("confidence", 0.0) for p in pages]
        avg_confidence = sum(page_confidences) / len(page_confidences)
        
        # LayoutLM confidence is typically high - adjust if needed
        # Apply text quality check
        text = extraction_data.get("text", "")
        text_quality = self._calculate_text_quality(text, expected_min_length=50)
        
        # Combine AI confidence with text quality
        final_confidence = (avg_confidence * 0.7) + (text_quality * 0.3)
        
        return Decimal(str(round(final_confidence, 4)))

