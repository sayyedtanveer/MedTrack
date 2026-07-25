import asyncio
import httpx
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings

async def test_api_qc_approve():
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    
    # 1. Get tenant ID from DB
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, name FROM tenants LIMIT 1"))
        tenant_row = res.fetchone()
        if not tenant_row:
            print("No tenant found!")
            return
        tenant_id = str(tenant_row[0])
        print(f"Using tenant: {tenant_row[1]} ({tenant_id})")
        
    await engine.dispose()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 2. Login
        login_data = {
            "email": "admin@medtrack.com",
            "password": "admin123",
            "tenant_id": tenant_id
        }
        print("Logging in...")
        login_resp = await client.post("http://localhost:5000/api/v1/auth/login", json=login_data)
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code} - {login_resp.text}")
            return
            
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!")
        
        # 3. Get pending work orders
        print("Fetching QC_PENDING work orders...")
        wo_resp = await client.get("http://localhost:5000/api/v1/work-orders/?status=QC_PENDING", headers=headers)
        if wo_resp.status_code != 200:
            print(f"Failed to fetch WOs: {wo_resp.status_code} - {wo_resp.text}")
            return
            
        wos = wo_resp.json().get("items", [])
        if not wos:
            print("No QC_PENDING work orders found.")
            return

        wo_id = wos[0]["id"]
        wo_number = wos[0]["wo_number"]
        print(f"Approving QC for WO: {wo_number} ({wo_id})")
        
        # 4. Approve QC
        approve_data = {
            "work_order_id": wo_id,
            "remarks": "Test approve from automated script"
        }
        resp = await client.post("http://localhost:5000/api/v1/quality-control/approve", headers=headers, json=approve_data)
        
        print("Status:", resp.status_code)
        try:
            print("Response:", resp.json())
        except:
            print("Response text:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_api_qc_approve())
