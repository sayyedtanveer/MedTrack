"""
Simplified test data creator for semi-finished material BOM testing.

This script creates:
1. 10 Raw Materials (RM-001 to RM-010)
2. 1 Semi-Finished Material (SF-MECH-ASSY)
3. 1 Semi-Finished Product Template (TPL-MECH-ASSY)
4. BOM for Semi-Finished (using 10 raw materials)
5. 1 Main Product Template (FG-GEAR-ROTAMETER)
6. BOM for Main Product using semi-finished MATERIAL (tests NEW feature)
7. BOM for Main Product using semi-finished TEMPLATE (traditional approach)
"""
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


def read_db_url() -> str:
    """Read DATABASE_URL from .env file."""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        raise RuntimeError(".env file not found")
    
    for line in env_file.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            # Ensure asyncpg driver
            if url.startswith("postgresql://") and "asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
    raise RuntimeError("DATABASE_URL not found in .env")


async def get_tenant_id(session: AsyncSession) -> uuid.UUID:
    """Get the first active tenant ID."""
    result = await session.execute(
        text("SELECT id FROM tenants WHERE is_deleted = false LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        raise RuntimeError("No active tenant found. Please create a tenant first.")
    return row[0]


async def get_or_create_unit(session: AsyncSession, tenant_id: uuid.UUID, code: str = "PCS") -> uuid.UUID:
    """Get or create a unit of measure."""
    result = await session.execute(
        text("""
            SELECT id FROM units_of_measure 
            WHERE tenant_id = :tenant_id AND code = :code
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "code": code}
    )
    row = result.fetchone()
    if row:
        return row[0]
    
    # Create the unit
    unit_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO units_of_measure (id, tenant_id, name, code, created_at, updated_at, is_deleted)
            VALUES (:id, :tenant_id, :name, :code, :now, :now, false)
        """),
        {
            "id": unit_id,
            "tenant_id": tenant_id,
            "name": "Pieces",
            "code": code,
            "now": datetime.now(timezone.utc)
        }
    )
    print(f"  ✓ Created unit: {code}")
    return unit_id


async def create_raw_materials(session: AsyncSession, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> list[uuid.UUID]:
    """Create 10 raw materials."""
    print("\n📦 Creating 10 Raw Materials...")
    
    raw_materials = [
        ("RM-TEST-001", "Steel Shaft"),
        ("RM-TEST-002", "Bearing"),
        ("RM-TEST-003", "Gear Wheel"),
        ("RM-TEST-004", "Spring"),
        ("RM-TEST-005", "Bolt M6"),
        ("RM-TEST-006", "Washer"),
        ("RM-TEST-007", "Gasket"),
        ("RM-TEST-008", "O-Ring"),
        ("RM-TEST-009", "Housing Body"),
        ("RM-TEST-010", "Cover Plate"),
    ]
    
    material_ids = []
    now = datetime.now(timezone.utc)
    
    for code, name in raw_materials:
        material_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO materials 
                (id, tenant_id, code, name, material_type, base_unit_id, 
                 current_stock, reserved_stock, is_batch_tracked, is_serialized,
                 inspection_required, hazardous_flag, qc_required_flag,
                 is_active, is_deleted, created_at, updated_at)
                VALUES 
                (:id, :tenant_id, :code, :name, 'raw', :unit_id,
                 0, 0, false, false, false, false, false,
                 true, false, :now, :now)
            """),
            {
                "id": material_id,
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "unit_id": unit_id,
                "now": now
            }
        )
        material_ids.append(material_id)
        print(f"  ✓ {code}: {name}")
    
    return material_ids


async def create_semi_finished_material(session: AsyncSession, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> uuid.UUID:
    """Create semi-finished material."""
    print("\n🔧 Creating Semi-Finished Material...")
    
    material_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO materials 
            (id, tenant_id, code, name, material_type, base_unit_id,
             current_stock, reserved_stock, is_batch_tracked, is_serialized,
             inspection_required, hazardous_flag, qc_required_flag,
             is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :name, 'semi_finished', :unit_id,
             0, 0, false, false, false, false, false,
             true, false, :now, :now)
        """),
        {
            "id": material_id,
            "tenant_id": tenant_id,
            "code": "SF-TEST-ASSY",
            "name": "Test Sub-Assembly (Semi-Finished)",
            "unit_id": unit_id,
            "now": now
        }
    )
    print(f"  ✓ SF-TEST-ASSY: Test Sub-Assembly (Semi-Finished)")
    
    return material_id


async def create_semi_finished_template(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create product template for semi-finished item."""
    print("\n📋 Creating Semi-Finished Product Template...")
    
    template_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO item_templates 
            (id, tenant_id, code, name, attributes, status, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :name, '[]'::jsonb, 'ACTIVE', true, false, :now, :now)
        """),
        {
            "id": template_id,
            "tenant_id": tenant_id,
            "code": "TPL-TEST-ASSY",
            "name": "Test Sub-Assembly Template",
            "now": now
        }
    )
    print(f"  ✓ TPL-TEST-ASSY: Test Sub-Assembly Template")
    
    return template_id


