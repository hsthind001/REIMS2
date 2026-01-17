
import sys
import os
import asyncio
import logging
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend directory to patch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary test file
TEST_DB_PATH = "test_corrections.json"

async def test_active_learning_loop():
    """
    Test Feedback Loop and LLM Injection.
    """
    logger.info("🧪 Testing Active Learning Feedback Loop...")
    
    # 1. Test FeedbackLoopService directly (Save/Load)
    from app.services.feedback_loop_service import FeedbackLoopService
    
    # Use temporary file
    service = FeedbackLoopService(data_path=TEST_DB_PATH)
    
    # Save a correction
    doc_type = "balance_sheet"
    original_text = "Assets: Cash $100"
    correction = {"assets": [{"name": "Cash", "value": 100}]}
    
    service.save_correction(original_text, correction, doc_type, "Basic test")
    
    # Verify load
    examples = service.get_few_shot_examples(doc_type)
    if len(examples) == 1 and examples[0]["expected_json"] == correction:
        logger.info("   ✅ Success: Correction saved and retrieved.")
    else:
        logger.error("   ❌ Failed: Correction persistence failed.")
        return False
        
    # 2. Test LLM Injection via LLMExtractionService
    # We strip the FeedbackLoop import inside the service, so we patch it there?
    # Actually we just use the real one with our test DB file if we can patch the init or path.
    # To keep it simple, we will patch FeedbackLoopService class in the module where it is DEFINED.

    with patch("app.services.feedback_loop_service.FeedbackLoopService") as MockFeedbackService, \
         patch("app.services.llm_extraction_service.get_local_llm_service") as mock_get_llm:
         
         # Setup Mock Feedback Service to return our example
         mock_feedback_instance = MockFeedbackService.return_value
         mock_feedback_instance.get_few_shot_examples.return_value = [
             {"text_snippet": "Example Text", "expected_json": {"foo": "bar"}}
         ]
         
         # Setup Mock LLM
         mock_llm_instance = MagicMock()
         mock_get_llm.return_value = mock_llm_instance
         mock_llm_instance.generate_json = AsyncMock(return_value={"success": True})
         
         # Instantiate Service
         from app.services.llm_extraction_service import LLMExtractionService
         llm_extractor = LLMExtractionService(db=MagicMock())
         
         logger.info("   Invoking extract_financial_data...")
         await llm_extractor.extract_financial_data("Some text", "balance_sheet")
         
         # Verify Prompt content
         # The system prompt should now contain the example
         call_args = mock_llm_instance.generate_json.call_args
         if call_args:
             kwargs = call_args.kwargs
             system_prompt = kwargs.get("system_prompt", "")
             if "Example Text" in system_prompt and '{"foo": "bar"}' in system_prompt:
                 logger.info("   ✅ Success: Few-shot example injected into system prompt.")
                 pass
             else:
                 logger.error(f"   ❌ Failed: Example not found in prompt. Prompt start: {system_prompt[:200]}...")
                 return False
         else:
             logger.error("   ❌ Failed: LLM generate_json not called.")
             return False

    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    return True

async def main():
    try:
        success = await test_active_learning_loop()
        if success:
            logger.info("\n🎉 Active Learning Verification Passed!")
            sys.exit(0)
        else:
            logger.error("\n❌ Verification Failed.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Script Error: {e}")
        import traceback
        traceback.print_exc()
        # Cleanup
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
