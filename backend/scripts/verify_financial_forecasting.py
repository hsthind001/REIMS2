
"""
Verification Script for Financial Forecasting Service
"""
import logging
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Add backend to path
sys.path.append('backend')

from app.services.financial_forecasting_service import FinancialForecastingService
from app.models.financial_metrics import FinancialMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestFinancialForecasting(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = FinancialForecastingService(self.mock_db)

    def create_mock_metrics(self, count=24):
        """Create 2 years of monthly data"""
        metrics = []
        base_date = datetime(2023, 1, 1)
        base_noi = 10000.0
        
        for i in range(count):
            date = base_date + timedelta(days=30*i)
            # Add some trend and seasonality
            noi = base_noi + (i * 100) + (1000 if i % 12 == 0 else 0)
            
            m = MagicMock(spec=FinancialMetrics)
            m.period_end_date = date
            m.net_operating_income = noi
            metrics.append(m)
        return metrics

    def test_forecast_noi_flow(self):
        """Test the orchestration flow without running actual Prophet optimization (too slow/heavy)"""
        logger.info("Testing forecast_noi flow with mocked Prophet...")
        
        # Manually inject Prophet mock into the module since it might be missing
        import app.services.financial_forecasting_service as ffs
        
        original_prophet_available = ffs.PROPHET_AVAILABLE
        original_prophet_class = getattr(ffs, 'Prophet', None)
        
        ffs.PROPHET_AVAILABLE = True
        MockProphetClass = MagicMock()
        ffs.Prophet = MockProphetClass
        
        try:
            # Setup Mock Prophet Instance
            mock_model_instance = MockProphetClass.return_value
            
            # Mock make_future_dataframe
            import pandas as pd
            future_df = pd.DataFrame({'ds': [datetime(2025, 1, 1)] * 12})
            mock_model_instance.make_future_dataframe.return_value = future_df
            
            # Mock predict
            forecast_df = pd.DataFrame({
                'ds': [datetime(2025, 1, 1) + timedelta(days=30*i) for i in range(12)],
                'yhat': [12000.0 + i*100 for i in range(12)],
                'yhat_lower': [11000.0] * 12,
                'yhat_upper': [13000.0] * 12
            })
            mock_model_instance.predict.return_value = forecast_df
            
            # Mock DB Return
            mock_metrics = self.create_mock_metrics()
            
            # Patch _fetch_historical_metrics on the instance
            with patch.object(self.service, '_fetch_historical_metrics', return_value=mock_metrics):
                result = self.service.forecast_noi(property_id=1, periods=12)
                
                # Assertions
                self.assertIn("forecast_periods", result)
                self.assertEqual(result["forecast_periods"], 12)
                self.assertEqual(len(result["data"]), 12)
                self.assertEqual(result["data"][0]["predicted_noi"], 12000.0)
                
                # Verify Prophet calls
                self.assertTrue(MockProphetClass.called)
                self.assertTrue(mock_model_instance.fit.called)
                self.assertTrue(mock_model_instance.predict.called)
                
                logger.info("SUCCESS: forecast_noi flow verified.")
                
        finally:
            # Restore original state
            ffs.PROPHET_AVAILABLE = original_prophet_available
            if original_prophet_class:
                ffs.Prophet = original_prophet_class
            else:
                del ffs.Prophet

if __name__ == "__main__":
    unittest.main()