async def create_semi_finished_bom(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    raw_material_ids: list[uuid.UUID],
    unit_id: uuid.UUID
) -> uuid.UUID:
    """Create BOM for semi-finished template using 10 raw materials."""
    print("\n📝 Creating BOM for Semi-Finished Template...")
    
    bom_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Create BOM
    await session.execute(
        text("""
            INSERT INTO bill_of_materials 
            (id, tenant_id, template_id, version, valid_from, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :template_id, :version, :valid_from, true, false, :now, :now)
        """),
        {
            "id": bom_id,
            "tenant_id": tenant_id,
            "template_id": template_id,
            "version": "v1.0",
            "valid_from": now,
            "now": now
        }
    )
    
    # Create BOM lines for 10 raw materials
    quantities = [1, 2, 1, 1, 4, 4, 1, 2, 1, 1]  # Different quantities for variety
    
    for idx, (material_id, qty) in enumerate(zip(raw_material_ids, quantities), start=1):
        line_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO bom_lines 
                (id, bom_id, material_id, quantity, scrap_percentage, unit_id, line_number, created_at, updated_at)
                VALUES 
                (:id, :bom_id, :material_id, :quantity, 0, :unit_id, :line_number, :now, :now)
            """),
            {
                "id": line_id,
                "bom_id": bom_id,
                "material_id": material_id,
                "quantity": Decimal(str(qty)),
                "unit_id": unit_id,
                "line_number": idx,
                "now": now
            }
        )
    
    print(f"  ✓ BOM created with 10 raw material lines")
    
    return bom_id


async def create_main_product_template(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create main product template (FG Rotameter)."""
    print("\n🏭 Creating Main Product Template...")
    
    template_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO item_templates 
            (id, tenant_id, code, name, attributes, status, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :name, '[]'::jsonb, 'ACTIVE', true, false, :now, :now)
        """),
        {
            "id": template_id,
            "tenant_id": tenant_id,
            "code": "FG-TEST-ROTAMETER",
            "name": "Test Gear Rotameter",
            "now": now
        }
    )
    print(f"  ✓ FG-TEST-ROTAMETER: Test Gear Rotameter")
    
    return template_id


async def create_main_product_bom_with_material(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    semi_finished_material_id: uuid.UUID,
    unit_id: uuid.UUID
) -> uuid.UUID:
    """Create BOM for main product using semi-finished MATERIAL."""
    print("\n📝 Creating BOM for Main Product (using semi-finished material)...")
    
    bom_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Create BOM
    await session.execute(
        text("""
            INSERT INTO bill_of_materials 
            (id, tenant_id, template_id, version, valid_from, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :template_id, :version, :valid_from, true, false, :now, :now)
        """),
        {
            "id": bom_id,
            "tenant_id": tenant_id,
            "template_id": template_id,
            "version": "v1.0-material",
            "valid_from": now,
            "now": now
        }
    )
    
    # Create BOM line with semi-finished material
    line_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO bom_lines 
            (id, bom_id, material_id, quantity, scrap_percentage, unit_id, line_number, created_at, updated_at)
            VALUES 
            (:id, :bom_id, :material_id, :quantity, 0, :unit_id, 1, :now, :now)
        """),
        {
            "id": line_id,
            "bom_id": bom_id,
            "material_id": semi_finished_material_id,
            "quantity": Decimal("1"),
            "unit_id": unit_id,
            "now": now
        }
    )
    
    print(f"  ✓ BOM created with semi-finished material line (SF-TEST-ASSY)")
    print(f"  ⭐ This tests the NEW functionality - semi-finished as material component!")
    
    return bom_id


