"""
Test Mathematical Integrity API Endpoint

This script calls the exact API endpoint that the dashboard uses to see what data is being returned.
"""
import sys
import requests
sys.path.append('/app')

from app.db.database import SessionLocal

def main():
    property_id = 11
    period_id = 169
    
    print("=" * 80)
    print("TESTING MATHEMATICAL INTEGRITY API ENDPOINT")
    print("=" * 80)
    print(f"Property: {property_id}, Period: {period_id}\n")
    
    # Test the API endpoint directly (correct path)
    url = f"http://localhost:8000/api/v1/forensic-audit/math-integrity/{property_id}/{period_id}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("API RESPONSE DATA:")
            print("-" * 80)
            print(f"Overall Status: {data.get('passed_checks', 'N/A')} of {data.get('total_checks', 'N/A')} checks passed")
            print(f"Failed Checks: {data.get('failed_checks', 'N/A')}")
            print(f"Warnings: {data.get('warnings', 'N/A')}")
            print(f"Errors: {data.get('errors', 'N/A')}\n")
            
            if 'by_document' in data:
                print("BREAKDOWN BY DOCUMENT:")
                print("-" * 80)
                for doc in data['by_document']:
                    print(f"{doc.get('document_type', 'Unknown')}: {doc.get('passed', 0)}/{doc.get('total', 0)} passed")
            
            print("\n" + "=" * 80)
        else:
            print(f"ERROR: {response.text}")
            
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
