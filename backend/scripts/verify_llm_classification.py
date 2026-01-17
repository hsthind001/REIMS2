
import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend directory to patch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock dependencies that might be missing or require heavy setup
sys.modules["app.db.minio_client"] = MagicMock()
sys.modules["app.utils.extraction_engine"] = MagicMock()

# Setup mocks for imports inside DocumentService
with patch("app.db.minio_client.get_minio_client") as mock_get_client:
    from app.services.document_service import DocumentService
    from app.models.property import Property
    from app.models.financial_period import FinancialPeriod
    from app.models.document_upload import DocumentUpload

async def test_semantic_classification_fallback():
    """
    Test that DocumentService falls back to LLM classification when basic detection fails.
    """
    logger.info("🧪 Testing Semantic Classification Fallback...")
    
    # 1. Setup Service and Mocks
    mock_db = MagicMock()
    service = DocumentService(mock_db)
    
    # Mock Property and Period retrieval to bypass initial checks
    mock_property = Property(id=1, property_code="ESP001", property_name="Test Prop")
    service.get_property_by_code = MagicMock(return_value=mock_property)
    service.get_or_create_period = MagicMock(return_value=FinancialPeriod(id=1))
    service.calculate_file_hash = MagicMock(return_value="hash123")
    service.check_duplicate = MagicMock(return_value=None)
    service.generate_file_path = AsyncMock(return_value="test/path.pdf")
    service.check_file_exists = MagicMock(return_value=None)
    service._get_next_version = MagicMock(return_value=1)
    
    # Mock upload_file (minio)
    with patch("app.services.document_service.upload_file", return_value=True):
        
        # 2. Mock MultiEngineExtractor (The regex detector)
        # We want it to FAIL detection ("unknown") to trigger the LLM fallback
        mock_detector_instance = MagicMock()
        mock_detector_instance.detect_property_with_intelligence.return_value = {
            "primary_property": {"code": "ESP001", "confidence": 90}
        }
        mock_detector_instance.detect_document_type.return_value = {
            "detected_type": "unknown", # <--- This should trigger fallback
            "confidence": 0
        }
        mock_detector_instance.detect_year_and_period.return_value = {"year": 2024, "month": 1}
        
        # Mock PyMuPDF text extraction which is needed for LLM
        mock_detector_instance.pymupdf.extract_text.return_value = {
            "success": True, 
            "pages": [{"text": "Content that looks like a balance sheet..."}] 
        }

        # 3. Mock LLMExtractionService (The LLM classifier)
        # Patch the class where it is DEFINED
        with patch("app.utils.extraction_engine.MultiEngineExtractor", return_value=mock_detector_instance), \
             patch("app.services.llm_extraction_service.LLMExtractionService") as MockLLMService:
            
            # Setup LLM Mock to succeed
            mock_llm_instance = MockLLMService.return_value
            mock_llm_instance.classify_document = AsyncMock(return_value={
                "document_type": "balance_sheet",
                "confidence": 0.95,
                "reasoning": "Contains assets and liabilities"
            })
            
            # 4. Invoke upload_document
            mock_file = AsyncMock()
            mock_file.filename = "test_doc.pdf"
            mock_file.read.return_value = b"fake pdf content"
            
            logger.info("   Invoking upload_document with 'unknown' type from regex...")
            result = await service.upload_document(
                property_code="ESP001",
                period_year=2024,
                period_month=1,
                document_type="balance_sheet", # User selected type
                file=mock_file
            )
            
            # 5. Verify LLM was called
            if mock_llm_instance.classify_document.called:
                logger.info("   ✅ Success: LLM classification was called.")
                # Verify that the detected type was updated in the log logic 
                # (We can't easily check internal var 'detected_type', but we can check if print was called 
                # or if the flow continued without 'unknown' logic if we had mismatch checks based on it)
                
                # Check if mismatch logic was triggered (User selected balance_sheet, LLM found balance_sheet)
                # If LLM found balance_sheet, then it matches user selection, so no mismatch error.
                if result.get("type_mismatch"):
                     logger.error(f"   ❌ Failed: Logic reported mismatch despite LLM finding correct type. Result: {result}")
                     return False
                else:
                     logger.info("   ✅ Verified: No mismatch reported (LLM successfully identified balance_sheet).")
                     return True
            else:
                logger.error("   ❌ Failed: LLM classification was NOT called.")
                return False

async def main():
    try:
        success = await test_semantic_classification_fallback()
        if success:
            logger.info("\n🎉 Semantic Classification Verification Passed!")
            sys.exit(0)
        else:
            logger.error("\n❌ Verification Failed.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Script Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
