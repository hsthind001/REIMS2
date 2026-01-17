
"""
Verification Script for Portfolio RAG Service
"""
import logging
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append('backend')

from app.services.portfolio_rag_service import PortfolioRagService
# Import the module to patch availability flag
import app.services.portfolio_rag_service as rag_module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPortfolioRag(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = PortfolioRagService(self.mock_db)

    def test_rag_flow_mocked(self):
        """Test RAG flow with simulated LangChain availability"""
        logger.info("Testing RAG flow with mocked LangChain...")
        
        # Preserve original state
        original_avail = rag_module.LANGCHAIN_AVAILABLE
        
        # Inject Mocked Dependency Availability
        rag_module.LANGCHAIN_AVAILABLE = True
        
        # Inject Mock Classes for imports that might have failed
        rag_module.Document = MagicMock()
        
        try:
            # Re-init service to pick up flag
            service = PortfolioRagService(self.mock_db)
            
            # Mock DB Data
            mock_prop = MagicMock()
            mock_prop.id = 1
            mock_prop.name = "Test Property"
            mock_prop.address = "123 Main St"
            mock_prop.unit_count = 100
            
            mock_metric = MagicMock()
            mock_metric.property_id = 1
            mock_metric.net_operating_income = 100000
            mock_metric.total_revenue = 200000
            mock_metric.period_end_date = "2024-01-01"
            
            # Setup DB Returns
            # Check how db.execute is called in build_index
            # properties = self.db.execute(select(Property)).scalars().all()
            
            # We need to chain the return values
            # 1st call: Properties
            # 2nd call: Metrics
            
            mock_result_props = MagicMock()
            mock_result_props.scalars.return_value.all.return_value = [mock_prop]
            
            mock_result_metrics = MagicMock()
            mock_result_metrics.scalars.return_value.all.return_value = [mock_metric]
            
            self.mock_db.execute.side_effect = [mock_result_props, mock_result_metrics]
            
            # TEST 1: Build Index
            success = service.build_index()
            
            if success:
                 logger.info("SUCCESS: Index built successfully (Mocked).")
            else:
                 self.fail("Failed to build index.")
                 
            # TEST 2: Query
            # Since we didn't actually build a real FAISS index (dependencies missing), 
            # the Service.query method returns a placeholder in the implementation.
            # We verify it returns a valid dict.
            
            response = service.query("What is the NOI?")
            self.assertIn("answer", response)
            self.assertIn("sources", response)
            
            logger.info("SUCCESS: Query returned valid response structure.")
            
        finally:
            rag_module.LANGCHAIN_AVAILABLE = original_avail

if __name__ == "__main__":
    unittest.main()
