"""
Test storekeeper login and JWT token.
"""
import requests
import json

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
    
    print(f"   Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   Error: {login_response.text}")
        return
    
    login_data = login_response.json()
    print(f"   ✓ Login successful")
    print(f"   User ID: {login_data.get('user_id')}")
    print(f"   Role: {login_data.get('role')}")
    print(f"   Token: {login_data.get('access_token')[:50]}...")
    
    token = login_data.get('access_token')
    
    # Step 2: Validate token with /auth/me
    print("\n2. Validating token with /auth/me...")
    me_response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Status: {me_response.status_code}")
    
    if me_response.status_code != 200:
        print(f"   Error: {me_response.text}")
        print("\n   ⚠ Token validation failed - this would cause logout!")
    else:
        me_data = me_response.json()
        print(f"   ✓ Token valid")
        print(f"   User: {me_data.get('user', {}).get('email')}")
        print(f"   Role: {me_data.get('user', {}).get('role')}")
        print(f"   Permissions: {me_data.get('permissions', [])[:5]}...")
    
    # Step 3: Test storekeeper dashboard endpoint
    print("\n3. Testing storekeeper dashboard endpoint...")
    dashboard_response = requests.get(
        f"{BASE_URL}/storekeeper/issue-queue",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"   Status: {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 200:
        print(f"   ✓ Dashboard endpoint accessible")
    elif dashboard_response.status_code == 401:
        print(f"   ⚠ Unauthorized - token might be invalid")
        print(f"   Error: {dashboard_response.text}")
    elif dashboard_response.status_code == 403:
        print(f"   ⚠ Forbidden - storekeeper doesn't have required permission")
        print(f"   Error: {dashboard_response.text}")
    else:
        print(f"   Error: {dashboard_response.text}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_login()
