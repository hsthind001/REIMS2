import requests
import sys
import json

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin" # Replace with valid user if needed, assuming admin exists from seed
PASSWORD = "admin" # Replace with valid password

def run_verification():
    print("🚀 Starting SaaS Verification...")
    
    session = requests.Session()
    
    # 1. Login
    print(f"\n1. Logging in as {USERNAME}...")
    try:
        login_resp = session.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            return
            
        user_data = login_resp.json()
        print("✅ Login successful")
        
        # 2. Check Organization Memberships
        print("\n2. Checking Organization Memberships...")
        orgs = user_data.get('organization_memberships', [])
        if not orgs:
            print("⚠️ No organization memberships found for user. verification limited.")
            # Create org if missing? For now just report.
        else:
            print(f"✅ Found {len(orgs)} organizations:")
            for org in orgs:
                print(f"   - {org['organization']['name']} (ID: {org['organization']['id']}, Role: {org['role']})")

        if not orgs:
            return

        target_org_id = orgs[0]['organization']['id']
        print(f"\n🎯 Target Organization ID: {target_org_id}")

        # 3. Test Property Creation (Tenancy Enforcement)
        print("\n3. Testing Property Creation (Tenancy Enforcement)...")
        
        prop_code = "SAAS001"
        prop_data = {
            "property_code": prop_code,
            "property_name": "SaaS Test Property",
            "status": "active"
        }
        
        # A. Without Header (Should fail if user has multiple orgs, or explicitly require it now?)
        # My implementation of get_current_organization tries to default if 1 org, or errors if multiple.
        # Let's see what happens.
        print("   a. Attempting without X-Organization-ID header...")
        try:
            resp_no_header = session.post(f"{BASE_URL}/properties/", json=prop_data)
            if resp_no_header.status_code == 201:
                print("   ⚠️ Created without header (User likely has single org, auto-resolved).")
                # Clean up
                prop_id = resp_no_header.json()['id']
                # session.delete(f"{BASE_URL}/properties/{prop_code}") 
            elif resp_no_header.status_code == 400:
                 print(f"   ✅ Correctly rejected/ambiguous: {resp_no_header.json()['detail']}")
            else:
                 print(f"   ℹ️ Response: {resp_no_header.status_code}")
        except Exception as e:
            print(f"   Error: {e}")

        # B. With Header
        print(f"   b. Attempting WITH X-Organization-ID: {target_org_id}...")
        headers = {"X-Organization-ID": str(target_org_id)}
        
        # Ensure unique code for this attempt
        prop_data['property_code'] = "SAAS003"
        
        resp_with_header = session.post(f"{BASE_URL}/properties/", json=prop_data, headers=headers)
        
        if resp_with_header.status_code == 201:
            print("   ✅ Property created successfully with Organization Context!")
            created_prop = resp_with_header.json()
            print(f"      ID: {created_prop['id']}, OrgID: {created_prop.get('organization_id')}")
            
            # Verify OrgID matches
            if created_prop.get('organization_id') == target_org_id:
                print("      ✅ Organization ID matches target.")
            else:
                print(f"      ❌ Organization ID Mismatch! Got {created_prop.get('organization_id')}")
                
            # Cleanup
            print("      Cleaning up...")
            session.delete(f"{BASE_URL}/properties/{prop_data['property_code']}", headers=headers)
            print("      Deleted.")
            
        else:
            print(f"   ❌ Failed to create property: {resp_with_header.status_code} - {resp_with_header.text}")

    except Exception as e:
        print(f"❌ Exception during verification: {e}")

if __name__ == "__main__":
    run_verification()
