"""
Test storekeeper login with detailed error output.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
STOREKEEPER_EMAIL = "storekeeper.test@medtrack-demo.com"
STOREKEEPER_PASSWORD = "Storekeeper@1234"


def test_login():
    print("=" * 60)
    print("TESTING STOREKEEPER LOGIN WITH DETAILED ERRORS")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Attempting login...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": STOREKEEPER_EMAIL,
            "password": STOREKEEPER_PASSWORD,
            "tenant_id": TENANT_ID
        }
    )
    
    if login_response.status_code != 200:
        print(f"   Error: {login_response.text}")
        return
    
    login_data = login_response.json()
    print(f"   ✓ Login successful - Role: {login_data.get('role')}")
    
    token = login_data.get('access_token')
    
    # Step 2: Test storekeeper dashboard endpoint with detailed error
    print("\n2. Testing storekeeper dashboard endpoint...")
    dashboard_response = requests.get(
        f"{BASE_URL}/storekeeper/issue-queue",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Status: {dashboard_response.status_code}")
    print(f"   Full Response: {dashboard_response.text}")
    
    # Step 3: Test with X-Tenant-ID header as well
    print("\n3. Testing with X-Tenant-ID header...")
    dashboard_response2 = requests.get(
        f"{BASE_URL}/storekeeper/issue-queue",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": TENANT_ID
        }
    )
    
    print(f"   Status: {dashboard_response2.status_code}")
    print(f"   Full Response: {dashboard_response2.text}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_login()
