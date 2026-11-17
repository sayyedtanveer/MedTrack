"""
Quick script to check if UOMs and Storage Locations exist in database
Run this to diagnose why dropdowns aren't appearing
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from backend.app.infrastructure.persistence.database import AsyncSessionLocal
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel


async def check_data():
    """Check what data exists in database"""
    print("=" * 70)
    print("CHECKING DATABASE FOR DROPDOWNS DATA")
    print("=" * 70)
    
    async with AsyncSessionLocal() as db:
        # Get first tenant
        tenant_result = await db.execute(select(TenantModel).where(TenantModel.is_deleted == False).limit(1))
        tenant = tenant_result.scalars().first()
        
        if not tenant:
            print("\n❌ ERROR: No tenants found in database!")
            return
        
        print(f"\n✅ Found tenant: {tenant.name} (ID: {tenant.id})")
        
        # Check UOMs
        print(f"\n{'='*70}")
        print("CHECKING UNITS OF MEASURE")
        print(f"{'='*70}")
        
        uom_result = await db.execute(
            select(UnitOfMeasureModel)
            .where(
                UnitOfMeasureModel.tenant_id == tenant.id,
                UnitOfMeasureModel.is_deleted == False,
                UnitOfMeasureModel.is_active == True
            )
            .order_by(UnitOfMeasureModel.code.asc())
        )
        uoms = uom_result.scalars().all()
        
        if uoms:
            print(f"\n✅ Found {len(uoms)} UOMs:")
            for uom in uoms:
                print(f"   - {uom.code} ({uom.name})")
        else:
            print("\n❌ NO UOMs found for this tenant!")
            print("   This is why Base Unit dropdown is empty!")
            print("\n   SOLUTION: Add UOMs using SQL:")
            print(f"""
   INSERT INTO units_of_measure (id, tenant_id, code, name, precision, is_active, is_deleted, created_at, updated_at)
   VALUES 
       (gen_random_uuid(), '{tenant.id}', 'KG', 'Kilogram', 3, true, false, NOW(), NOW()),
       (gen_random_uuid(), '{tenant.id}', 'MTR', 'Meter', 2, true, false, NOW(), NOW()),
       (gen_random_uuid(), '{tenant.id}', 'PCS', 'Pieces', 0, true, false, NOW(), NOW()),
       (gen_random_uuid(), '{tenant.id}', 'LTR', 'Liter', 2, true, false, NOW(), NOW());
            """)
        
        # Check Storage Locations
        print(f"\n{'='*70}")
        print("CHECKING STORAGE LOCATIONS")
        print(f"{'='*70}")
        
        loc_result = await db.execute(
            select(LocationModel)
            .where(
                LocationModel.tenant_id == tenant.id,
                LocationModel.is_deleted == False,
                LocationModel.is_active == True
            )
            .order_by(LocationModel.name.asc())
        )
        locations = loc_result.scalars().all()
        
        if locations:
            print(f"\n✅ Found {len(locations)} Storage Locations:")
            for loc in locations:
                code = loc.code if loc.code else "(no code)"
                default = " [DEFAULT]" if loc.is_default else ""
                print(f"   - {loc.name} ({code}){default}")
        else:
            print("\n❌ NO Storage Locations found for this tenant!")
            print("   This is why Storage Location dropdown is empty!")
            print("\n   SOLUTION: Add locations using SQL:")
            print(f"""
   INSERT INTO locations (id, tenant_id, code, name, location_type, is_active, is_default, is_deleted, created_at, updated_at)
   VALUES 
       (gen_random_uuid(), '{tenant.id}', 'MAIN-WH', 'Main Warehouse', 'WAREHOUSE', true, true, false, NOW(), NOW()),
       (gen_random_uuid(), '{tenant.id}', 'STORE-1', 'Storage Room 1', 'WAREHOUSE', true, false, false, NOW(), NOW());
            """)
        
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Tenant: {tenant.name}")
        print(f"UOMs configured: {len(uoms)}")
        print(f"Storage Locations configured: {len(locations)}")
        
        if len(uoms) == 0 or len(locations) == 0:
            print("\n⚠️  DROPDOWNS WILL NOT APPEAR because master data is missing!")
            print("   Run the SQL statements above to fix this.")
        else:
            print("\n✅ Master data exists - dropdowns should appear!")
            print("   If dropdowns still don't appear:")
            print("   1. Restart backend server")
            print("   2. Login to MedTrack")
            print("   3. Download template")
            print("   4. Check backend logs for errors")


if __name__ == "__main__":
    asyncio.run(check_data())
