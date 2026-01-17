
import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, patch, ANY
from typing import List

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure modules are loaded
try:
    from app.api.v1 import metrics, portfolio_analytics
except ImportError as e:
    logger.error(f"Import Error: {e}")
    # Fallback/Debug
    import sys
    logger.info(f"Sys Path: {sys.path}")

async def test_dashboard_metrics_summary():
    """
    Simulate GET /metrics/summary
    """
    logger.info("\n🧪 Testing Dashboard Metrics Summary (/api/v1/metrics/summary)...")
    
    with patch("app.api.v1.metrics.get_db") as mock_get_db, \
         patch("app.api.v1.metrics.cache_get") as mock_cache_get, \
         patch("sqlalchemy.inspect") as mock_inspect:
        
        # 1. Mock DB Session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # 2. Mock Cache Miss
        mock_cache_get.return_value = None
        
        # 3. Mock Table Inspection (Assume period_document_completeness exists)
        mock_inspect.return_value.has_table.return_value = True
        
        # 4. Mock DB Query Results
        # The query logic in metrics.py is complex (joins, subqueries).
        # We will mock the FINAL result of `db.query(...).all()`
        
        # We need to mock the `db.query()` chain. 
        # The code executes: `complete_rows = db.query(latest_complete_query)...all()`
        # We can try to mock the `db.query.return_value.filter.return_value.all.return_value`
        
        # Mock Row Object
        class MockRow:
            def __init__(self, property_code, property_name, period_id, period_year, period_month, total_assets, metric_val):
                self.property_code = property_code
                self.property_name = property_name
                self.period_id = period_id
                self.period_year = period_year
                self.period_month = period_month
                self.total_assets = total_assets
                self.total_revenue = metric_val
                self.net_income = metric_val * 0.2
                self.net_operating_income = metric_val * 0.4
                self.occupancy_rate = 95.0
                self.dscr = 1.25
                self.ltv_ratio = 65.0
                self.total_revenue = metric_val
                self.is_complete = True
                self.net_property_value = total_assets # Fallback test
                
        mock_rows = [
            MockRow("PROP001", "Sunset Apts", 101, 2024, 1, 1000000.0, 50000.0),
            MockRow("PROP002", "Downtown Office", 102, 2024, 1, 5000000.0, 250000.0)
        ]
        
        # Since the code makes multiple query calls (check for has_completeness, fetch complete, fetch fallback),
        # we need to be careful.
        # It calls `db.query(latest_complete_query)...all()`
        # We can just return 'mock_rows' for any `.all()` call to keep it simple, checking if it processes them.
        
        # To make it robust against specific chained calls, we configure the last `.all()`
        mock_db.query.return_value.filter.return_value.all.return_value = mock_rows
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_rows
        
        # Also need to mock the `.subquery()` and joins if we want deep simulation, but mocking the results is easier.
        # Actually the code builds `latest_complete_query` using `db.query(...)`.
        # So `db.query(...)` returns a Query object.
        
        from app.api.v1.metrics import get_metrics_summary
        
        # 5. Execute
        try:
            result = await get_metrics_summary(skip=0, limit=10, year=None, db=mock_db)
            
            # 6. Verify
            if len(result) > 0:
                logger.info(f"   ✅ Success: Retrieved {len(result)} summary items.")
                logger.info(f"   Sample: {result[0].property_name} - NOI: ${result[0].net_operating_income}")
                return True
            else:
                logger.error("   ❌ Failed: No results returned.")
                return False
                
        except Exception as e:
            logger.error(f"   ❌ Exception during execution: {e}")
            # If mocking failed (due to complex SQLAlchemy structure), we might see it here.
            return False

