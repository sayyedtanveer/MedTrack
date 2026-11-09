"""
Test storekeeper login with backend exception logging.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
STOREKEEPER_EMAIL = "storekeeper.test@medtrack-demo.com"
STOREKEEPER_PASSWORD = "Storekeeper@1234"


def test_login():
    print("=" * 60)
    print("TESTING STOREKEEPER LOGIN")
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
    
    # Step 2: Decode JWT to see what's inside
    print("\n2. Decoding JWT token...")
    import base64
    parts = token.split('.')
    if len(parts) == 3:
        payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        print(f"   JWT Payload:")
        print(f"   - sub (user_id): {payload.get('sub')}")
        print(f"   - tid (tenant_id): {payload.get('tid')}")
        print(f"   - role: {payload.get('role')}")
        print(f"   - exp: {payload.get('exp')}")
        print(f"   - iat: {payload.get('iat')}")
    
    # Step 3: Test storekeeper dashboard endpoint
    print("\n3. Testing storekeeper dashboard endpoint...")
    print(f"   Token (first 50 chars): {token[:50]}...")
    
    dashboard_response = requests.get(
        f"{BASE_URL}/storekeeper/issue-queue",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": TENANT_ID
        }
    )
    
    print(f"   Status: {dashboard_response.status_code}")
    print(f"   Response: {dashboard_response.text}")
    
    # Step 4: Test a simpler endpoint that should work
    print("\n4. Testing /auth/me endpoint (should work)...")
    me_response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Status: {me_response.status_code}")
    if me_response.status_code == 200:
        print(f"   ✓ /auth/me works")
    else:
        print(f"   Error: {me_response.text}")
    
    # Step 5: Test inventory endpoint (storekeeper should have access)
    print("\n5. Testing /inventory endpoint (storekeeper should have access)...")
    inv_response = requests.get(
        f"{BASE_URL}/inventory",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Status: {inv_response.status_code}")
    if inv_response.status_code == 200:
        print(f"   ✓ /inventory works")
    elif inv_response.status_code == 401:
        print(f"   ⚠ Unauthorized - same issue as storekeeper endpoint")
    else:
        print(f"   Response: {inv_response.text}")
    
    print("\n" + "=" * 60)
    print("Check backend logs above for exception details")
    print("=" * 60)


if __name__ == "__main__":
    test_login()
