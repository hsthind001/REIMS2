#!/usr/bin/env python3
"""
Batch Testing Script for Cash Flow Statement Extraction

Tests all Cash Flow PDFs in MinIO across all properties and years.
Validates production-ready extraction with comprehensive quality metrics.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_header import CashFlowHeader
from app.core.config import settings
from datetime import datetime, date
import hashlib
import time

# Configure database
def get_database_url():
    return f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define all Cash Flow files to test
TEST_FILES = [
    {'property_code': 'ESP001', 'year': 2023, 'month': 12, 'path': 'ESP001-Eastern-Shore-Plaza/2023/cash-flow/ESP_2023_Cash_Flow_Statement.pdf', 'size': 25545},
    {'property_code': 'ESP001', 'year': 2024, 'month': 12, 'path': 'ESP001-Eastern-Shore-Plaza/2024/cash-flow/ESP_2024_Cash_Flow_Statement.pdf', 'size': 25569},
    {'property_code': 'HMND001', 'year': 2023, 'month': 12, 'path': 'HMND001-Hammond-Aire/2023/cash-flow/HMND_2023_Cash_Flow_Statement.pdf', 'size': 25513},
    {'property_code': 'HMND001', 'year': 2024, 'month': 12, 'path': 'HMND001-Hammond-Aire/2024/cash-flow/HMND_2024_Cash_Flow_Statement.pdf', 'size': 25785},
    {'property_code': 'TCSH001', 'year': 2023, 'month': 12, 'path': 'TCSH001-The-Crossings/2023/cash-flow/TCSH_2023_Cash_Flow_Statement.pdf', 'size': 25203},
    {'property_code': 'TCSH001', 'year': 2024, 'month': 12, 'path': 'TCSH001-The-Crossings/2024/cash-flow/TCSH_2024_Cash_Flow_Statement.pdf', 'size': 25388},
    {'property_code': 'WEND001', 'year': 2023, 'month': 12, 'path': 'WEND001-Wendover-Commons/2023/cash-flow/WEND_2023_Cash_Flow_Statement.pdf', 'size': 25018},
    {'property_code': 'WEND001', 'year': 2024, 'month': 12, 'path': 'WEND001-Wendover-Commons/2024/cash-flow/WEND_2024_Cash_Flow_Statement.pdf', 'size': 25263},
]

def get_or_create_upload_record(db, file_info):
    """Create document upload record if it doesn't exist"""
    # Get property
    property = db.query(Property).filter(
        Property.property_code == file_info['property_code']
    ).first()
    
    if not property:
        print(f"  ❌ Property {file_info['property_code']} not found")
        return None
    
    # Get or create period
    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property.id,
        FinancialPeriod.period_year == file_info['year'],
        FinancialPeriod.period_month == file_info['month']
    ).first()
    
    if not period:
        period = FinancialPeriod(
            property_id=property.id,
            period_year=file_info['year'],
            period_month=file_info['month'],
            period_start_date=date(file_info['year'], file_info['month'], 1),
            period_end_date=date(file_info['year'], file_info['month'], 31),
            fiscal_year=file_info['year'],
            fiscal_quarter=4
        )
        db.add(period)
        db.commit()
        db.refresh(period)
    
    # Check if upload exists
    upload = db.query(DocumentUpload).filter(
        DocumentUpload.file_path == file_info['path']
    ).first()
    
    if upload:
        # Reset if previously failed
        if upload.extraction_status in ['failed', 'processing']:
            upload.extraction_status = 'pending'
            upload.extraction_started_at = None
            upload.extraction_completed_at = None
            upload.notes = None
            db.commit()
        return upload
    
    # Create new upload record
    file_name = file_info['path'].split('/')[-1]
    file_hash = hashlib.md5(file_info['path'].encode()).hexdigest()
    
    upload = DocumentUpload(
        property_id=property.id,
        period_id=period.id,
        document_type='cash_flow',
        file_name=file_name,
        file_path=file_info['path'],
        file_hash=file_hash,
        file_size_bytes=file_info['size'],
        upload_date=datetime.now(),
        extraction_status='pending'
    )
    
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    return upload

