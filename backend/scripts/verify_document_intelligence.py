
import logging
import sys
import os
from unittest.mock import MagicMock, patch
from PIL import Image

# Add backend to path
sys.path.append('backend')
from app.services import document_intelligence_service # Import module
from app.services.document_intelligence_service import DocumentIntelligenceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting verification of DocumentIntelligenceService (Mocked)...")

    # Mock DB
    mock_db = MagicMock()
    
    # Initialize Service
    service = DocumentIntelligenceService(db=mock_db)
    
    # Create dummy image
    dummy_image = Image.new('RGB', (100, 100), color = 'white')
    
    # 1. Test Fallback Flow (assuming LayoutLM unavailable or fails)
    # We patch _load_document_image to return our dummy image
    # And patch os.path.exists to allow dummy path
    with patch.object(service, '_load_document_image', return_value=dummy_image), \
         patch('os.path.exists', return_value=True):
        
        # Test Case A: Force Tesseract (Simulate LayoutLM/EasyOCR missing/failing)
        # We also mock the analysis methods to control the outcome
        with patch.object(service, '_analyze_with_layoutlm', side_effect=Exception("LayoutLM Not Found")), \
             patch.object(service, '_analyze_with_easyocr', side_effect=Exception("EasyOCR Not Found")), \
             patch.object(service, '_analyze_with_tesseract', return_value={'confidence':0.9, 'text_content': 'Tesseract Text', 'entities': []}):
            
            # Temporarily set flags to enable fallbacks (if any logic depends on it, but loop checks vars)
            # For simplicity, we rely on the side_effects simulating availability
            
            logger.info("Test A: Testing failover to Tesseract...")
            
            # We temporarily ensure the service thinks Tesseract is available for this test
            original_tess = document_intelligence_service.TESSERACT_AVAILABLE
            document_intelligence_service.TESSERACT_AVAILABLE = True
            
            result = service.analyze_document("dummy.pdf")
            
            if result['method'] == 'tesseract' and result['text_content'] == 'Tesseract Text':
                logger.info("SUCCESS: Fell back to Tesseract as expected.")
            else:
                logger.error(f"FAILURE: Did not fall back to Tesseract correctly. Result: {result}")
                sys.exit(1)
            
            document_intelligence_service.TESSERACT_AVAILABLE = original_tess

        # Test Case B: Test LayoutLM success (Simulate it working)
        with patch.object(service, '_analyze_with_layoutlm', return_value={'confidence':0.95, 'text_content': 'LayoutLM Text', 'entities': []}):
             
             # We assume self.layoutlm_model is truthy for this test, so we mock it
             service.layoutlm_model = MagicMock()
             
             logger.info("Test B: Testing LayoutLM priority...")
             result = service.analyze_document("dummy.pdf")
             
             if result['method'] == 'layoutlmv3':
                 logger.info("SUCCESS: Used LayoutLMv3 as priority.")
             else:
                 logger.error(f"FAILURE: Did not use LayoutLMv3. Result: {result}")
                 sys.exit(1)
                 
    logger.info("Verification of DocumentIntelligenceService flow complete.")

if __name__ == "__main__":
    main()
