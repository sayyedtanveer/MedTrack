"""
Direct test of auth dependency for storekeeper.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.config import settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from backend.app.infrastructure.security.jwt_claim_validator import parse_tenant_claim, parse_user_claim


async def test_auth_dependency():
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    # Create JWT handler
    jwt_handler = JWTHandler(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expiry_minutes=settings.jwt_expiry_minutes
    )
    
    # Create a test token for storekeeper
    user_id = "ccc976e2-12ea-4c04-9d5b-19188dcc9229"
    tenant_id = "b5ef68c4-18be-4fa6-a439-a23c34877550"
    role = "storekeeper"
    
    access_token = jwt_handler.create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role
    )
    
    print("=" * 60)
    print("TESTING AUTH DEPENDENCY")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Tenant ID: {tenant_id}")
    print(f"Role: {role}")
    print(f"Token: {access_token[:50]}...")
    
    # Decode token
    print("\n1. Decoding token...")
    try:
        payload = jwt_handler.decode_token(access_token)
        print(f"   ✓ Token decoded successfully")
        print(f"   Payload keys: {list(payload.keys())}")
        print(f"   sub: {payload.get('sub')}")
        print(f"   tid: {payload.get('tid')}")
        print(f"   role: {payload.get('role')}")
    except Exception as e:
        print(f"   ✗ Failed to decode token: {e}")
        return
    
    # Test parse_tenant_claim
    print("\n2. Testing parse_tenant_claim...")
    try:
        parsed_tid = parse_tenant_claim(payload)
        print(f"   ✓ Tenant ID parsed: {parsed_tid}")
    except Exception as e:
        print(f"   ✗ Failed to parse tenant claim: {e}")
        import traceback
        traceback.print_exc()
    
    # Test parse_user_claim
    print("\n3. Testing parse_user_claim...")
    try:
        parsed_uid = parse_user_claim(payload)
        print(f"   ✓ User ID parsed: {parsed_uid}")
    except Exception as e:
        print(f"   ✗ Failed to parse user claim: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_auth_dependency())
