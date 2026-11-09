"""Debug script to check operations by tenant."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from backend.app.infrastructure.persistence.database import create_engine
    from backend.app.config import settings
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, text
    
    # Import all models to register them
    import backend.app.infrastructure.persistence.models

    engine = create_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n" + "="*70)
        print("CHECKING TENANTS AND OPERATIONS")
        print("="*70 + "\n")

        # Query directly using SQL to avoid model relation issues
        result = await session.execute(text("""
            SELECT t.id, t.name, COUNT(o.id) as op_count
            FROM tenants t
            LEFT JOIN operations o ON o.tenant_id = t.id AND o.is_deleted = FALSE
            WHERE t.is_deleted = FALSE
            GROUP BY t.id, t.name
            ORDER BY t.name
        """))
        
        tenant_data = result.fetchall()
        
        if not tenant_data:
            print("⚠ No tenants found")
            return
            
        print(f"📊 Found {len(tenant_data)} tenant(s):\n")
        
        for tenant_id, tenant_name, op_count in tenant_data:
            print(f"  Tenant: {tenant_name}")
            print(f"  ID: {tenant_id}")
            print(f"  ├─ Operations: {op_count}")
            
            # List operations for this tenant
            ops = await session.execute(text("""
                SELECT operation_code, name, is_active 
                FROM operations 
                WHERE tenant_id = :tid AND is_deleted = FALSE
                ORDER BY default_sequence
            """), {"tid": tenant_id})
            
            for code, name, is_active in ops.fetchall():
                status = "✓" if is_active else "⊘"
                print(f"     └─ [{status}] {code}: {name}")
            print()
        
        print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
