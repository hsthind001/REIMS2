
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

async def test_visual_understanding():
    """
    Test ImageAnalysisService flow with mocked image conversion and LLM.
    """
    logger.info("🧪 Testing Visual Understanding (LLaVA Integration)...")
    
    # Needs to mock pdf2image before importing service if it triggers import error catch?
    # Actually the service handles ImportError inside the method, but let's mock it globally.
    
    with patch("app.services.image_analysis_service.convert_from_bytes") as mock_convert, \
         patch("app.services.image_analysis_service.get_local_llm_service") as mock_get_llm:
        
        # 1. Setup Service
        from app.services.image_analysis_service import ImageAnalysisService
        
        # Mock Image Conversion
        mock_image = MagicMock()
        mock_image.save = MagicMock() # Mock PIL save
        mock_convert.return_value = [mock_image] # Return one image
        
        # Mock LLM Service
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance
        mock_llm_instance.analyze_image = AsyncMock(return_value="The chart shows a steady increase in Net Operating Income from Q1 to Q4.")
        
        service = ImageAnalysisService()
        
        # 2. Execute
        # Pass dummy bytes
        pdf_bytes = b"%PDF-1.4..." 
        logger.info("   Invoking extract_charts_and_graphs...")
        result = await service.extract_charts_and_graphs(pdf_bytes)
        
        # 3. Verify
        if result["success"] and result["charts_found"] > 0:
            analysis = result["details"][0]["analysis"]
            logger.info(f"   ✅ Success: Visual analysis returned: '{analysis}'")
            
            # Verify prompts were sent
            # Check if analyze_image was called
            if mock_llm_instance.analyze_image.called:
                 logger.info("   ✅ Verified: LLM `analyze_image` was called.")
                 return True
            else:
                 logger.error("   ❌ Failed: LLM was not invoked.")
                 return False
        else:
            logger.error(f"   ❌ Failed: Result was {result}")
            return False

async def main():
    try:
        success = await test_visual_understanding()
        if success:
            logger.info("\n🎉 Visual Understanding Verification Passed!")
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
