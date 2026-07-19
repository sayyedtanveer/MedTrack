"""
Script to create a storekeeper user using the admin API.
This is safer than direct database insertion.
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
ADMIN_EMAIL = "admin.e2e@medtrack-demo.com"
ADMIN_PASSWORD = "E2EAdmin@1234"

STOREKEEPER_EMAIL = "storekeeper.test@medtrack-demo.com"
STOREKEEPER_PASSWORD = "Storekeeper@1234"


def create_storekeeper_user():
    """Create a storekeeper user via the admin API."""
    
    # Step 1: Login as admin
    print("Step 1: Logging in as admin...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "tenant_id": TENANT_ID
        }
    )
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    admin_token = login_response.json()["access_token"]
    print("✓ Admin login successful")
    
    # Step 2: Create storekeeper user
    print("\nStep 2: Creating storekeeper user...")
    create_response = requests.post(
        f"{BASE_URL}/users",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-ID": TENANT_ID
        },
        json={
            "email": STOREKEEPER_EMAIL,
            "password": STOREKEEPER_PASSWORD,
            "first_name": "Test",
            "last_name": "Storekeeper",
            "role": "storekeeper",
            "is_active": True
        }
    )
    
    if create_response.status_code in [200, 201]:
        print("✓ Storekeeper user created successfully")
        user_data = create_response.json()
        print("\n" + "=" * 60)
        print("STOREKEEPER USER CREDENTIALS")
        print("=" * 60)
        print(f"Email: {STOREKEEPER_EMAIL}")
        print(f"Password: {STOREKEEPER_PASSWORD}")
        print(f"Tenant ID: {TENANT_ID}")
        print(f"User ID: {user_data.get('id', 'N/A')}")
        print(f"Role: storekeeper")
        print("=" * 60)
        print("\nYou can now login with these credentials to test work order flow.")
    elif create_response.status_code == 400 and "already exists" in create_response.text.lower():
        print("⚠ User already exists")
        print("\n" + "=" * 60)
        print("STOREKEEPER USER CREDENTIALS")
        print("=" * 60)
        print(f"Email: {STOREKEEPER_EMAIL}")
        print(f"Password: {STOREKEEPER_PASSWORD}")
        print(f"Tenant ID: {TENANT_ID}")
        print(f"Role: storekeeper")
        print("=" * 60)
        print("\nUser already exists. Use these credentials to login.")
    else:
        print(f"Failed to create user: {create_response.status_code}")
        print(create_response.text)


if __name__ == "__main__":
    create_storekeeper_user()
