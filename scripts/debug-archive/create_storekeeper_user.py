"""
Script to create a storekeeper user for testing work order flow.
Run this script to generate storekeeper login credentials.
"""
import asyncio
import uuid
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from backend.app.config import settings


# Configuration
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
STOREKEEPER_EMAIL = "storekeeper.test@medtrack-demo.com"
STOREKEEPER_PASSWORD = "Storekeeper@1234"


async def create_storekeeper_user():
    """Create a storekeeper user in the database."""
    
    # Create async engine
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    password_hasher = BcryptPasswordHasher()
    hashed_password = password_hasher.hash(STOREKEEPER_PASSWORD)
    
    async with async_session() as session:
        try:
            # Check if user already exists
            from backend.app.infrastructure.persistence.models.user_model import UserModel
            from sqlalchemy import select
            
            result = await session.execute(
                select(UserModel).where(UserModel.email == STOREKEEPER_EMAIL)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"User {STOREKEEPER_EMAIL} already exists.")
                print(f"Email: {STOREKEEPER_EMAIL}")
                print(f"Password: {STOREKEEPER_PASSWORD}")
                print(f"Tenant ID: {TENANT_ID}")
                print(f"Role: {existing_user.role}")
                return
            
            # Create new storekeeper user
            user = UserModel(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(TENANT_ID),
                email=STOREKEEPER_EMAIL,
                hashed_password=hashed_password,
                first_name="Test",
                last_name="Storekeeper",
                role="storekeeper",
                is_active=True,
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            print("=" * 60)
            print("STOREKEEPER USER CREATED SUCCESSFULLY")
            print("=" * 60)
            print(f"Email: {STOREKEEPER_EMAIL}")
            print(f"Password: {STOREKEEPER_PASSWORD}")
            print(f"Tenant ID: {TENANT_ID}")
            print(f"User ID: {user.id}")
            print(f"Role: storekeeper")
            print("=" * 60)
            print("\nYou can now use these credentials to login as storekeeper")
            print("and test the work order release flow.")
            
        except Exception as e:
            await session.rollback()
            print(f"Error creating user: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_storekeeper_user())
