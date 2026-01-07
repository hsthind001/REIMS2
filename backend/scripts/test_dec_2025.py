from app.db.database import SessionLocal
from app.services.metrics_service import MetricsService

db = SessionLocal()
try:
    service = MetricsService(db)
    metrics = service.calculate_all_metrics(1, 99)  # property_id=1, period_id=99 (2025-12)
    print(f'NOI: ${metrics.net_operating_income:,.2f}')
    print(f'DSCR: {metrics.dscr:.4f}' if metrics.dscr else 'DSCR: NULL')
    print(f'Status: {"HEALTHY" if metrics.dscr and metrics.dscr >= 1.25 else "CRITICAL"}')
finally:
    db.close()
