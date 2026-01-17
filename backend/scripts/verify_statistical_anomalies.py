
"""
Verification Script for Statistical Anomalies
"""
import asyncio
import logging
import sys
from decimal import Decimal
from typing import List

# Add backend to path
sys.path.append('backend')

from app.services.statistical_anomaly_service import StatisticalAnomalyService
from app.models.income_statement_data import IncomeStatementData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock valid IncomeStatementData
def create_mock_data() -> List[IncomeStatementData]:
    data = []
    
    # 50 "normal" transactions around 1000
    for i in range(50):
        data.append(IncomeStatementData(
            id=i, 
            account_name=f"Rent Income {i}", 
            period_amount=Decimal(1000 + (i % 10)),
            period_start_date="2023-01-01"
        ))
        
    # 1 Anomaly
    data.append(IncomeStatementData(
        id=999, 
        account_name="Anomalous Expense", 
        period_amount=Decimal(100000), # Huge outlier
        period_start_date="2023-01-01"
    ))
    
    return data

def main():
    logger.info("Starting verification of StatisticalAnomalyService...")
    
    # Mock DB session (None is fine for this test as we don't query)
    service = StatisticalAnomalyService(db=None)
    
    # Create mock data
    data = create_mock_data()
    logger.info(f"Created {len(data)} mock data points")
    
    # 1. Train
    success = service.train_model(data)
    if not success:
        logger.error("Failed to train model")
        sys.exit(1)
    logger.info("Training successful")
    
    # 2. Detect
    anomalies = service.detect_anomalies(data)
    logger.info(f"Detected {len(anomalies)} anomalies")
    
    # Verify the anomaly is caught
    detected_ids = [a['item_id'] for a in anomalies]
    if 999 in detected_ids:
        logger.info("SUCCESS: Detected known anomaly (ID 999)")
        
        # Print details
        anomaly = next(a for a in anomalies if a['item_id'] == 999)
        logger.info(f"Anomaly Details: Score={anomaly['anomaly_score']:.2f}, Prob={anomaly['anomaly_probability']:.2f}")
    else:
        logger.error("FAILURE: Did not detect known anomaly")
        sys.exit(1)

if __name__ == "__main__":
    main()
