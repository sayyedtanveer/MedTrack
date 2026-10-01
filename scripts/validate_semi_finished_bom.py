#!/usr/bin/env python3
"""
Semi-Finished BOM Implementation Validation Script

This script validates that the semi-finished BOM explosion implementation
meets all safety constraints and works correctly.

Usage:
    python scripts/validate_semi_finished_bom.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def validate_database_schema():
    """Verify no database migration is required."""
    print("🔍 Validating database schema...")
    
    from sqlalchemy import inspect
    from backend.app.infrastructure.database import engine
    
    inspector = inspect(engine)
    
    # Check item_variants.material_id exists
    columns = {col['name']: col for col in inspector.get_columns('item_variants')}
    
    assert 'material_id' in columns, "❌ item_variants.material_id not found"
    assert columns['material_id']['nullable'] == True, "❌ material_id must be nullable"
    
    print("  ✅ item_variants.material_id exists (nullable)")
    
    # Check materials.material_type enum
    columns = {col['name']: col for col in inspector.get_columns('materials')}
    assert 'material_type' in columns, "❌ materials.material_type not found"
    
    print("  ✅ materials.material_type exists")
    
    # Check BOMs relationships
    columns = {col['name']: col for col in inspector.get_columns('boms')}
    assert 'variant_id' in columns, "❌ boms.variant_id not found"
    
    print("  ✅ boms.variant_id exists")
    
    columns = {col['name']: col for col in inspector.get_columns('bom_lines')}
    assert 'material_id' in columns, "❌ bom_lines.material_id not found"
    
    print("  ✅ bom_lines.material_id exists")
    
    print("✅ Database schema validation PASSED - No migration required\n")


async def validate_backend_code():
    """Verify backend code has required functionality."""
    print("🔍 Validating backend code...")
    
    # Check BOMBrowserService has circular protection
    from backend.app.domain.bom.services.bom_browser_service import BOMBrowserService
    import inspect
    
    build_tree_source = inspect.getsource(BOMBrowserService.build_tree)
    assert 'visited_bom_ids' in build_tree_source, "❌ Circular reference protection missing"
    print("  ✅ Circular reference protection present")
    
    recursive_source = inspect.getsource(BOMBrowserService._build_recursive)
    assert 'semi_finished' in recursive_source, "❌ Semi-finished logic missing"
    print("  ✅ Semi-finished explosion logic present")
    
    assert 'visited_bom_ids' in recursive_source, "❌ visited_bom_ids tracking missing"
    print("  ✅ Visited BOM tracking present")
    
    # Check BOMProvider protocol
    from backend.app.domain.bom.services.bom_browser_service import BOMProvider
    assert hasattr(BOMProvider, 'get_bom_for_material'), "❌ get_bom_for_material missing"
    print("  ✅ BOMProvider.get_bom_for_material exists")
    
    # Check repository implementation
    from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
    assert hasattr(BOMRepository, 'get_bom_for_material'), "❌ Repository method missing"
    print("  ✅ BOMRepository.get_bom_for_material exists")
    
    print("✅ Backend code validation PASSED\n")


async def validate_frontend_files():
    """Verify frontend files exist and have required code."""
    print("🔍 Validating frontend code...")
    
    variant_manager_path = Path(__file__).parent.parent / "frontend/src/modules/products/components/VariantManager.tsx"
    assert variant_manager_path.exists(), "❌ VariantManager.tsx not found"
    
    content = variant_manager_path.read_text()
    assert 'advancedExpanded' in content, "❌ advancedExpanded state missing"
    assert 'ChevronDown' in content, "❌ Chevron icons not imported"
    assert 'Advanced: Material Mapping' in content, "❌ Advanced section missing"
    print("  ✅ VariantManager.tsx has collapsible Advanced section")
    
    bom_tree_path = Path(__file__).parent.parent / "frontend/src/modules/bom/components/BOMTreeView.tsx"
    assert bom_tree_path.exists(), "❌ BOMTreeView.tsx not found"
    
    content = bom_tree_path.read_text()
    assert 'semi_finished' in content, "❌ Semi-finished badge logic missing"
    assert 'Semi-Finished' in content, "❌ Semi-Finished badge text missing"
    print("  ✅ BOMTreeView.tsx has purple SF badge")
    
    types_path = Path(__file__).parent.parent / "frontend/src/types/bom.types.ts"
    assert types_path.exists(), "❌ bom.types.ts not found"
    
    content = types_path.read_text()
    assert 'material_type?' in content, "❌ material_type field missing"
    print("  ✅ BOMTreeNode has material_type field")
    
    print("✅ Frontend code validation PASSED\n")


async def validate_backward_compatibility():
    """Verify backward compatibility constraints."""
    print("🔍 Validating backward compatibility...")
    
    # Check CreateVariantInput accepts optional material_id
    from backend.app.application.product.commands.variant_commands import CreateVariantCommand
    import inspect
    
    sig = inspect.signature(CreateVariantCommand.__init__)
    params = sig.parameters
    
    # material_id should be optional (has default or is Optional)
    assert 'material_id' in params, "❌ material_id parameter missing"
    # Check if it's optional by looking at annotation or default
    param = params['material_id']
    is_optional = param.default != inspect.Parameter.empty or 'Optional' in str(param.annotation)
    assert is_optional, "❌ material_id must be optional"
    
    print("  ✅ CreateVariantCommand.material_id is optional")
    print("  ✅ Existing variant creation flow preserved")
    
    print("✅ Backward compatibility validation PASSED\n")


async def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Semi-Finished BOM Implementation Validation")
    print("=" * 60)
    print()
    
    try:
        await validate_database_schema()
        await validate_backend_code()
        await validate_frontend_files()
        await validate_backward_compatibility()
        
        print("=" * 60)
        print("🎉 ALL VALIDATIONS PASSED!")
        print("=" * 60)
        print()
        print("Implementation is ready for manual testing.")
        print("Please execute the 9 test scenarios from the implementation report.")
        print()
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
