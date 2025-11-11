#!/usr/bin/env python3
"""Create database schema from models"""
from app.db.database import engine, Base
# Import all models
from app.models import user, property, document_upload, financial_period, chart_of_accounts
from app.models import validation_rule, extraction_template, extraction_log, audit_trail
from app.models import balance_sheet_data, income_statement_data, cash_flow_data, rent_roll_data
from app.models import validation_result, financial_metric

print('🔄 Creating all tables from models...')
Base.metadata.create_all(bind=engine)
print('✅ Tables created!')

# Verify
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
    count = result.scalar()
    print(f'📊 Total tables: {count}')
