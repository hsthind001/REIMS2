
import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock dependencies before imports
sys.modules["app.services.local_llm_service"] = MagicMock()

from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.llm_extraction_service import LLMExtractionService

async def test_llm_fallback_logic():
    """
    Test that ExtractionOrchestrator calls LLMExtractionService when regex fails.
    """
    logger.info("🧪 Testing LLM Fallback Logic...")
    
    # 1. Setup Mocks
    mock_db = MagicMock()
    orchestrator = ExtractionOrchestrator(mock_db)
    
    # Mock LLM Service Response
    mock_llm_data = {
        "line_items": [
            {"account_name": "Consulting Fees", "amount": 5000.00, "section": "Revenue"},
            {"account_name": "Software License", "amount": 150.00, "section": "Expense"}
        ],
        "net_operating_income": 4850.00
    }
    
    # We patch the class where it is DEFINED, because it is imported at runtime
    with patch("app.services.llm_extraction_service.LLMExtractionService") as MockLLMService:
        # Setup the mock instance
        mock_instance = MockLLMService.return_value
        mock_instance.extract_financial_data = AsyncMock(return_value={
            "success": True,
            "data": mock_llm_data
        })
        
        # 2. Define Test Input (Unstructured text that regex is likely to fail on)
        # Note: The regex looks for "Name   Values", so we provide text that doesn't match that specific spacing
        bad_text = """
        INCOME STATEMENT
        For the period ending Dec 31, 2024
        
        We acknowledge receipt of Consulting Fees in the amount of $5,000.00.
        Additionally, we paid out Software License fees totaling $150.00.
        
        Net Income for the period: $4,850.00
        """
        
        # 3. Run Method
        logger.info("   Invoking _fallback_extraction with unstructured text...")
        result = await orchestrator._fallback_extraction(bad_text, "income_statement")
        
        # 4. Verify Results
        if result["success"] and result.get("extraction_method") == "llm_fallback":
            logger.info("   ✅ Success: Fallback triggered LLM extraction.")
            logger.info(f"   Items found: {len(result['line_items'])}")
            
            # Verify specific items
            fees = next((i for i in result['line_items'] if i['account_name'] == 'Consulting Fees'), None)
            if fees and fees['amount'] == 5000.0:
                logger.info("   ✅ Verified 'Consulting Fees' extracted correctly.")
            else:
                logger.error("   ❌ Failed to verify 'Consulting Fees'.")
                
            software = next((i for i in result['line_items'] if i['account_name'] == 'Software License'), None)
            if software and software['amount'] == 150.0:
                 logger.info("   ✅ Verified 'Software License' extracted correctly.")
            else:
                 logger.error("   ❌ Failed to verify 'Software License'.")
                 
            return True
        else:
            logger.error(f"   ❌ Failed: Logic did not fall back to LLM. Result: {result}")
            return False

async def main():
    try:
        success = await test_llm_fallback_logic()
        if success:
            logger.info("\n🎉 All Verification Tests Passed!")
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
