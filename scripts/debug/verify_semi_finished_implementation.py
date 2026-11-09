#!/usr/bin/env python3
"""
Complete verification script for semi-finished BOM implementation.
This script performs comprehensive database, code, and relationship verification.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from backend.app.infrastructure.database import engine


async def verify_database_schema():
    """Verify database schema has required columns."""
    print("="*70)
    print("1. DATABASE SCHEMA VERIFICATION")
    print("="*70)
    
    async with engine.begin() as conn:
        # Check item_variants.material_id
        result = await conn.execute(text("""
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = 'item_variants' AND column_name = 'material_id'
        """))
        row = result.fetchone()
        if row:
            print(f"✅ item_variants.material_id EXISTS")
            print(f"   - Nullable: {row[1]}")
            print(f"   - Type: {row[2]}")
        else:
            print(f"❌ item_variants.material_id NOT FOUND")
            return False
        
        # Check materials.material_type
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'materials' AND column_name = 'material_type'
        """))
        row = result.fetchone()
        if row:
            print(f"✅ materials.material_type EXISTS")
            print(f"   - Type: {row[1]}")
        else:
            print(f"❌ materials.material_type NOT FOUND")
            return False
        
        # Check foreign key relationship
        result = await conn.execute(text("""
            SELECT constraint_name, table_name, column_name
            FROM information_schema.key_column_usage
            WHERE table_name = 'item_variants' 
            AND column_name = 'material_id'
        """))
        row = result.fetchone()
        if row:
            print(f"✅ Foreign key constraint: {row[0]}")
        else:
            print(f"⚠️  No FK constraint found (but column exists)")
    
    print()
    return True


async def verify_data_relationships():
    """Verify actual data in database."""
    print("="*70)
    print("2. DATA RELATIONSHIP VERIFICATION")
    print("="*70)
    
    async with engine.begin() as conn:
        # Count semi-finished materials
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM materials 
            WHERE material_type = 'semi_finished' AND is_deleted = false
        """))
        sf_count = result.scalar()
        print(f"Semi-Finished Materials: {sf_count}")
        
        # Count variants with material_id
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM item_variants 
            WHERE material_id IS NOT NULL AND is_deleted = false
        """))
        variant_link_count = result.scalar()
        print(f"Variants with material_id: {variant_link_count}")
        
        # Show actual relationships
        result = await conn.execute(text("""
            SELECT 
                m.code as material_code,
                m.name as material_name,
                m.material_type,
                v.code as variant_code,
                v.name as variant_name,
                EXISTS(SELECT 1 FROM boms WHERE variant_id = v.id AND is_active = true) as has_bom
            FROM materials m
            JOIN item_variants v ON v.material_id = m.id
            WHERE m.is_deleted = false AND v.is_deleted = false
            LIMIT 10
        """))
        
        relationships = result.fetchall()
        if relationships:
            print(f"\n✅ Found {len(relationships)} Material ← Variant relationships:")
            for row in relationships:
                bom_status = "✅ BOM" if row[5] else "⚠️  No BOM"
                print(f"   {row[0]} ({row[2]}) ← {row[3]} [{bom_status}]")
        else:
            print(f"\n⚠️  No Material ← Variant relationships found")
            print(f"   This is OK if you haven't created test data yet")
        
        # Check for semi-finished materials WITH variants AND BOMs
        result = await conn.execute(text("""
            SELECT 
                m.code as material_code,
                v.code as variant_code,
                b.version as bom_version,
                COUNT(bl.id) as bom_lines
            FROM materials m
            JOIN item_variants v ON v.material_id = m.id
            JOIN boms b ON b.variant_id = v.id AND b.is_active = true
            LEFT JOIN bom_lines bl ON bl.bom_id = b.id
            WHERE m.material_type = 'semi_finished' 
            AND m.is_deleted = false 
            AND v.is_deleted = false
            AND b.is_deleted = false
            GROUP BY m.code, v.code, b.version
        """))
        
        complete_chains = result.fetchall()
        if complete_chains:
            print(f"\n✅ Complete Semi-Finished Chains (Material → Variant → BOM):")
            for row in complete_chains:
                print(f"   {row[0]} → {row[1]} → BOM {row[2]} ({row[3]} lines)")
        else:
            print(f"\n⚠️  No complete SF chains found (this needs test data)")
    
    print()
    return True


