"""
Check storekeeper user in database.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.config import settings


async def check_storekeeper():
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, email, role, is_active, is_deleted, tenant_id FROM users WHERE email = :email"),
            {"email": "storekeeper.test@medtrack-demo.com"}
        )
        user = result.fetchone()
        
        if user:
            print("=" * 60)
            print("STOREKEEPER USER FOUND IN DATABASE")
            print("=" * 60)
            print(f"ID: {user[0]}")
            print(f"Email: {user[1]}")
            print(f"Role: {user[2]}")
            print(f"Is Active: {user[3]}")
            print(f"Is Deleted: {user[4]}")
            print(f"Tenant ID: {user[5]}")
            print("=" * 60)
        else:
            print("Storekeeper user NOT found in database")
        
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_storekeeper())
