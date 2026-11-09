"""
Script to create a storekeeper user using raw SQL.
This bypasses ORM foreign key constraints.
"""
import asyncio
import uuid
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from backend.app.config import settings


# Configuration
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
STOREKEEPER_EMAIL = "storekeeper.test@medtrack-demo.com"
STOREKEEPER_PASSWORD = "Storekeeper@1234"


async def create_storekeeper_user():
    """Create a storekeeper user using raw SQL."""
    
    # Create async engine
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    password_hasher = BcryptPasswordHasher()
    hashed_password = password_hasher.hash(STOREKEEPER_PASSWORD)
    user_id = str(uuid.uuid4())
    
    async with engine.begin() as conn:
        try:
            # Check if user already exists
            result = await conn.execute(
                text("SELECT id, email, role FROM users WHERE email = :email"),
                {"email": STOREKEEPER_EMAIL}
            )
            existing_user = result.fetchone()
            
            if existing_user:
                print(f"User {STOREKEEPER_EMAIL} already exists.")
                print("=" * 60)
                print("STOREKEEPER USER CREDENTIALS")
                print("=" * 60)
                print(f"Email: {STOREKEEPER_EMAIL}")
                print(f"Password: {STOREKEEPER_PASSWORD}")
                print(f"Tenant ID: {TENANT_ID}")
                print(f"User ID: {existing_user[0]}")
                print(f"Role: {existing_user[2]}")
                print("=" * 60)
                return
            
            # Insert user using raw SQL
            await conn.execute(
                text("""INSERT INTO users 
                   (id, tenant_id, email, hashed_password, first_name, last_name, role, is_active, 
                    totp_enabled, backup_codes, is_deleted, created_at, updated_at)
                   VALUES (:id, :tenant_id, :email, :hashed_password, :first_name, :last_name, 
                           :role, :is_active, :totp_enabled, :backup_codes, :is_deleted, NOW(), NOW())"""),
                {
                    "id": user_id,
                    "tenant_id": TENANT_ID,
                    "email": STOREKEEPER_EMAIL,
                    "hashed_password": hashed_password,
                    "first_name": "Test",
                    "last_name": "Storekeeper",
                    "role": "storekeeper",
                    "is_active": True,
                    "totp_enabled": False,
                    "backup_codes": "[]",
                    "is_deleted": False
                }
            )
            
            print("=" * 60)
            print("STOREKEEPER USER CREATED SUCCESSFULLY")
            print("=" * 60)
            print(f"Email: {STOREKEEPER_EMAIL}")
            print(f"Password: {STOREKEEPER_PASSWORD}")
            print(f"Tenant ID: {TENANT_ID}")
            print(f"User ID: {user_id}")
            print(f"Role: storekeeper")
            print("=" * 60)
            print("\nYou can now use these credentials to login as storekeeper")
            print("and test the work order release flow.")
            
        except Exception as e:
            print(f"Error creating user: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_storekeeper_user())
