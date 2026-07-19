"""
Data migration script to generate item_codes for existing materials and item_templates.

This script:
1. Creates a default "Uncategorized" category with code_prefix="GEN" if not exists
2. Generates item_codes for materials without item_code
3. Generates item_codes for item_templates without item_code
4. Sets code_locked=true for all generated codes
5. Preserves all existing relationships

Usage:
    python -m backend.db_scripts.migrate_item_codes [--dry-run]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.application.inventory.services.item_code_service import ItemCodeService


async def get_uncategorized_category(session: AsyncSession, tenant_id: str) -> MaterialCategoryModel:
    """Get or create the default Uncategorized category."""
    category = await session.scalar(
        select(MaterialCategoryModel).where(
            MaterialCategoryModel.name == "Uncategorized",
            MaterialCategoryModel.tenant_id == tenant_id,
            MaterialCategoryModel.is_deleted.is_(False),
        )
    )
    
    if category is None:
        category = MaterialCategoryModel(
            id=None,  # Will be set by DB
            tenant_id=tenant_id,
            name="Uncategorized",
            code_prefix="GEN",
            description="Default category for items without category assignment",
            is_active=True,
        )
        session.add(category)
        await session.flush()
        print(f"Created default 'Uncategorized' category with code_prefix='GEN' for tenant {tenant_id}")
    else:
        print(f"Using existing 'Uncategorized' category for tenant {tenant_id}")
    
    return category


async def migrate_materials(session: AsyncSession, tenant_id: str, dry_run: bool) -> int:
    """Generate item_codes for materials without item_code."""
    item_code_service = ItemCodeService(session)
    
    # Get materials without item_code
    materials = await session.execute(
        select(MaterialModel).where(
            MaterialModel.tenant_id == tenant_id,
            (MaterialModel.code.is_(None)) | (MaterialModel.code == ""),
            MaterialModel.is_deleted.is_(False),
        )
    )
    materials_list = materials.scalars().all()
    
    if not materials_list:
        print("No materials found without item_code")
        return 0
    
    print(f"Found {len(materials_list)} materials without item_code")
    
    # Get or create Uncategorized category
    category = await get_uncategorized_category(session, tenant_id)
    
    migrated_count = 0
    for material in materials_list:
        # Determine item type based on material_type
        item_type_map = {
            "raw": "RM",
            "RAW": "RM",
            "finished": "FG",
            "FINISHED": "FG",
            "semi_finished": "SF",
            "SEMI_FINISHED": "SF",
        }
        item_type = item_type_map.get(material.material_type, "RM")
        
        # Use existing category or default to Uncategorized
        category_id = material.category_id if material.category_id else category.id
        
        try:
            if not dry_run:
                new_code = await item_code_service.generate(
                    tenant_id=tenant_id,
                    item_type=item_type,
                    category_id=category_id,
                    target="material",
                )
                material.code = new_code
                material.code_locked = True
                print(f"  Generated item_code: {new_code} for material: {material.name}")
            else:
                print(f"  [DRY RUN] Would generate item_code for material: {material.name}")
            migrated_count += 1
        except Exception as e:
            print(f"  ERROR: Failed to generate code for material {material.name}: {e}")
            continue
    
    if not dry_run and migrated_count > 0:
        await session.flush()
    
    return migrated_count


async def migrate_item_templates(session: AsyncSession, tenant_id: str, dry_run: bool) -> int:
    """Generate item_codes for item_templates without item_code."""
    item_code_service = ItemCodeService(session)
    
    # Get item_templates without item_code
    templates = await session.execute(
        select(ItemTemplateModel).where(
            ItemTemplateModel.tenant_id == tenant_id,
            (ItemTemplateModel.code.is_(None)) | (ItemTemplateModel.code == ""),
            ItemTemplateModel.is_deleted.is_(False),
        )
    )
    templates_list = templates.scalars().all()
    
    if not templates_list:
        print("No item_templates found without item_code")
        return 0
    
    print(f"Found {len(templates_list)} item_templates without item_code")
    
    # Get or create Uncategorized category
    category = await get_uncategorized_category(session, tenant_id)
    
    migrated_count = 0
    for template in templates_list:
        # Use existing category or default to Uncategorized
        category_id = template.category_id if template.category_id else category.id
        
        try:
            if not dry_run:
                new_code = await item_code_service.generate(
                    tenant_id=tenant_id,
                    item_type="FG",  # Item templates are finished goods
                    category_id=category_id,
                    target="item_template",
                )
                template.code = new_code
                template.code_locked = True
                print(f"  Generated item_code: {new_code} for template: {template.name}")
            else:
                print(f"  [DRY RUN] Would generate item_code for template: {template.name}")
            migrated_count += 1
        except Exception as e:
            print(f"  ERROR: Failed to generate code for template {template.name}: {e}")
            continue
    
    if not dry_run and migrated_count > 0:
        await session.flush()
    
    return migrated_count


async def main():
    parser = argparse.ArgumentParser(description="Migrate existing records to have item_codes")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--tenant-id",
        default="b5ef68c4-18be-4fa6-a439-a23c34877550",
        help="Tenant ID to migrate (default: demo tenant)",
    )
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://medtrack:medtrack@localhost:5432/medtrack",
        help="Database URL",
    )
    
    args = parser.parse_args()
    
    print(f"{'=' * 60}")
    print(f"Item Code Migration Script")
    print(f"{'=' * 60}")
    print(f"Tenant ID: {args.tenant_id}")
    print(f"Dry Run: {args.dry_run}")
    print(f"{'=' * 60}\n")
    
    engine = create_async_engine(args.database_url, echo=False)
    
    async with engine.begin() as conn:
        async with AsyncSession(conn) as session:
            try:
                print("Migrating materials...")
                materials_count = await migrate_materials(session, args.tenant_id, args.dry_run)
                
                print("\nMigrating item_templates...")
                templates_count = await migrate_item_templates(session, args.tenant_id, args.dry_run)
                
                if not args.dry_run:
                    await session.commit()
                    print(f"\n{'=' * 60}")
                    print(f"Migration completed successfully!")
                    print(f"Materials migrated: {materials_count}")
                    print(f"Templates migrated: {templates_count}")
                    print(f"{'=' * 60}")
                else:
                    print(f"\n{'=' * 60}")
                    print(f"DRY RUN completed!")
                    print(f"Materials to migrate: {materials_count}")
                    print(f"Templates to migrate: {templates_count}")
                    print(f"Run without --dry-run to apply changes")
                    print(f"{'=' * 60}")
                    
            except Exception as e:
                await session.rollback()
                print(f"\nERROR: Migration failed: {e}")
                print("Rolling back all changes...")
                raise
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
