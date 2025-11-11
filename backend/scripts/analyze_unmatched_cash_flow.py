"""
Analyze Unmatched Cash Flow Accounts

Exports and analyzes the 762 unmatched cash flow accounts to identify:
- Missing accounts in chart_of_accounts
- OCR errors (0 vs O, 1 vs I, etc.)
- Name variations that fuzzy matching should catch
- Frequency of each unmatched account

Usage:
    python3 scripts/analyze_unmatched_cash_flow.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.cash_flow_data import CashFlowData
from app.models.financial_period import FinancialPeriod
from app.models.chart_of_accounts import ChartOfAccounts
from sqlalchemy import func
import csv
from datetime import datetime


def analyze_unmatched_accounts():
    """Export and analyze unmatched cash flow accounts"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("UNMATCHED CASH FLOW ACCOUNTS ANALYSIS")
        print("=" * 80)
        
        # Query unmatched accounts with statistics
        query = db.query(
            CashFlowData.account_code,
            CashFlowData.account_name,
            func.count(CashFlowData.id).label('occurrence_count'),
            func.avg(CashFlowData.extraction_confidence).label('avg_extraction_conf'),
            func.min(FinancialPeriod.period_year).label('first_year'),
            func.max(FinancialPeriod.period_year).label('last_year'),
            func.count(func.distinct(CashFlowData.property_id)).label('property_count')
        ).join(
            FinancialPeriod, CashFlowData.period_id == FinancialPeriod.id
        ).filter(
            CashFlowData.account_id == None
        ).group_by(
            CashFlowData.account_code,
            CashFlowData.account_name
        ).order_by(
            func.count(CashFlowData.id).desc()
        ).all()
        
        print(f"\n📊 Found {len(query)} unique unmatched account codes/names")
        print(f"   Total unmatched records: {sum(r.occurrence_count for r in query)}")
        
        # Export to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'unmatched_cash_flow_accounts_{timestamp}.csv'
        
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Account Code',
                'Account Name',
                'Occurrences',
                'Avg Extraction Conf',
                'First Year',
                'Last Year',
                'Properties',
                'Potential Match in COA',
                'Match Type'
            ])
            
            # Get all chart of accounts for fuzzy matching
            all_accounts = db.query(ChartOfAccounts).filter(
                ChartOfAccounts.is_active == True
            ).all()
            
            print("\n" + "=" * 80)
            print("TOP 20 UNMATCHED ACCOUNTS:")
            print("=" * 80)
            print(f"{'Code':<15} {'Name':<40} {'Count':>6} {'Conf':>6} {'Match Suggestion':<30}")
            print("-" * 80)
            
            for idx, row in enumerate(query[:50], 1):
                # Try to find potential matches
                potential_match = None
                match_type = None
                
                # Check for exact code match (shouldn't find any)
                for acc in all_accounts:
                    if row.account_code and acc.account_code == row.account_code:
                        potential_match = f"{acc.account_code} - {acc.account_name}"
                        match_type = "EXACT_CODE (shouldn't happen)"
                        break
                
                # Check for similar names
                if not potential_match and row.account_name:
                    from fuzzywuzzy import fuzz
                    best_match = None
                    best_score = 0
                    for acc in all_accounts:
                        score = fuzz.token_set_ratio(row.account_name.lower(), acc.account_name.lower())
                        if score > best_score and score >= 80:
                            best_score = score
                            best_match = acc
                    
                    if best_match:
                        potential_match = f"{best_match.account_code} - {best_match.account_name}"
                        match_type = f"FUZZY_NAME ({best_score}%)"
                
                if not potential_match:
                    potential_match = "NO MATCH FOUND"
                    match_type = "MISSING"
                
                # Print top 20
                if idx <= 20:
                    code_display = (row.account_code or '')[:14]
                    name_display = (row.account_name or '')[:39]
                    conf_display = f"{float(row.avg_extraction_conf or 0):.1f}%"
                    match_display = potential_match[:29]
                    
                    print(f"{code_display:<15} {name_display:<40} {row.occurrence_count:>6} {conf_display:>6} {match_display:<30}")
                
                # Write to CSV
                writer.writerow([
                    row.account_code or '',
                    row.account_name or '',
                    row.occurrence_count,
                    round(float(row.avg_extraction_conf or 0), 2),
                    row.first_year,
                    row.last_year,
                    row.property_count,
                    potential_match,
                    match_type
                ])
        
        print("-" * 80)
        print(f"\n✅ Full analysis exported to: {csv_filename}")
        print(f"\n📋 SUMMARY:")
        print(f"   - Unique unmatched accounts: {len(query)}")
        print(f"   - Total unmatched records: {sum(r.occurrence_count for r in query)}")
        print(f"   - CSV file: {csv_filename}")
        
        # Categorize by match type
        missing_count = 0
        fuzzy_match_count = 0
        
        for row in query:
            # Try fuzzy match
            found_fuzzy = False
            if row.account_name:
                from fuzzywuzzy import fuzz
                for acc in all_accounts:
                    score = fuzz.token_set_ratio(row.account_name.lower(), acc.account_name.lower())
                    if score >= 80:
                        found_fuzzy = True
                        break
            
            if found_fuzzy:
                fuzzy_match_count += 1
            else:
                missing_count += 1
        
        print(f"\n📊 CATEGORIZATION:")
        print(f"   - Could match with better fuzzy logic: {fuzzy_match_count}")
        print(f"   - Genuinely missing from COA: {missing_count}")
        print(f"   - Total: {len(query)}")
        
        print("\n💡 RECOMMENDATIONS:")
        if fuzzy_match_count > 0:
            print(f"   1. {fuzzy_match_count} accounts could match with current COA")
            print(f"      → Check if intelligent matching is working correctly")
        if missing_count > 0:
            print(f"   2. {missing_count} accounts need to be added to chart_of_accounts")
            print(f"      → Review CSV and create SQL INSERT statements")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    analyze_unmatched_accounts()

