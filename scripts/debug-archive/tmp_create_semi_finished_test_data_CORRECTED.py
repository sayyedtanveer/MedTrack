#!/usr/bin/env python3
"""
CORRECTED: Create test data for semi-finished material BOM testing.

This script creates:
1. 10 Raw Materials (RM-001 to RM-010)
2. 1 Semi-Finished Material (SF-MECH-ASSY)
3. 1 Semi-Finished Product Template (TPL-MECH-ASSY)
4. 1 Semi-Finished Variant (links template → material via material_id)
5. BOM for Semi-Finished Variant (uses 10 raw materials)
6. 1 Main Product Template (FG-ROTAMETER)
7. 1 Main Product Variant
8. BOM for Main Product (uses semi-finished MATERIAL as component)

CORRECTED SCHEMA:
- Uses item_variants (not product_variants)
- Sets material_id directly in item_variants (no variant_outputs table)
- Uses boms table (not bill_of_materials)
- No line_number column in bom_lines
- valid_from is DateTime not text
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


async def get_tenant_and_user(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Get the first active tenant ID and a user ID."""
    result = await session.execute(
        text("SELECT id FROM tenants WHERE is_deleted = false LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        raise RuntimeError("No active tenant found. Please create a tenant first.")
    tenant_id = row[0]
    
    result = await session.execute(
        text("SELECT id FROM users WHERE tenant_id = :tenant_id LIMIT 1"),
        {"tenant_id": tenant_id}
    )
    row = result.fetchone()
    if not row:
        raise RuntimeError(f"No users found for tenant {tenant_id}")
    user_id = row[0]
    
    return tenant_id, user_id


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


async def create_raw_materials(session: AsyncSession, tenant_id: uuid.UUID, unit_id: uuid.UUID, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Create 10 raw materials."""
    print("\n📦 Creating 10 Raw Materials...")
    
    raw_materials = [
        ("RM-001", "Steel Shaft", Decimal("10.50")),
        ("RM-002", "Bearing", Decimal("25.00")),
        ("RM-003", "Gear Wheel", Decimal("45.75")),
        ("RM-004", "Spring", Decimal("5.25")),
        ("RM-005", "Bolt M6", Decimal("0.50")),
        ("RM-006", "Washer", Decimal("0.25")),
        ("RM-007", "Gasket", Decimal("3.50")),
        ("RM-008", "O-Ring", Decimal("2.00")),
        ("RM-009", "Housing Body", Decimal("85.00")),
        ("RM-010", "Cover Plate", Decimal("15.00")),
    ]
    
    material_ids = []
    now = datetime.now(timezone.utc)
    
    for code, name, cost in raw_materials:
        material_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO materials 
                (id, tenant_id, code, name, material_type, base_unit_id,
                 current_cost, current_stock, reserved_stock, 
                 is_batch_tracked, is_serialized, inspection_required, 
                 hazardous_flag, qc_required_flag, traceability_enabled,
                 expiry_tracking, quarantine_required, cuttable_inventory,
                 remaining_quantity_tracking, reusable_remainder,
                 is_active, is_deleted, created_by, updated_by,
                 created_at, updated_at)
                VALUES 
                (:id, :tenant_id, :code, :name, 'raw', :unit_id,
                 :cost, 0, 0,
                 false, false, false,
                 false, false, false,
                 false, false, false,
                 false, false,
                 true, false, :user_id, :user_id,
                 :now, :now)
            """),
            {
                "id": material_id,
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "unit_id": unit_id,
                "cost": cost,
                "user_id": user_id,
                "now": now
            }
        )
        material_ids.append(material_id)
        print(f"  ✓ {code}: {name} (Cost: ${cost})")
    
    return material_ids


async def create_semi_finished_material(session: AsyncSession, tenant_id: uuid.UUID, unit_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID:
    """Create semi-finished material."""
    print("\n🔧 Creating Semi-Finished Material...")
    
    material_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO materials 
            (id, tenant_id, code, name, material_type, base_unit_id,
             current_cost, current_stock, reserved_stock,
             is_batch_tracked, is_serialized, inspection_required,
             hazardous_flag, qc_required_flag, traceability_enabled,
             expiry_tracking, quarantine_required, cuttable_inventory,
             remaining_quantity_tracking, reusable_remainder,
             is_active, is_deleted, created_by, updated_by,
             created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :name, 'semi_finished', :unit_id,
             0, 0, 0,
             false, false, false,
             false, false, false,
             false, false, false,
             false, false,
             true, false, :user_id, :user_id,
             :now, :now)
        """),
        {
            "id": material_id,
            "tenant_id": tenant_id,
            "code": "SF-MECH-ASSY",
            "name": "Mechanical Sub-Assembly",
            "unit_id": unit_id,
            "user_id": user_id,
            "now": now
        }
    )
    print(f"  ✓ SF-MECH-ASSY: Mechanical Sub-Assembly (Type: semi_finished)")
    
    return material_id


async def create_semi_finished_template(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create product template for semi-finished item."""
    print("\n📋 Creating Semi-Finished Product Template...")
    
    template_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO item_templates 
            (id, tenant_id, code, item_code, name, item_type, description,
             attributes, code_locked, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :item_code, :name, 'SF', :description,
             '[]'::jsonb, true, true, false, :now, :now)
        """),
        {
            "id": template_id,
            "tenant_id": tenant_id,
            "code": "TPL-MECH-ASSY",
            "item_code": "MECH-ASSY",
            "name": "Mechanical Sub-Assembly Template",
            "description": "Template for mechanical sub-assemblies",
            "now": now
        }
    )
    print(f"  ✓ TPL-MECH-ASSY: Mechanical Sub-Assembly Template")
    
    return template_id


async def create_semi_finished_variant(
    session: AsyncSession, 
    tenant_id: uuid.UUID, 
    template_id: uuid.UUID,
    material_id: uuid.UUID,  # ← Links variant to SF material
    unit_id: uuid.UUID
) -> uuid.UUID:
    """Create variant that PRODUCES the semi-finished material."""
    print("\n🔗 Creating Semi-Finished Variant (Template → Material Link)...")
    
    variant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # CORRECTED: Use item_variants table, set material_id directly
    await session.execute(
        text("""
            INSERT INTO item_variants 
            (id, tenant_id, template_id, code, name, variant_key,
             attribute_values, base_unit_id, material_id, standard_cost,
             is_active, is_deleted, code_locked, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :template_id, :code, :name, :variant_key,
             '{}'::jsonb, :unit_id, :material_id, :standard_cost,
             true, false, true, :now, :now)
        """),
        {
            "id": variant_id,
            "tenant_id": tenant_id,
            "template_id": template_id,
            "code": "MECH-ASSY-STD",
            "name": "Standard Mechanical Assembly",
            "variant_key": "STANDARD",
            "unit_id": unit_id,
            "material_id": material_id,  # ← CRITICAL: Direct link to SF material
            "standard_cost": Decimal("200.00"),
            "now": now
        }
    )
    
    print(f"  ✓ MECH-ASSY-STD variant created")
    print(f"  ✓ Variant.material_id → SF-MECH-ASSY (Direct FK link)")
    
    return variant_id


async def create_semi_finished_bom(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    variant_id: uuid.UUID,  # ← BOM for the SF variant
    raw_material_ids: list[uuid.UUID],
    unit_id: uuid.UUID,
    user_id: uuid.UUID
) -> uuid.UUID:
    """Create BOM for semi-finished VARIANT using 10 raw materials."""
    print("\n📝 Creating BOM for Semi-Finished Variant...")
    
    bom_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # CORRECTED: Use boms table, variant_id (not template_id), DateTime for valid_from
    await session.execute(
        text("""
            INSERT INTO boms 
            (id, tenant_id, variant_id, version, valid_from, 
             is_active, is_deleted, created_by, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :variant_id, :version, :valid_from,
             true, false, :user_id, :now, :now)
        """),
        {
            "id": bom_id,
            "tenant_id": tenant_id,
            "variant_id": variant_id,  # ← Linked to SF variant
            "version": "1.0",
            "valid_from": now,
            "user_id": user_id,
            "now": now
        }
    )
    
    # Create BOM lines for 10 raw materials
    quantities = [1, 2, 3, 1, 4, 4, 1, 2, 1, 1]  # Different quantities
    scrap_pcts = [0, 0, 0, 0, 5, 5, 0, 0, 0, 0]  # 5% scrap on bolts/washers
    
    for idx, (material_id, qty, scrap) in enumerate(zip(raw_material_ids, quantities, scrap_pcts)):
        line_id = uuid.uuid4()
        # CORRECTED: No line_number column, use tenant_id
        await session.execute(
            text("""
                INSERT INTO bom_lines 
                (id, tenant_id, bom_id, material_id, quantity, scrap_percentage, 
                 unit_id, is_deleted, created_at, updated_at)
                VALUES 
                (:id, :tenant_id, :bom_id, :material_id, :quantity, :scrap, 
                 :unit_id, false, :now, :now)
            """),
            {
                "id": line_id,
                "tenant_id": tenant_id,
                "bom_id": bom_id,
                "material_id": material_id,
                "quantity": Decimal(str(qty)),
                "scrap": Decimal(str(scrap)),
                "unit_id": unit_id,
                "now": now
            }
        )
    
    print(f"  ✓ BOM created for SF variant with 10 raw material lines")
    print(f"  ✓ Quantities: {quantities}")
    print(f"  ✓ Scrap %: {scrap_pcts}")
    
    return bom_id


async def create_main_product_template(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create main product template (FG Rotameter)."""
    print("\n🏭 Creating Main Product Template...")
    
    template_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO item_templates 
            (id, tenant_id, code, item_code, name, item_type, description,
             attributes, code_locked, is_active, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :code, :item_code, :name, 'FG', :description,
             '[]'::jsonb, true, true, false, :now, :now)
        """),
        {
            "id": template_id,
            "tenant_id": tenant_id,
            "code": "FG-ROTAMETER",
            "item_code": "ROTAMETER",
            "name": "Gear Rotameter",
            "description": "Complete rotameter assembly",
            "now": now
        }
    )
    print(f"  ✓ FG-ROTAMETER: Gear Rotameter")
    
    return template_id


async def create_main_product_variant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    unit_id: uuid.UUID
) -> uuid.UUID:
    """Create variant for main product."""
    print("\n🔧 Creating Main Product Variant...")
    
    variant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    await session.execute(
        text("""
            INSERT INTO item_variants 
            (id, tenant_id, template_id, code, name, variant_key,
             attribute_values, base_unit_id, standard_cost, selling_price,
             is_active, is_deleted, code_locked, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :template_id, :code, :name, :variant_key,
             '{}'::jsonb, :unit_id, :standard_cost, :selling_price,
             true, false, true, :now, :now)
        """),
        {
            "id": variant_id,
            "tenant_id": tenant_id,
            "template_id": template_id,
            "code": "ROTAMETER-STD",
            "name": "Standard Rotameter",
            "variant_key": "STANDARD",
            "unit_id": unit_id,
            "standard_cost": Decimal("500.00"),
            "selling_price": Decimal("750.00"),
            "now": now
        }
    )
    
    print(f"  ✓ ROTAMETER-STD variant created")
    
    return variant_id


async def create_main_product_bom(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    variant_id: uuid.UUID,  # Main product variant
    semi_finished_material_id: uuid.UUID,  # SF material as component
    unit_id: uuid.UUID,
    user_id: uuid.UUID
) -> uuid.UUID:
    """Create BOM for main product using semi-finished MATERIAL as component."""
    print("\n📝 Creating BOM for Main Product (using SF material)...")
    
    bom_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Create BOM for main product variant
    await session.execute(
        text("""
            INSERT INTO boms 
            (id, tenant_id, variant_id, version, valid_from,
             is_active, is_deleted, created_by, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :variant_id, :version, :valid_from,
             true, false, :user_id, :now, :now)
        """),
        {
            "id": bom_id,
            "tenant_id": tenant_id,
            "variant_id": variant_id,
            "version": "1.0",
            "valid_from": now,
            "user_id": user_id,
            "now": now
        }
    )
    
    # Create BOM line with semi-finished MATERIAL (this is the KEY test!)
    line_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO bom_lines 
            (id, tenant_id, bom_id, material_id, quantity, scrap_percentage,
             unit_id, is_deleted, created_at, updated_at)
            VALUES 
            (:id, :tenant_id, :bom_id, :material_id, :quantity, :scrap,
             :unit_id, false, :now, :now)
        """),
        {
            "id": line_id,
            "tenant_id": tenant_id,
            "bom_id": bom_id,
            "material_id": semi_finished_material_id,  # ← SF material as component!
            "quantity": Decimal("1"),
            "scrap": Decimal("5"),  # 5% scrap allowance
            "unit_id": unit_id,
            "now": now
        }
    )
    
    print(f"  ✓ BOM created with SF-MECH-ASSY as material component")
    print(f"  ✓ Quantity: 1, Scrap: 5%")
    print(f"  ✓ This tests the NEW multi-level BOM explosion!")
    
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
            WHERE tenant_id = :tenant_id AND is_deleted = false
            GROUP BY material_type
            ORDER BY material_type
        """),
        {"tenant_id": tenant_id}
    )
    print("\n📦 Materials:")
    for row in result:
        print(f"  • {row[0]}: {row[1]} items")
    
    # Show SF variant → material link
    result = await session.execute(
        text("""
            SELECT 
                v.code as variant_code,
                m.code as material_code,
                m.material_type,
                EXISTS(SELECT 1 FROM boms WHERE variant_id = v.id AND is_active = true) as has_bom
            FROM item_variants v
            JOIN materials m ON v.material_id = m.id
            WHERE v.tenant_id = :tenant_id AND v.is_deleted = false
        """),
        {"tenant_id": tenant_id}
    )
    print(f"\n🔗 Variant → Material Links:")
    for row in result:
        bom_status = "✅ Has BOM" if row[3] else "⚠️  No BOM"
        print(f"  • {row[0]} → {row[1]} ({row[2]}) [{bom_status}]")
    
    # Show BOM structure
    result = await session.execute(
        text("""
            SELECT 
                v.code as product_code,
                b.version,
                COUNT(bl.id) as line_count,
                STRING_AGG(DISTINCT 
                    CASE 
                        WHEN bl.material_id IS NOT NULL THEN 'material'
                        WHEN bl.template_id IS NOT NULL THEN 'template'
                        WHEN bl.variant_id IS NOT NULL THEN 'variant'
                    END, ', ') as component_types
            FROM boms b
            JOIN item_variants v ON b.variant_id = v.id
            LEFT JOIN bom_lines bl ON bl.bom_id = b.id
            WHERE b.tenant_id = :tenant_id AND b.is_deleted = false
            GROUP BY v.code, b.version
            ORDER BY v.code
        """),
        {"tenant_id": tenant_id}
    )
    print(f"\n📝 BOMs:")
    for row in result:
        print(f"  • {row[0]} v{row[1]}: {row[2]} lines ({row[3]})")
    
    print("\n" + "="*70)
    print("✅ TEST DATA READY!")
    print("="*70)
    print("\n🧪 NEXT STEPS TO VERIFY:")
    print("\n1. Check Material → Variant → BOM Chain:")
    print("   SF-MECH-ASSY (material)")
    print("     ↑ material_id")
    print("   MECH-ASSY-STD (variant)")
    print("     ↓ variant_id")
    print("   BOM v1.0 (10 raw material lines)")
    print()
    print("2. Check Multi-Level BOM:")
    print("   ROTAMETER-STD BOM")
    print("     └── SF-MECH-ASSY (material component)")
    print("           └── Should explode to show 10 raw materials")
    print()
    print("3. Test API:")
    print("   GET /api/v1/bom/{rotameter_bom_id}/tree?max_depth=20")
    print("   Expected: Nested tree showing SF → Raw materials")
    print()
    print("4. Test UI:")
    print("   Products → Variants → Add Variant")
    print("   - Verify: Advanced section collapsed by default")
    print("   - Expand Advanced → Select SF-MECH-ASSY")
    print("   - Create variant → Verify material_id saved")
    print()
    print("5. View BOM Tree:")
    print("   BOM → View ROTAMETER-STD BOM")
    print("   - Verify: Purple 'Semi-Finished' badge on SF-MECH-ASSY")
    print("   - Expand → Verify: 10 raw materials displayed")
    print("   - Verify: Quantities rolled up correctly")
    print("\n" + "="*70 + "\n")


async def main():
    """Main execution."""
    print("="*70)
    print("🚀 CORRECTED SEMI-FINISHED MATERIAL TEST DATA CREATOR")
    print("="*70)
    
    db_url = read_db_url()
    print(f"\n📡 Connecting to database...")
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Get tenant and user
            tenant_id, user_id = await get_tenant_and_user(session)
            print(f"  ✓ Using tenant: {tenant_id}")
            print(f"  ✓ Using user: {user_id}")
            
            # Get or create unit
            unit_id = await get_or_create_unit(session, tenant_id, "PCS")
            
            # Create all data
            raw_material_ids = await create_raw_materials(session, tenant_id, unit_id, user_id)
            semi_finished_material_id = await create_semi_finished_material(session, tenant_id, unit_id, user_id)
            semi_template_id = await create_semi_finished_template(session, tenant_id)
            semi_variant_id = await create_semi_finished_variant(
                session, tenant_id, semi_template_id, semi_finished_material_id, unit_id
            )
            semi_bom_id = await create_semi_finished_bom(
                session, tenant_id, semi_variant_id, raw_material_ids, unit_id, user_id
            )
            main_template_id = await create_main_product_template(session, tenant_id)
            main_variant_id = await create_main_product_variant(session, tenant_id, main_template_id, unit_id)
            main_bom_id = await create_main_product_bom(
                session, tenant_id, main_variant_id, semi_finished_material_id, unit_id, user_id
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
