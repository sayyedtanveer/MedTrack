"""Debug script to test the full material onboarding workflow with supplier pricing."""

import json
import requests
import io
from datetime import datetime, timedelta

# Configuration
API_BASE = "http://127.0.0.1:8001"
TENANT_ID = "df413048-964e-45da-af55-91e90d7c54ee"

# Auth token from backend
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyYzc0MzUxOC0xZjYyLTQzYmUtODBlZC1jMDk5ODhiM2EwZWMiLCJ0aWQiOiJkZjQxMzA0OC05NjRlLTQ1ZGEtYWY1NS05MWU5MGQ3YzU0ZWUiLCJyb2xlIjoiYWRtaW4iLCJpYXQiOjE3OTQ1NTk5MDEsImV4cCI6MTc5NDU2MzUwMSwianRpIjoiZjEyMWMyODEtNDVmNy00ODc4LTkzYTktOWY5NDZhYTU3ZWI0In0.tYJJNQS8d0ibk6PL-Zsz-s8Bprq18nGR-U9qFHap82I"

def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-Tenant-ID": TENANT_ID,
    }

def create_test_csv():
    """Create a test CSV with supplier pricing fields."""
    csv_content = """Item Code,Material Name,Category,Base Unit,Opening Stock,Supplier Name,Supplier Price,Supplier Currency,Supplier MOQ,Supplier UOM,Effective From,Effective To,Proposed Initial Cost
MAT-SUPP-001,Raw Steel Supply,Raw Materials,KG,100,Acme Steel Inc,25.50,USD,50,KG,2026-11-09,,26.00
MAT-SUPP-002,Aluminum Ingot,Raw Materials,KG,200,Global Metals Corp,18.75,USD,100,KG,2026-11-09,,19.50
MAT-SUPP-003,Copper Wire,Raw Materials,METER,500,Premium Wires Ltd,2.30,USD,1000,METER,2026-11-09,,2.40
"""
    return csv_content.encode('utf-8')

def step1_upload_file():
    """Step 1: Upload file and create session."""
    print("\n" + "="*70)
    print("STEP 1: Upload File")
    print("="*70)
    
    url = f"{API_BASE}/api/v1/inventory/material-onboarding/sessions"
    
    files = {
        "file": ("test_supplier_pricing.csv", create_test_csv(), "text/csv")
    }
    
    response = requests.post(url, files=files, headers=get_headers())
    
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Error: {response.json()}")
        return None
    
    data = response.json()
    session_id = data.get("session_id")
    print(f"Session ID: {session_id}")
    print(f"Headers detected: {data.get('headers', [])[:5]}...")
    print(f"Mapping suggestions: {json.dumps(data.get('mapping', {}), indent=2)[:200]}...")
    
    return session_id

def step2_validate(session_id):
    """Step 2: Validate the session."""
    print("\n" + "="*70)
    print("STEP 2: Validate Session")
    print("="*70)
    
    url = f"{API_BASE}/api/v1/inventory/material-onboarding/sessions/{session_id}/validate"
    
    # Use the mapping from step 1
    validate_payload = {
        "mapping": {
            "Item Code": "item_code",
            "Material Name": "material_name",
            "Category": "material_category",
            "Base Unit": "uom",
            "Opening Stock": "opening_stock",
            "Supplier Name": "supplier_name",
            "Supplier Price": "supplier_price",
            "Supplier Currency": "supplier_currency",
            "Supplier MOQ": "supplier_moq",
            "Supplier UOM": "supplier_uom",
            "Effective From": "effective_from_date",
            "Effective To": "effective_to_date",
            "Proposed Initial Cost": "proposed_initial_cost",
        }
    }
    
    response = requests.post(url, json=validate_payload, headers=get_headers())
    
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Error: {response.json()}")
        return False
    
    data = response.json()
    print(f"Summary: {json.dumps(data.get('summary', {}), indent=2)}")
    print(f"Rows processed: {len(data.get('rows', []))}")
    
    return True

def step3_preview(session_id):
    """Step 3: Get preview."""
    print("\n" + "="*70)
    print("STEP 3: Preview")
    print("="*70)
    
    url = f"{API_BASE}/api/v1/inventory/material-onboarding/sessions/{session_id}/preview"
    
    response = requests.get(url, headers=get_headers())
    
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Error: {response.json()}")
        return False
    
    data = response.json()
    print(f"Preview summary: {json.dumps(data.get('summary', {}), indent=2)}")
    
    return True

def step4_execute(session_id):
    """Step 4: Execute the import."""
    print("\n" + "="*70)
    print("STEP 4: Execute Import")
    print("="*70)
    
    url = f"{API_BASE}/api/v1/inventory/material-onboarding/sessions/{session_id}/execute"
    
    execute_payload = {
        "dry_run": False,
        "duplicate_strategy": "SKIP"
    }
    
    response = requests.post(url, json=execute_payload, headers=get_headers())
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code >= 400:
        print(f"\n❌ EXECUTE FAILED")
        print("This is where the 400 Bad Request error occurs.")
        print("\nError details:")
        error_detail = response.json().get('detail', 'Unknown error')
        print(f"  {error_detail}")
        return False
    
    print(f"\n✅ EXECUTE SUCCEEDED")
    return True

def main():
    """Run the full onboarding workflow."""
    print("\n" + "="*70)
    print("MATERIAL ONBOARDING WORKFLOW TEST (WITH SUPPLIER PRICING)")
    print("="*70)
    
    # Step 1: Upload
    session_id = step1_upload_file()
    if not session_id:
        print("Failed to create session")
        return
    
    # Step 2: Validate
    if not step2_validate(session_id):
        print("Validation failed")
        return
    
    # Step 3: Preview
    if not step3_preview(session_id):
        print("Preview failed")
        return
    
    # Step 4: Execute
    if not step4_execute(session_id):
        print("\nFull workflow completed but execute endpoint returned error.")
        print("Need to check database tables and models.")
        return
    
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("="*70)

if __name__ == "__main__":
    main()
