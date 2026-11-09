"""
Example: Testing Centralized Error Logging System

This script demonstrates how to trigger different error scenarios
and verify the error logging system is working correctly.

Run this after deploying the system:
1. Start the FastAPI app
2. Run this script
3. Query the error_logs table to verify entries
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_validation_error():
    """Test 400 VALIDATION_ERROR handling."""
    print_section("Test 1: Validation Error (400)")
    
    # Example: Missing required field
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "test@example.com"}  # Missing password
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Query database: SELECT * FROM error_logs WHERE trace_id = '{trace_id}';")
    
    return trace_id


def test_auth_error():
    """Test 401 AUTH_FAILED handling."""
    print_section("Test 2: Auth Error (401)")
    
    # Example: Invalid credentials
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Verify filtering: password should be [REDACTED] in DB")
    
    return trace_id


def test_permission_error():
    """Test 403 FORBIDDEN handling."""
    print_section("Test 3: Permission Error (403)")
    
    # Example: Delete user without admin role
    # (Assumes you have a valid but non-admin token)
    headers = {"Authorization": "Bearer invalid-token"}
    response = requests.delete(
        f"{BASE_URL}/admin/users/{uuid.uuid4()}",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Verify: Authorization header should NOT appear in DB (filtered)")
    
    return trace_id


def test_not_found_error():
    """Test 404 NOT_FOUND handling."""
    print_section("Test 4: Not Found Error (404)")
    
    # Example: Get non-existent resource
    fake_id = uuid.uuid4()
    response = requests.get(f"{BASE_URL}/users/{fake_id}")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Expected error_code: NOT_FOUND")
    
    return trace_id


def test_internal_error():
    """Test 500 INTERNAL_ERROR handling."""
    print_section("Test 5: Internal Server Error (500)")
    
    # Example: Trigger an unhandled exception
    # This would be any endpoint that crashes unexpectedly
    response = requests.get(f"{BASE_URL}/broken-endpoint")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Expected: Full stack trace in DB for debugging")
        print(f"Expected: file_name and line_number populated")
    
    return trace_id


def test_large_request_body():
    """Test request body truncation at 5KB."""
    print_section("Test 6: Large Request Body (Truncation)")
    
    # Create a 6KB payload
    large_payload = {"data": "x" * (6 * 1024)}
    
    response = requests.post(
        f"{BASE_URL}/process",
        json=large_payload
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Verify in DB:")
        print(f"  - request_body_truncated: TRUE")
        print(f"  - request_body length: <= 5120 bytes")
    
    return trace_id


def test_sensitive_field_filtering():
    """Test sensitive field filtering in request body."""
    print_section("Test 7: Sensitive Field Filtering")
    
    # Request with sensitive fields
    response = requests.post(
        f"{BASE_URL}/users",
        json={
            "email": "user@example.com",
            "password": "SecretPassword123",
            "confirm_password": "SecretPassword123",
            "access_token": "jwt-token-123",
            "api_key": "api-key-456"
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")
    
    trace_id = data.get("error", {}).get("trace_id")
    if trace_id:
        print(f"\nTrace ID: {trace_id}")
        print(f"Verify in DB request_body:")
        print(f"  - email: user@example.com (visible)")
        print(f"  - password: [REDACTED] (filtered)")
        print(f"  - confirm_password: [REDACTED] (filtered)")
        print(f"  - access_token: [REDACTED] (filtered)")
        print(f"  - api_key: [REDACTED] (filtered)")
    
    return trace_id


def verify_database():
    """Instructions for verifying in database."""
    print_section("Verify Error Logs in Database")
    
    sql = """
    -- Count total errors
    SELECT COUNT(*) as total_errors FROM error_logs;
    
    -- Show recent errors
    SELECT 
        trace_id, 
        timestamp, 
        status_code, 
        error_code, 
        error_type,
        path,
        file_name,
        line_number
    FROM error_logs
    ORDER BY timestamp DESC
    LIMIT 10;
    
    -- Check filtering (should see [REDACTED])
    SELECT 
        trace_id,
        request_body,
        request_body_truncated
    FROM error_logs
    WHERE request_body IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 5;
    
    -- Check header filtering (no Authorization)
    SELECT 
        trace_id,
        headers
    FROM error_logs
    WHERE headers IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 5;
    """
    
    print("Run these SQL queries in your database:\n")
    print(sql)


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  CENTRALIZED ERROR LOGGING SYSTEM - TEST SUITE")
    print("=" * 60)
    print("\nMake sure the FastAPI app is running on localhost:8000")
    print("These tests will trigger various error scenarios\n")
    
    trace_ids = {}
    
    try:
        trace_ids["validation"] = test_validation_error()
    except Exception as e:
        print(f"Error in validation test: {e}")
    
    try:
        trace_ids["auth"] = test_auth_error()
    except Exception as e:
        print(f"Error in auth test: {e}")
    
    try:
        trace_ids["permission"] = test_permission_error()
    except Exception as e:
        print(f"Error in permission test: {e}")
    
    try:
        trace_ids["not_found"] = test_not_found_error()
    except Exception as e:
        print(f"Error in not_found test: {e}")
    
    try:
        trace_ids["internal"] = test_internal_error()
    except Exception as e:
        print(f"Error in internal test: {e}")
    
    try:
        trace_ids["large_body"] = test_large_request_body()
    except Exception as e:
        print(f"Error in large_body test: {e}")
    
    try:
        trace_ids["sensitive"] = test_sensitive_field_filtering()
    except Exception as e:
        print(f"Error in sensitive test: {e}")
    
    # Verify database
    verify_database()
    
    # Summary
    print_section("Test Summary")
    print(f"Total trace IDs captured: {len([t for t in trace_ids.values() if t])}")
    for test_name, trace_id in trace_ids.items():
        if trace_id:
            print(f"  ✓ {test_name}: {trace_id}")
        else:
            print(f"  ✗ {test_name}: No trace_id returned")
    
    print("\n" + "=" * 60)
    print("  NEXT STEPS")
    print("=" * 60)
    print("""
1. Run the SQL queries above to verify error_logs table contents
2. Check that sensitive fields are [REDACTED] in request_body
3. Verify Authorization header is NOT in headers column
4. Confirm file_name and line_number are populated
5. Check request_body_truncated flag for large payloads

If all checks pass: Error logging system is working correctly! ✓
    """)


if __name__ == "__main__":
    main()
