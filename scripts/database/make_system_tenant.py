import asyncio
import os
import sys
from uuid import UUID

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.infrastructure.persistence.database import async_session_factory
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from sqlalchemy import select, update

async def main():
    if len(sys.argv) != 2:
        print("Usage: poetry run python make_system_tenant.py <tenant_slug>")
        sys.exit(1)

    slug = sys.argv[1]
    
    async with async_session_factory() as session:
        # Find the tenant
        stmt = select(TenantModel).where(TenantModel.slug == slug)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print(f"Error: Tenant with slug '{slug}' not found.")
            sys.exit(1)
            
        if tenant.is_system_tenant:
            print(f"Tenant '{slug}' is already a system tenant!")
            sys.exit(0)
            
        # Update
        stmt = update(TenantModel).where(TenantModel.slug == slug).values(is_system_tenant=True)
        await session.execute(stmt)
        await session.commit()
        
        print(f"Success! Tenant '{slug}' has been promoted to a System Tenant.")
        print("Please log out and log back in for the changes to take effect.")

if __name__ == "__main__":
    asyncio.run(main())
