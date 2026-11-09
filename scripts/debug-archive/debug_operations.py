"""Quick debug script to check operations in database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, text
from backend.app.infrastructure.persistence.database import create_engine
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


async def debug_check():
    """Check operations and tenants in database."""
    
    settings = get_settings()
    print("\n" + "=" * 80)
    print("DATABASE OPERATIONS DEBUG")
    print("=" * 80 + "\n")
    
    print(f"Database URL: {settings.database_url}\n")
    
    engine = create_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Check tenants
            print("📋 TENANTS:")
            print("-" * 80)
            tenants = await session.execute(select(TenantModel).where(TenantModel.is_deleted == False))
            tenant_list = tenants.scalars().all()
            if tenant_list:
                for tenant in tenant_list:
                    print(f"  ✓ {tenant.name} ({tenant.id})")
            else:
                print("  ⚠️  No tenants found!")
            
            print("\n")
            
            # Check operations count
            print("📊 OPERATIONS COUNT:")
            print("-" * 80)
            result = await session.execute(select(OperationModel).where(OperationModel.is_deleted == False))
            operations = result.scalars().all()
            print(f"  Total operations in DB: {len(operations)}")
            
            if operations:
                print("\n  Operations by tenant:")
                by_tenant = {}
                for op in operations:
                    if op.tenant_id not in by_tenant:
                        by_tenant[op.tenant_id] = []
                    by_tenant[op.tenant_id].append(op)
                
                for tid, ops in by_tenant.items():
                    tenant = next((t for t in tenant_list if t.id == tid), None)
                    tenant_name = tenant.name if tenant else "UNKNOWN"
                    print(f"    {tenant_name} ({tid}): {len(ops)} operations")
                    for op in ops:
                        status_str = "✓ ACTIVE" if op.is_active else "✗ INACTIVE"
                        print(f"      - {op.operation_code}: {op.name} {status_str}")
            else:
                print("  ⚠️  No operations found in database!")
            
            print("\n")
            
            # Run raw SQL to verify schema
            print("🔍 RAW SQL CHECK:")
            print("-" * 80)
            result = await session.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'operations'
                    ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            if columns:
                print("  Operations table columns:")
                for col, dtype in columns:
                    print(f"    - {col}: {dtype}")
            else:
                print("  ⚠️  Operations table not found in schema!")
            
            print("\n" + "=" * 80 + "\n")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(debug_check())