def trigger_extraction(upload_id):
    """Trigger extraction task via Celery"""
    from app.tasks.extraction_tasks import extract_document
    task = extract_document.delay(upload_id)
    return task.id

def collect_results(db, upload_id):
    """Collect extraction results from database"""
    upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
    
    if not upload:
        return None
    
    # Get Cash Flow Header
    header = db.query(CashFlowHeader).filter(
        CashFlowHeader.upload_id == upload_id
    ).first()
    
    # Get extracted line items
    line_items = db.query(CashFlowData).filter(
        CashFlowData.upload_id == upload_id
    ).all()
    
    # Calculate metrics
    total_records = len(line_items)
    matched_count = sum(1 for d in line_items if d.account_id is not None)
    match_rate = (matched_count / total_records * 100) if total_records > 0 else 0
    avg_confidence = sum(float(d.extraction_confidence or 0) for d in line_items) / total_records if total_records > 0 else 0
    
    # Get unmatched accounts
    unmatched = [
        {'code': d.account_code or '[no code]', 'name': d.account_name, 'amount': float(d.period_amount)}
        for d in line_items if d.account_id is None
    ]
    
    # Validate NOI calculation
    noi_valid = False
    if header:
        expected_noi = header.total_income - header.total_expenses
        actual_noi = header.net_operating_income
        noi_diff = abs(expected_noi - actual_noi) if expected_noi and actual_noi else None
        noi_valid = noi_diff < 0.01 if noi_diff is not None else False
    
    return {
        'upload_id': upload_id,
        'status': upload.extraction_status,
        'total_records': total_records,
        'matched_count': matched_count,
        'match_rate': match_rate,
        'avg_confidence': avg_confidence,
        'has_header': header is not None,
        'total_income': float(header.total_income) if header else 0,
        'total_expenses': float(header.total_expenses) if header else 0,
        'noi': float(header.net_operating_income) if header else 0,
        'net_income': float(header.net_income) if header else 0,
        'noi_valid': noi_valid,
        'unmatched': unmatched,
        'notes': upload.notes
    }

