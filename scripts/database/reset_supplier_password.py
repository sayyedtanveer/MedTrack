import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from passlib.context import CryptContext

async def update_password():
    # Initialize bcrypt context (same as backend uses)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Hash the password
    new_password = "Erp@1234"
    hashed = pwd_context.hash(new_password)
    
    engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
    async with engine.begin() as conn:
        # Update the password
        result = await conn.execute(sa.text("""
            UPDATE users 
            SET hashed_password = :pwd_hash, updated_at = NOW()
            WHERE email = :email AND tenant_id = :tenant_id
            RETURNING id, email
        """), {
            'email': 'test_supplier@synapse-erp.com',
            'tenant_id': '6e3be467-7ed3-4503-a709-d6c1fce9b1a5',
            'pwd_hash': hashed
        })
        row = result.fetchone()
        
        if row:
            print(f"✓ Password updated for {row[1]}")
            print(f"  Password: {new_password}")
            print(f"  New hash: {hashed[:20]}...")
        else:
            print("✗ User not found")
    
    await engine.dispose()

asyncio.run(update_password())
