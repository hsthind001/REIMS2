"""
Test the updated Collections Quality API endpoint
"""
import sys
import requests
sys.path.append('/app')

def main():
    property_id = 11
    period_id = 169
    
    print("=" * 80)
    print("TESTING COLLECTIONS QUALITY API (After Fix)")
    print("=" * 80)
    
    url = f"http://localhost:8000/api/v1/forensic-audit/collections-quality/{property_id}/{period_id}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("REVENUE QUALITY:")
            print("-" * 80)
            revenue = data.get('revenue_quality', {})
            print(f"Quality Score: {revenue.get('quality_score')}")
            print(f"Total Revenue: ${revenue.get('total_revenue'):,.2f}")
            print(f"Collectible Revenue: ${revenue.get('collectible_revenue'):,.2f}")
            print(f"At-Risk Revenue: ${revenue.get('at_risk_revenue'):,.2f}")
            print(f"Collectible %: {revenue.get('collectible_pct'):.1f}%")
            
            print("\n\nCASH CONVERSION:")
            print("-" * 80)
            cash_conv = data.get('cash_conversion', {})
            print(f"Revenue Recognized: ${cash_conv.get('revenue_recognized'):,.2f}")
            print(f"Cash Collected: ${cash_conv.get('cash_collected'):,.2f}")
            print(f"Conversion Ratio: {cash_conv.get('conversion_ratio'):.1%}")
            
            print("\n\nA/R AGING:")
            print("-" * 80)
            ar = data.get('ar_aging', {})
            print(f"Total A/R: ${ar.get('total_ar'):,.2f}")
            print(f"Current (0-30): ${ar.get('current_0_30'):,.2f}")
            
        else:
            print(f"ERROR: {response.text}")
            
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