def main():
    """Run batch testing for all Cash Flow files"""
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║     BATCH CASH FLOW EXTRACTION TESTING                                ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    db = SessionLocal()
    results = []
    
    print(f"📋 Testing {len(TEST_FILES)} Cash Flow files...")
    print("=" * 70)
    print()
    
    for idx, file_info in enumerate(TEST_FILES, 1):
        print(f"🧪 Test {idx}/{len(TEST_FILES)}: {file_info['property_code']} {file_info['year']}")
        print(f"   File: {file_info['path'].split('/')[-1]} ({file_info['size']} bytes)")
        
        # Get or create upload record
        upload = get_or_create_upload_record(db, file_info)
        
        if not upload:
            print(f"   ❌ Failed to create upload record")
            results.append({
                'property': file_info['property_code'],
                'year': file_info['year'],
                'status': 'ERROR',
                'error': 'Failed to create upload record'
            })
            continue
        
        print(f"   Upload ID: {upload.id}")
        
        # Trigger extraction
        try:
            task_id = trigger_extraction(upload.id)
            print(f"   Task ID: {task_id}")
            print(f"   ⏳ Waiting 35 seconds for extraction...")
            time.sleep(35)  # Cash Flow may take slightly longer than Balance Sheet
            
            # Collect results
            result = collect_results(db, upload.id)
            
            if result:
                results.append({
                    'property': file_info['property_code'],
                    'year': file_info['year'],
                    'upload_id': upload.id,
                    **result
                })
                
                # Display results
                status_icon = "✅" if result['status'] == 'completed' else "❌"
                print(f"   {status_icon} Status: {result['status']}")
                print(f"   📊 Records: {result['total_records']}")
                print(f"   🎯 Match Rate: {result['match_rate']:.1f}%")
                print(f"   💯 Confidence: {result['avg_confidence']:.1f}%")
                print(f"   💰 Total Income: ${result['total_income']:,.2f}")
                print(f"   💸 Total Expenses: ${result['total_expenses']:,.2f}")
                print(f"   📈 NOI: ${result['noi']:,.2f}")
                print(f"   ⚖️  NOI Calc Valid: {'✅ YES' if result['noi_valid'] else '❌ NO'}")
                
            else:
                print(f"   ❌ Failed to collect results")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'property': file_info['property_code'],
                'year': file_info['year'],
                'status': 'ERROR',
                'error': str(e)
            })
        
        print()
    
    db.close()
    
    # Generate summary
    print()
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║     BATCH TESTING RESULTS - SUMMARY                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    completed = [r for r in results if r.get('status') == 'completed']
    failed = [r for r in results if r.get('status') in ['failed', 'ERROR']]
    
    print(f"Total Files Tested: {len(results)}")
    print(f"✅ Completed: {len(completed)}")
    print(f"❌ Failed: {len(failed)}")
    print()
    
    if completed:
        print("COMPLETED EXTRACTIONS:")
        print("─" * 70)
        print(f"{'Property':<12} {'Year':<6} {'Records':<10} {'Match%':<10} {'Conf%':<10} {'NOI Valid'}")
        print("─" * 70)
        
        for r in completed:
            noi_icon = "✅" if r.get('noi_valid') else "❌"
            print(f"{r['property']:<12} {r['year']:<6} {r.get('total_records', 0):<10} {r.get('match_rate', 0):<10.1f} {r.get('avg_confidence', 0):<10.1f} {noi_icon}")
        
        print()
        
        # Overall statistics
        avg_records = sum(r.get('total_records', 0) for r in completed) / len(completed)
        avg_match = sum(r.get('match_rate', 0) for r in completed) / len(completed)
        avg_conf = sum(r.get('avg_confidence', 0) for r in completed) / len(completed)
        all_noi_valid = all(r.get('noi_valid', False) for r in completed)
        
        print("OVERALL STATISTICS:")
        print(f"  Average Records: {avg_records:.1f}")
        print(f"  Average Match Rate: {avg_match:.1f}%")
        print(f"  Average Confidence: {avg_conf:.1f}%")
        print(f"  All NOI Valid: {'✅ YES' if all_noi_valid else '❌ NO'}")
        print()
    
    if failed:
        print("FAILED EXTRACTIONS:")
        print("─" * 70)
        for r in failed:
            print(f"  ❌ {r['property']} {r['year']}: {r.get('error', 'Unknown error')[:60]}")
        print()
    
    # Collect all unmatched accounts
    all_unmatched = {}
    for r in completed:
        for um in r.get('unmatched', []):
            key = um['code']
            if key not in all_unmatched:
                all_unmatched[key] = um
    
    if all_unmatched:
        print("UNMATCHED ACCOUNTS ACROSS ALL FILES:")
        print("─" * 70)
        for code, info in sorted(all_unmatched.items()):
            print(f"  • {code}: {info['name']}")
        print()
    
    # Production readiness assessment
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║     PRODUCTION READINESS ASSESSMENT                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    if len(completed) >= 6 and avg_match >= 85 and avg_conf >= 75 and all_noi_valid:
        print("✅ PRODUCTION-READY")
        print("   • High success rate")
        print("   • Excellent match rates")
        print("   • Good confidence scores")
        print("   • All NOI calculations valid")
        print()
        print("RECOMMENDATION: Cash Flow extraction is READY FOR PRODUCTION")
    else:
        print("⚠️  NEEDS REVIEW")
        print(f"   • Completed: {len(completed)}/{len(results)}")
        print(f"   • Avg Match: {avg_match:.1f}% (need ≥85%)")
        print(f"   • Avg Confidence: {avg_conf:.1f}% (need ≥75%)")
        print(f"   • All NOI Valid: {all_noi_valid}")
        print()
        print("RECOMMENDATION: Review failures before production deployment")
    
    print()
    return results

if __name__ == "__main__":
    results = main()
    
    # Return exit code based on results
    completed_count = sum(1 for r in results if r.get('status') == 'completed')
    sys.exit(0 if completed_count >= 6 else 1)