async def test_portfolio_analytics():
    """
    Simulate GET /portfolio-analytics/analytics
    """
    logger.info("\n🧪 Testing Portfolio Analytics (/api/v1/portfolio-analytics/analytics)...")
    
    with patch("app.api.v1.portfolio_analytics.get_db") as mock_get_db:
        
        # 1. Mock DB
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # 2. Mock Counts
        # Mocking `db.query(...).count()`
        # We need side_effect to return different values for different queries (Properties vs Anomalies)
        
        # We can inspect call args, or just return fixed values if order is deterministic.
        # Order: 
        # 1. Total Props (count)
        # 2. Total Anomalies (count)
        # 3. Severity (group_by.all)
        # 4. Top Accounts (group_by.order_by.limit.all)
        # 5. Top Props (group_by.order_by.limit.all)
        
        mock_db.query.return_value.filter.return_value.count.side_effect = [10, 5] # 10 props, 5 anomalies
        
        # Mock grouped results
        mock_severity = [("high", 2), ("medium", 3)]
        mock_accounts = [("REV.001", 3), ("EXP.050", 2)]
        mock_props = [(1, 3), (2, 2)]
        
        # Config the `.all()` returns
        # The code creates NEW query objects for each step.
        # We can use side_effect on `.all()` but it's shared across all chains.
        # Better to just return a sequence of results.
        
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_severity # For severity
        # Wait, chained calls are tricky with simple mocking if they vary.
        # Let's hope the chain is unique enough or just return generic compatible data.
        
        # Specifically:
        # Severity: .filter().group_by().all()
        # Accounts: .filter().group_by().order_by().limit().all()
        # Props: .filter().group_by().order_by().limit().all()
        
        # We can mock `db.query` to return different Mocks based on what model is passed.
        # But `db.query` is called with Model classes.
        
        # Let's import the endpoint function and `Property`, `AnomalyDetection` models to mock them.
        from app.models.property import Property
        from app.models.anomaly_detection import AnomalyDetection
        
        def query_side_effect(*args):
             mock_q = MagicMock()
             if args[0] == Property:
                 # Property Query
                 if hasattr(mock_q, 'filter'): return mock_q
                 mock_q.first.return_value = Property(id=1, property_name="Test Prop", property_code="P1")
             elif args[0] == AnomalyDetection:
                  pass # Anomaly Logic
             elif args[0] == AnomalyDetection.severity:
                  # Severity aggregation
                  mock_q.filter.return_value.group_by.return_value.all.return_value = mock_severity
             elif args[0] == AnomalyDetection.account_code:
                  # Account aggregation
                  mock_q.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_accounts
             elif args[0] == AnomalyDetection.property_id:
                  # Property aggregation
                  mock_q.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_props
             
             # Default behavior for counts (Property / Anomaly)
             # This is hard because `db.query(Property)` returns a query that has .count().
             # We set specific return values on the generated mock if needed.
             return mock_q

        # Attempting a simpler mock strategy:
        # Just mock the final methods to return what's expected for all calls in sequence.
        # sequence of `.all()` calls:
        # 1. Severity
        # 2. Top Accounts
        # 3. Top Props
        
        # Sequence of `.count()` calls:
        # 1. Props
        # 2. Anomalies
        
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.group_by.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        
        query_mock.count.side_effect = [10, 5]
        query_mock.all.side_effect = [
            mock_severity,
            mock_accounts,
            mock_props
        ]
        
        # Mock Property lookup in loop
        # The loop calls `db.query(Property).filter(...).first()`
        # This interferes with our main `db.query` mock which is `query_mock`.
        # `query_mock.first.return_value` needs to return a Property object.
        mock_prop = MagicMock()
        mock_prop.property_name = "Test Property"
        mock_prop.property_code = "TP001"
        query_mock.first.return_value = mock_prop
        
        from app.api.v1.portfolio_analytics import get_portfolio_analytics
        
        try:
            result = await get_portfolio_analytics(db=mock_db)
            
            logger.info(f"   ✅ Success: Analytics computed.")
            logger.info(f"   Total Properties: {result.total_properties}")
            logger.info(f"   Total Anomalies: {result.total_anomalies}")
            logger.info(f"   Avg Anomalies: {result.average_anomalies_per_property}")
            
            if result.total_properties == 10 and result.total_anomalies == 5:
                return True
            else:
                 logger.error("   ❌ Failed: Counts mismatch.")
                 return False
                 
        except Exception as e:
            logger.error(f"   ❌ Exception: {e}")
            return False

async def main():
    logger.info("Starting Dashboard Verification...")
    
    success_metrics = await test_dashboard_metrics_summary()
    success_analytics = await test_portfolio_analytics()
    
    if success_metrics and success_analytics:
        logger.info("\n🎉 Dashboard Verification Passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Verification Failed.")
        sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
