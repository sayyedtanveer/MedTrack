"""
Quick Setup Script for Semi-Finished BOM
Creates all test data automatically in one go!

Usage:
    python scripts/quick_setup_semi_finished_bom.py

What it creates:
    - 10 raw materials (RM-001 to RM-010)
    - 1 semi-finished material (SF-MECH-ASSY)
    - 1 product template (TPL-ROTAMETER)
    - 2 variants (VAR-SF-MECH with material link, FG-ROTAMETER)
    - 2 BOMs (SF BOM with 10 raw materials, FG BOM with SF material)

Result:
    FG-ROTAMETER → SF-MECH-ASSY → RM-001...RM-010 (automatic explosion)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.infrastructure.database import async_session_maker
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.item_template_repository import ItemTemplateRepository
from backend.app.infrastructure.persistence.repositories.item_variant_repository import ItemVariantRepository
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.domain.material.entities.material import Material
from backend.app.domain.item_template.entities.item_template import ItemTemplate
from backend.app.domain.item_variant.entities.item_variant import ItemVariant
from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine
import uuid
from decimal import Decimal
from datetime import datetime


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(step, text):
    """Print formatted step."""
    print(f"\n[{step}] {text}")


def print_success(text):
    """Print success message."""
    print(f"   ✓ {text}")


def print_info(text):
    """Print info message."""
    print(f"      → {text}")


async def quick_setup(session: AsyncSession, tenant_id: uuid.UUID):
    """Create all test data in one go."""
    
    print_header("QUICK SETUP: SEMI-FINISHED BOM")
    print(f"\nTenant ID: {tenant_id}")
    print("\nCreating complete test data for multi-level BOM explosion...")
    
    # Initialize repositories
    material_repo = MaterialRepository(session)
    template_repo = ItemTemplateRepository(session)
    variant_repo = ItemVariantRepository(session)
    bom_repo = BOMRepository(session)
    
    # Use hardcoded unit UUID (in real app, query from database)
    unit_id = uuid.uuid4()
    
    # ==================================================================
    # STEP 1: Create 10 Raw Materials
    # ==================================================================
    print_step("1/7", "Creating 10 raw materials...")
    
    raw_materials = []
    for i in range(1, 11):
        material = Material(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code=f"RM-{i:03d}",
            name=f"Raw Material {i:03d}",
            material_type="raw_material",
            description=f"Test raw material {i} for BOM explosion demo",
            base_unit_id=unit_id,
            current_cost=Decimal(str(i * 10)),
            reorder_level=Decimal("100.0"),
            reorder_quantity=Decimal("500.0"),
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await material_repo.add(material)
        raw_materials.append(material)
        print_success(f"{material.code}: {material.name} (${material.current_cost})")
    
    # ==================================================================
    # STEP 2: Create Semi-Finished Material
    # ==================================================================
    print_step("2/7", "Creating semi-finished material...")
    
    sf_material = Material(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="SF-MECH-ASSY",
        name="Mechanical Assembly - Semi Finished",
        material_type="semi_finished",  # ← KEY: This enables BOM explosion
        description="Semi-finished mechanical assembly for rotameter",
        base_unit_id=unit_id,
        current_cost=Decimal("550.0"),
        reorder_level=Decimal("50.0"),
        reorder_quantity=Decimal("200.0"),
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await material_repo.add(sf_material)
    print_success(f"{sf_material.code}: {sf_material.name}")
    print_info(f"Type: {sf_material.material_type} (enables explosion)")
    
    # ==================================================================
    # STEP 3: Create Product Template
    # ==================================================================
    print_step("3/7", "Creating product template...")
    
    template = ItemTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="TPL-ROTAMETER",
        item_code="FG",
        item_type="FG",
        name="Rotameter Product Template",
        description="Template for rotameter finished goods",
        category_id=None,
        base_unit_id=unit_id,
        attributes=[
            {"key": "color", "label": "Color", "values": ["Red", "Blue", "Green"]},
            {"key": "size", "label": "Size", "values": ["Small", "Medium", "Large"]}
        ],
        code_locked=False,
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await template_repo.add(template)
    print_success(f"{template.code}: {template.name}")
    
    # ==================================================================
    # STEP 4: Create Variant for Semi-Finished (THE KEY LINK!)
    # ==================================================================
    print_step("4/7", "Creating variant for semi-finished material...")
    
    sf_variant = ItemVariant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=template.id,
        code="VAR-SF-MECH",
        name="SF Mechanical Assembly Variant",
        variant_key="sf-mech",
        attribute_values={},
        base_unit_id=unit_id,
        material_id=sf_material.id,  # ← KEY LINK: Variant → Material
        standard_cost=Decimal("550.0"),
        selling_price=Decimal("750.0"),
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await variant_repo.add(sf_variant)
    print_success(f"{sf_variant.code}: {sf_variant.name}")
    print_info(f"Linked to material: {sf_material.code}")
    print_info("This link enables automatic BOM explosion!")
    
    # ==================================================================
    # STEP 5: Create BOM for Semi-Finished Material
    # ==================================================================
    print_step("5/7", "Creating BOM for semi-finished material...")
    
    sf_bom = BillOfMaterial(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=None,
        variant_id=sf_variant.id,  # ← BOM belongs to variant
        version="1.0.0",
        is_active=True,
        valid_from=None,
        valid_to=None,
        created_by=None,
        approved_by=None,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        operations_count=0,
        lines=[],
        operations=[]
    )
    
    # Add 10 raw material lines
    for i, rm in enumerate(raw_materials, start=1):
        line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=sf_bom.id,
            material_id=rm.id,
            template_id=None,
            variant_id=None,
            quantity=Decimal(str(i)),  # Progressive quantities
            scrap_percentage=Decimal("0.0"),
            unit_id=unit_id
        )
        sf_bom.add_line(line)
    
    await bom_repo.add(sf_bom)
    print_success(f"BOM v{sf_bom.version} created for {sf_variant.code}")
    print_info("Contains 10 raw material lines:")
    for i, rm in enumerate(raw_materials, start=1):
        print(f"         - {rm.code}: qty={i}")
    
    # ==================================================================
    # STEP 6: Create Finished Good Variant
    # ==================================================================
    print_step("6/7", "Creating finished good variant...")
    
    fg_variant = ItemVariant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=template.id,
        code="FG-ROTAMETER",
        name="Rotameter - Red/Small",
        variant_key="red-small",
        attribute_values={"color": "Red", "size": "Small"},
        base_unit_id=unit_id,
        material_id=None,  # FG variants typically don't link to materials
        standard_cost=Decimal("600.0"),
        selling_price=Decimal("1000.0"),
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await variant_repo.add(fg_variant)
    print_success(f"{fg_variant.code}: {fg_variant.name}")
    
    # ==================================================================
    # STEP 7: Create BOM for Finished Good
    # ==================================================================
    print_step("7/7", "Creating BOM for finished good...")
    
    fg_bom = BillOfMaterial(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=None,
        variant_id=fg_variant.id,
        version="1.0.0",
        is_active=True,
        valid_from=None,
        valid_to=None,
        created_by=None,
        approved_by=None,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        operations_count=0,
        lines=[],
        operations=[]
    )
    
    # Add semi-finished material to FG BOM
    fg_line = BOMLine(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        bom_id=fg_bom.id,
        material_id=sf_material.id,  # ← Uses semi-finished material
        template_id=None,
        variant_id=None,
        quantity=Decimal("1.0"),
        scrap_percentage=Decimal("5.0"),  # 5% scrap for testing
        unit_id=unit_id
    )
    fg_bom.add_line(fg_line)
    
    await bom_repo.add(fg_bom)
    print_success(f"BOM v{fg_bom.version} created for {fg_variant.code}")
    print_info(f"Contains 1 line: {sf_material.code} (qty=1.0, scrap=5%)")
    
    # Commit all changes
    await session.commit()
    
    # ==================================================================
    # SUCCESS SUMMARY
    # ==================================================================
    print_header("✓ SETUP COMPLETE!")
    
    print("\n📊 Summary:")
    print(f"   • 10 Raw Materials: RM-001 to RM-010")
    print(f"   • 1 Semi-Finished: {sf_material.code}")
    print(f"   • 1 Template: {template.code}")
    print(f"   • 2 Variants: {sf_variant.code}, {fg_variant.code}")
    print(f"   • 2 BOMs: {sf_bom.version} (SF), {fg_bom.version} (FG)")
    
    print("\n🎯 Expected Hierarchy:")
    print(f"   {fg_variant.code}")
    print(f"     └─ {sf_material.code} (qty: 1.05 with 5% scrap) 🟣")
    print("         ├─ RM-001 (qty: 1.05)")
    print("         ├─ RM-002 (qty: 2.10)")
    print("         ├─ RM-003 (qty: 3.15)")
    print("         ├─ RM-004 (qty: 4.20)")
    print("         ├─ RM-005 (qty: 5.25)")
    print("         ├─ RM-006 (qty: 6.30)")
    print("         ├─ RM-007 (qty: 7.35)")
    print("         ├─ RM-008 (qty: 8.40)")
    print("         ├─ RM-009 (qty: 9.45)")
    print("         └─ RM-010 (qty: 10.50)")
    
    print("\n🚀 Next Steps:")
    print("   1. Login to MedTrack ERP")
    print(f"   2. Navigate to: Products → Variants")
    print(f"   3. Find variant: {fg_variant.code}")
    print("   4. Go to BOM tab")
    print("   5. Click 'View Tree' button")
    print("   6. Expand SF-MECH-ASSY to see all 10 raw materials!")
    
    print("\n📝 Database IDs (for API testing):")
    print(f"   Tenant ID:    {tenant_id}")
    print(f"   SF Material:  {sf_material.id}")
    print(f"   SF Variant:   {sf_variant.id}")
    print(f"   SF BOM:       {sf_bom.id}")
    print(f"   FG Variant:   {fg_variant.id}")
    print(f"   FG BOM:       {fg_bom.id}")
    
    print("\n" + "=" * 80)
    
    return {
        "tenant_id": str(tenant_id),
        "raw_materials": [str(rm.id) for rm in raw_materials],
        "sf_material_id": str(sf_material.id),
        "sf_material_code": sf_material.code,
        "sf_variant_id": str(sf_variant.id),
        "sf_bom_id": str(sf_bom.id),
        "fg_variant_id": str(fg_variant.id),
        "fg_variant_code": fg_variant.code,
        "fg_bom_id": str(fg_bom.id),
    }


async def main():
    """Main execution."""
    
    # IMPORTANT: Replace with your actual tenant ID
    # You can find this by logging in and checking the user's tenant_id
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    print("\n" + "=" * 80)
    print("  QUICK SETUP: SEMI-FINISHED BOM")
    print("=" * 80)
    print("\n⚠️  WARNING: This will create test data in your database!")
    print(f"\nTenant ID: {tenant_id}")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("\n❌ Setup cancelled.")
        return 1
    
    try:
        async with async_session_maker() as session:
            result = await quick_setup(session, tenant_id)
            
            # Save IDs to file for later reference
            import json
            output_file = Path(__file__).parent.parent / "test_data_ids.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\n💾 IDs saved to: {output_file}")
            print("\n✅ Setup completed successfully!")
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
