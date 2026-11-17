"""Debug script to test material onboarding execute endpoint and capture the 400 error."""

import asyncio
import json
import requests
from datetime import datetime

# Configuration
API_BASE = "http://127.0.0.1:8001"
TENANT_ID = "df413048-964e-45da-af55-91e90d7c54ee"
USER_ID = "2c743518-1f62-43be-80ed-c09988b3a0ec"

# Auth token from the backend logs
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyYzc0MzUxOC0xZjYyLTQzYmUtODBlZC1jMDk5ODhiM2EwZWMiLCJ0aWQiOiJkZjQxMzA0OC05NjRlLTQ1ZGEtYWY1NS05MWU5MGQ3YzU0ZWUiLCJyb2xlIjoiYWRtaW4iLCJpYXQiOjE3OTQ1NTk5MDEsImV4cCI6MTc5NDU2MzUwMSwianRpIjoiZjEyMWMyODEtNDVmNy00ODc4LTkzYTktOWY5NDZhYTU3ZWI0In0.tYJJNQS8d0ibk6PL-Zsz-s8Bprq18nGR-U9qFHap82I"

def main():
    """Test the execute endpoint."""
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Tenant-ID": TENANT_ID,
        "Content-Type": "application/json",
    }
    
    # Use the session ID from the earlier test
    session_id = "f32dacb6-599a-476b-9efd-087d38d92eb8"  # From earlier test
    
    execute_payload = {
        "dry_run": False,
        "duplicate_strategy": "SKIP"
    }
    
    url = f"{API_BASE}/api/v1/inventory/material-onboarding/sessions/{session_id}/execute"
    
    print(f"\nExecuting POST {url}")
    print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
    print(f"Body: {json.dumps(execute_payload, indent=2)}")
    
    response = requests.post(url, json=execute_payload, headers=headers)
    
    print(f"\nStatus: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
    except:
        print(f"Response (raw): {response.text}")
    
    # If error, try to understand what went wrong
    if response.status_code >= 400:
        print(f"\n❌ ERROR: {response.status_code}")
        print("\nTroubleshooting steps:")
        print("1. Check backend logs for detailed error")
        print("2. Verify supplier_price_agreements table exists")
        print("3. Verify standard_cost_revisions table exists")
        print("4. Check if models are properly initialized")

if __name__ == "__main__":
    main()