async def create_main_product_bom_with_template(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    main_template_id: uuid.UUID,
    semi_template_id: uuid.UUID
) -> uuid.UUID:
    """Create alternative BOM for main product using semi-finished TEMPLATE."""
    print("\n📝 Creating ALTERNATIVE BOM (using template reference)...")
    
    bom_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Create BOM
    await session.execute(
        text("""
            INSERT INTO bill_of_materials 
            (id, tenant_id, template_id, version, valid_from, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :template_id, :version, :valid_from, false, false, :now, :now)
        """),
        {
            "id": bom_id,
            "tenant_id": tenant_id,
            "template_id": main_template_id,
            "version": "v1.0-template",
            "valid_from": now,
            "now": now
        }
    )
    
    # Create BOM line with template reference
    line_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO bom_lines 
            (id, bom_id, template_id, quantity, scrap_percentage, line_number, created_at, updated_at)
            VALUES 
            (:id, :bom_id, :template_id, :quantity, 0, 1, :now, :now)
        """),
        {
            "id": line_id,
            "bom_id": bom_id,
            "template_id": semi_template_id,
            "quantity": Decimal("1"),
            "now": now
        }
    )
    
    print(f"  ✓ Alternative BOM created with template reference (TPL-TEST-ASSY)")
    print(f"  ℹ This is the TRADITIONAL approach - template has built-in BOM link")
    
    return bom_id


async def print_summary(session: AsyncSession, tenant_id: uuid.UUID):
    """Print summary of created data."""
    print("\n" + "="*70)
    print("📊 DATA CREATION SUMMARY")
    print("="*70)
    
    # Count materials by type
    result = await session.execute(
        text("""
            SELECT material_type, COUNT(*) 
            FROM materials 
            WHERE tenant_id = :tenant_id AND is_deleted = false AND code LIKE 'RM-TEST-%' OR code LIKE 'SF-TEST-%'
            GROUP BY material_type
            ORDER BY material_type
        """),
        {"tenant_id": tenant_id}
    )
    print("\n📦 Test Materials Created:")
    for row in result:
        print(f"  • {row[0]}: {row[1]} items")
    
    # Templates
    result = await session.execute(
        text("""
            SELECT COUNT(*) 
            FROM item_templates 
            WHERE tenant_id = :tenant_id AND is_deleted = false AND code LIKE '%TEST%'
        """),
        {"tenant_id": tenant_id}
    )
    template_count = result.scalar()
    print(f"\n📋 Test Product Templates: {template_count}")
    
    # BOMs
    result = await session.execute(
        text("""
            SELECT t.code, t.name, b.version, COUNT(bl.id) as line_count,
                   CASE 
                       WHEN bl.material_id IS NOT NULL THEN 'Material'
                       WHEN bl.template_id IS NOT NULL THEN 'Template'
                   END as component_type
            FROM bill_of_materials b
            JOIN item_templates t ON b.template_id = t.id
            LEFT JOIN bom_lines bl ON bl.bom_id = b.id
            WHERE b.tenant_id = :tenant_id AND b.is_deleted = false AND t.code LIKE '%TEST%'
            GROUP BY t.code, t.name, b.version, component_type
            ORDER BY t.code, b.version
        """),
        {"tenant_id": tenant_id}
    )
    print(f"\n📝 Test BOMs:")
    for row in result:
        comp_type = row[4] or "Mixed"
        print(f"  • {row[0]} - {row[2]}: {row[3]} lines ({comp_type})")
    
    print("\n" + "="*70)
    print("✅ TEST DATA READY!")
    print("="*70)
    print("\n🧪 TESTING GUIDE:")
    print("="*70)
    print("\n1. Navigate to: Products > Product Templates")
    print("\n2. Find 'FG-TEST-ROTAMETER' template")
    print("\n3. View BOMs tab - you should see 2 versions:")
    print("   ⭐ v1.0-material (ACTIVE)")
    print("      • Uses SF-TEST-ASSY as MATERIAL component")
    print("      • THIS TESTS YOUR NEW FEATURE!")
    print("      • Click to view - should show semi-finished material in BOM")
    print("\n   ℹ v1.0-template (INACTIVE)")  
    print("      • Uses TPL-TEST-ASSY as TEMPLATE component")
    print("      • Traditional approach that always worked")
    print("\n4. View 'TPL-TEST-ASSY' template:")
    print("   • Go to BOMs tab")
    print("   • Should show v1.0 with 10 raw materials")
    print("\n5. 🎯 KEY TEST - Try adding a new component:")
    print("   • Edit the v1.0-material BOM")
    print("   • Click 'Add Component'")
    print("   • Select Component Type: Material")
    print("   • In dropdown, search for 'SF-TEST'")
    print("   • ✅ SF-TEST-ASSY should appear in the list!")
    print("   • ✅ You should be able to add it without errors!")
    print("\n6. Verify semi-finished appears alongside raw materials")
    print("\n7. Try to add a finished good - should be blocked!")
    print("\n" + "="*70 + "\n")


async def main():
    """Main execution."""
    print("="*70)
    print("🚀 SIMPLIFIED SEMI-FINISHED TEST DATA CREATOR")
    print("="*70)
    
    db_url = read_db_url()
    print(f"\n📡 Connecting to database...")
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Get tenant
            tenant_id = await get_tenant_id(session)
            print(f"  ✓ Using tenant: {tenant_id}")
            
            # Get or create unit
            unit_id = await get_or_create_unit(session, tenant_id, "PCS")
            
            # Create all data
            raw_material_ids = await create_raw_materials(session, tenant_id, unit_id)
            semi_finished_material_id = await create_semi_finished_material(session, tenant_id, unit_id)
            semi_template_id = await create_semi_finished_template(session, tenant_id)
            semi_bom_id = await create_semi_finished_bom(
                session, tenant_id, semi_template_id, raw_material_ids, unit_id
            )
            main_template_id = await create_main_product_template(session, tenant_id)
            main_bom_material_id = await create_main_product_bom_with_material(
                session, tenant_id, main_template_id, semi_finished_material_id, unit_id
            )
            main_bom_template_id = await create_main_product_bom_with_template(
                session, tenant_id, main_template_id, semi_template_id
            )
            
            # Commit all changes
            await session.commit()
            print("\n💾 All data committed to database")
            
            # Print summary
            await print_summary(session, tenant_id)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
