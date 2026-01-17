
import sys
import logging

# Add backend to path
sys.path.append('backend')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_startup():
    logger.info("Attempting to import FastAPI app...")
    try:
        from app.main import app
        logger.info("✅ Successfully imported app.main")
        
        from app.services.statistical_anomaly_service import StatisticalAnomalyService
        from app.services.document_intelligence_service import DocumentIntelligenceService
        from app.services.financial_forecasting_service import FinancialForecastingService
        from app.services.portfolio_rag_service import PortfolioRagService
        
        logger.info("✅ Successfully imported all new AI services")
        return True
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_startup()
    sys.exit(0 if success else 1)
