#!/usr/bin/env python3
"""Create database schema from models"""
import sys
sys.path.insert(0, '/app')

from app.db.database import engine, Base
# Import all models
from app.models import (
    user, property, document_upload, financial_period, chart_of_accounts,
    validation_rule, extraction_template, extraction_log, audit_trail,
    balance_sheet_data, income_statement_data, cash_flow_data, rent_roll_data,
    validation_result, financial_metric
)
from sqlalchemy import text

print('🔄 Creating all tables from models...')
try:
    Base.metadata.create_all(bind=engine)
    print('✅ Tables created!')
    
    # Verify
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
        count = result.scalar()
        print(f'📊 Total tables: {count}')
        
        # List tables
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"))
        tables = [row[0] for row in result]
        print(f'📋 Tables: {", ".join(tables)}')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

