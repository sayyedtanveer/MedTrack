"""
Validation script for semi-finished material BOM explosion.

This script creates test data to validate the multi-level BOM explosion feature:
- Creates 10 raw materials (RM-001 to RM-010)
- Creates 1 semi-finished material (SF-MECH-ASSY)
- Creates 1 finished good template (TPL-ROTAMETER)
- Creates 1 finished good variant (FG-ROTAMETER)
- Creates BOM for semi-finished: SF-MECH-ASSY → RM-001...RM-010
- Creates BOM for finished good: FG-ROTAMETER → SF-MECH-ASSY
- Validates the explosion works correctly

Expected hierarchy after explosion:
FG-ROTAMETER
  └─ SF-MECH-ASSY (qty: 1)
      ├─ RM-001 (qty: 1)
      ├─ RM-002 (qty: 2)
      ├─ RM-003 (qty: 3)
      ...
      └─ RM-010 (qty: 10)
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


async def create_test_data(session: AsyncSession, tenant_id: uuid.UUID):
    """Create test data for BOM explosion validation."""
    
    print("=" * 80)
    print("CREATING TEST DATA FOR SEMI-FINISHED BOM EXPLOSION")
    print("=" * 80)
    
    # Initialize repositories
    material_repo = MaterialRepository(session)
    template_repo = ItemTemplateRepository(session)
    variant_repo = ItemVariantRepository(session)
    bom_repo = BOMRepository(session)
    
    # Get or create a unit of measure (assuming 'pcs' or 'kg' exists)
    # For simplicity, we'll use a hardcoded UUID - in real scenario, query from DB
    unit_id = uuid.uuid4()
    
    # Step 1: Create 10 raw materials
    print("\n[1/7] Creating 10 raw materials (RM-001 to RM-010)...")
    raw_material_ids = []
    for i in range(1, 11):
        material = Material(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code=f"RM-{i:03d}",
            name=f"Raw Material {i:03d}",
            material_type="raw_material",
            description=f"Test raw material {i}",
            base_unit_id=unit_id,
            current_cost=Decimal(str(i * 10)),  # RM-001: $10, RM-002: $20, etc.
            reorder_level=Decimal("100.0"),
            reorder_quantity=Decimal("500.0"),
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await material_repo.add(material)
        raw_material_ids.append(material.id)
        print(f"   ✓ Created {material.code}: {material.name} (${material.current_cost})")
    
    # Step 2: Create semi-finished material
    print("\n[2/7] Creating semi-finished material (SF-MECH-ASSY)...")
    sf_material = Material(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="SF-MECH-ASSY",
        name="Mechanical Assembly - Semi Finished",
        material_type="semi_finished",
        description="Semi-finished mechanical assembly",
        base_unit_id=unit_id,
        current_cost=Decimal("550.0"),  # Sum of raw materials
        reorder_level=Decimal("50.0"),
        reorder_quantity=Decimal("200.0"),
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await material_repo.add(sf_material)
    print(f"   ✓ Created {sf_material.code}: {sf_material.name} (${sf_material.current_cost})")
    
    # Step 3: Create finished good template
    print("\n[3/7] Creating finished good template (TPL-ROTAMETER)...")
    fg_template = ItemTemplate(
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
            {"key": "color", "label": "Color", "values": ["Red", "Blue"]},
            {"key": "size", "label": "Size", "values": ["Small", "Large"]}
        ],
        code_locked=False,
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await template_repo.add(fg_template)
    print(f"   ✓ Created {fg_template.code}: {fg_template.name}")
    
    # Step 4: Create variant for semi-finished material (this links SF material to BOM)
    print("\n[4/7] Creating variant for semi-finished material (VAR-SF-MECH)...")
    sf_variant = ItemVariant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=fg_template.id,  # Link to any template
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
    print(f"   ✓ Created {sf_variant.code}: {sf_variant.name}")
    print(f"      → Linked to material: {sf_material.code}")
    
    # Step 5: Create BOM for semi-finished material
    print("\n[5/7] Creating BOM for semi-finished material (SF-MECH-ASSY → 10 raw materials)...")
    sf_bom = BillOfMaterial(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=None,
        variant_id=sf_variant.id,  # ← BOM linked to variant
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
    
    # Add 10 raw material lines to SF BOM
    for i, rm_id in enumerate(raw_material_ids, start=1):
        line = BOMLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            bom_id=sf_bom.id,
            material_id=rm_id,
            template_id=None,
            variant_id=None,
            quantity=Decimal(str(i)),  # RM-001: 1, RM-002: 2, ..., RM-010: 10
            scrap_percentage=Decimal("0.0"),
            unit_id=unit_id
        )
        sf_bom.add_line(line)
        print(f"   ✓ Added RM-{i:03d} with quantity: {i}")
    
    await bom_repo.add(sf_bom)
    print(f"   ✓ Created BOM v{sf_bom.version} for {sf_variant.code}")
    
    # Step 6: Create finished good variant
    print("\n[6/7] Creating finished good variant (FG-ROTAMETER)...")
    fg_variant = ItemVariant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        template_id=fg_template.id,
        code="FG-ROTAMETER",
        name="Rotameter Finished Good - Red/Small",
        variant_key="red-small",
        attribute_values={"color": "Red", "size": "Small"},
        base_unit_id=unit_id,
        material_id=None,
        standard_cost=Decimal("600.0"),
        selling_price=Decimal("1000.0"),
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await variant_repo.add(fg_variant)
    print(f"   ✓ Created {fg_variant.code}: {fg_variant.name}")
    
    # Step 7: Create BOM for finished good
    print("\n[7/7] Creating BOM for finished good (FG-ROTAMETER → SF-MECH-ASSY)...")
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
        material_id=sf_material.id,  # ← Semi-finished material
        template_id=None,
        variant_id=None,
        quantity=Decimal("1.0"),
        scrap_percentage=Decimal("5.0"),  # 5% scrap
        unit_id=unit_id
    )
    fg_bom.add_line(fg_line)
    print(f"   ✓ Added {sf_material.code} with quantity: 1.0 (5% scrap)")
    
    await bom_repo.add(fg_bom)
    print(f"   ✓ Created BOM v{fg_bom.version} for {fg_variant.code}")
    
    # Commit transaction
    await session.commit()
    
    print("\n" + "=" * 80)
    print("TEST DATA CREATED SUCCESSFULLY!")
    print("=" * 80)
    
    return {
        "tenant_id": tenant_id,
        "raw_materials": raw_material_ids,
        "sf_material": sf_material.id,
        "sf_material_code": sf_material.code,
        "sf_variant": sf_variant.id,
        "sf_bom": sf_bom.id,
        "fg_template": fg_template.id,
        "fg_variant": fg_variant.id,
        "fg_variant_code": fg_variant.code,
        "fg_bom": fg_bom.id
    }


async def validate_explosion(session: AsyncSession, test_data: dict):
    """Validate that the BOM explosion works correctly."""
    
    print("\n" + "=" * 80)
    print("VALIDATING BOM EXPLOSION")
    print("=" * 80)
    
    # Initialize repositories and services
    bom_repo = BOMRepository(session)
    from backend.app.infrastructure.services.bom_providers import (
        InfrastructureBOMProvider,
        InfrastructureComponentDetailProvider
    )
    from backend.app.domain.bom.services.bom_browser_service import BOMBrowserService
    
    # Get FG BOM
    fg_bom = await bom_repo.get_by_id(test_data["fg_bom"], test_data["tenant_id"])
    if not fg_bom:
        print("   ✗ FAILED: Could not retrieve FG BOM")
        return False
    
    print(f"\n[1/3] Retrieved FG BOM: {test_data['fg_variant_code']} v{fg_bom.version}")
    print(f"   └─ BOM has {len(fg_bom.lines)} line(s)")
    
    # Build providers
    bom_provider = InfrastructureBOMProvider(bom_repo)
    details_provider = InfrastructureComponentDetailProvider(session)
    
    # Build tree
    print("\n[2/3] Building BOM tree with explosion...")
    browser_service = BOMBrowserService(bom_provider, details_provider)
    tree = await browser_service.build_tree(test_data["tenant_id"], fg_bom, max_depth=20)
    
    print(f"   ✓ Tree built successfully")
    print(f"   └─ Root has {len(tree.get('children', []))} child(ren)")
    
    # Validate structure
    print("\n[3/3] Validating tree structure...")
    
    if len(tree["children"]) != 1:
        print(f"   ✗ FAILED: Expected 1 child (SF material), got {len(tree['children'])}")
        return False
    
    sf_node = tree["children"][0]
    print(f"   ✓ Found SF node: {sf_node['name']} ({sf_node['code']})")
    print(f"      - Type: {sf_node['type']}")
    print(f"      - Material Type: {sf_node.get('material_type', 'N/A')}")
    print(f"      - Quantity: {sf_node['quantity']}")
    print(f"      - Children: {len(sf_node.get('children', []))}")
    
    if sf_node.get("material_type") != "semi_finished":
        print(f"   ✗ FAILED: Expected material_type='semi_finished', got '{sf_node.get('material_type')}'")
        return False
    
    if len(sf_node.get("children", [])) != 10:
        print(f"   ✗ FAILED: Expected 10 children (raw materials), got {len(sf_node.get('children', []))}")
        return False
    
    print(f"   ✓ SF node has correct material_type and 10 children")
    
    # Validate raw material quantities
    print("\n   Validating raw material quantities (with 5% scrap rollup)...")
    expected_multiplier = 1.05  # 1.0 qty * (1 + 5%/100)
    all_correct = True
    
    for i, rm_node in enumerate(sf_node["children"], start=1):
        expected_qty = i * expected_multiplier
        actual_qty = rm_node["quantity"]
        
        if abs(actual_qty - expected_qty) < 0.001:  # Float comparison tolerance
            print(f"      ✓ {rm_node['code']}: {actual_qty:.2f} (expected: {expected_qty:.2f})")
        else:
            print(f"      ✗ {rm_node['code']}: {actual_qty:.2f} (expected: {expected_qty:.2f}) - MISMATCH!")
            all_correct = False
    
    if not all_correct:
        print("\n   ✗ VALIDATION FAILED: Quantity mismatches detected")
        return False
    
    print("\n" + "=" * 80)
    print("✓ VALIDATION PASSED!")
    print("=" * 80)
    print("\nExpected hierarchy verified:")
    print("FG-ROTAMETER")
    print("  └─ SF-MECH-ASSY (qty: 1.05 with 5% scrap)")
    print("      ├─ RM-001 (qty: 1.05)")
    print("      ├─ RM-002 (qty: 2.10)")
    print("      ├─ RM-003 (qty: 3.15)")
    print("      ...")
    print("      └─ RM-010 (qty: 10.50)")
    print("\n" + "=" * 80)
    
    return True


async def main():
    """Main execution function."""
    
    # Use a test tenant ID - in production, this would come from authentication
    # You may need to adjust this to match an existing tenant in your database
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    print("\n" + "=" * 80)
    print("SEMI-FINISHED MATERIAL BOM EXPLOSION VALIDATION")
    print("=" * 80)
    print(f"\nTenant ID: {tenant_id}")
    print("\nThis script will:")
    print("  1. Create test data (10 raw materials, 1 SF material, 1 FG variant)")
    print("  2. Create hierarchical BOMs (FG → SF → 10 RMs)")
    print("  3. Validate that BOM explosion works correctly")
    print("\n" + "=" * 80)
    
    try:
        async with async_session_maker() as session:
            # Create test data
            test_data = await create_test_data(session, tenant_id)
            
            # Validate explosion
            success = await validate_explosion(session, test_data)
            
            if success:
                print("\n✓ All validations passed!")
                print("\nTo view in UI:")
                print(f"  1. Navigate to Products → Variants")
                print(f"  2. Find variant: {test_data['fg_variant_code']}")
                print(f"  3. Open BOM tab")
                print(f"  4. Click 'View Tree' to see multi-level explosion")
                print(f"  5. Verify SF-MECH-ASSY shows purple 'Semi-Finished' badge")
                print(f"  6. Verify SF-MECH-ASSY expands to show 10 raw materials")
                return 0
            else:
                print("\n✗ Validation failed!")
                return 1
                
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