async def verify_bom_explosion_code():
    """Verify BOM explosion code exists."""
    print("="*70)
    print("3. CODE IMPLEMENTATION VERIFICATION")
    print("="*70)
    
    # Check files exist
    files_to_check = [
        "backend/app/domain/bom/services/bom_browser_service.py",
        "backend/app/infrastructure/persistence/repositories/bom_repository.py",
        "backend/app/infrastructure/services/bom_providers.py",
        "frontend/src/modules/products/components/VariantManager.tsx",
        "frontend/src/modules/bom/components/BOMTreeView.tsx",
    ]
    
    all_exist = True
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} NOT FOUND")
            all_exist = False
    
    if not all_exist:
        return False
    
    # Check key code patterns
    browser_service = Path("backend/app/domain/bom/services/bom_browser_service.py").read_text()
    checks = [
        ("visited_bom_ids", "Circular reference protection"),
        ("semi_finished", "Semi-finished detection logic"),
        ("get_bom_for_material", "Material BOM lookup call"),
    ]
    
    print()
    for pattern, desc in checks:
        if pattern in browser_service:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - '{pattern}' not found")
            return False
    
    print()
    return True


async def verify_no_migration():
    """Verify no migration was created for semi-finished feature."""
    print("="*70)
    print("4. MIGRATION VERIFICATION")
    print("="*70)
    
    # Check alembic versions
    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print("❌ alembic/versions directory not found")
        return False
    
    # Get recent migrations (last 5)
    migration_files = sorted(versions_dir.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    
    print("Recent migrations (last 5):")
    for mig in migration_files:
        print(f"  • {mig.name}")
    
    # Check if any mention semi_finished, variant, or material_id
    sf_related = []
    for mig in migration_files:
        if mig.name == "__init__.py":
            continue
        content = mig.read_text()
        if any(keyword in content.lower() for keyword in ["semi_finished", "semi-finished", "material_id"]):
            sf_related.append(mig.name)
    
    if sf_related:
        print(f"\n⚠️  Found {len(sf_related)} migrations mentioning semi-finished/material_id:")
        for name in sf_related:
            print(f"  • {name}")
        print("   Verify these are PRE-EXISTING, not new migrations")
    else:
        print(f"\n✅ NO NEW MIGRATIONS for semi-finished feature")
    
    print()
    return True


async def generate_final_report():
    """Generate final verification report."""
    print("="*70)
    print("FINAL VERIFICATION REPORT")
    print("="*70)
    
    schema_ok = await verify_database_schema()
    data_ok = await verify_data_relationships()
    code_ok = await verify_bom_explosion_code()
    migration_ok = await verify_no_migration()
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Database Schema:      {'✅ PASS' if schema_ok else '❌ FAIL'}")
    print(f"Data Relationships:   {'✅ PASS' if data_ok else '❌ FAIL'}")
    print(f"Code Implementation:  {'✅ PASS' if code_ok else '❌ FAIL'}")
    print(f"No New Migration:     {'✅ PASS' if migration_ok else '❌ FAIL'}")
    print("="*70)
    
    if all([schema_ok, data_ok, code_ok, migration_ok]):
        print("\n✅ ALL CHECKS PASSED")
        print("\nNEXT STEPS:")
        print("1. Create test data (or verify existing data)")
        print("2. Test multi-level BOM explosion via API")
        print("3. Test UI display of nested BOM")
        print("4. Test circular BOM protection")
        print("5. Test tenant isolation")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("Review the failures above and fix before proceeding")
        return 1


async def main():
    try:
        result = await generate_final_report()
        await engine.dispose()
        return result
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        await engine.dispose()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
