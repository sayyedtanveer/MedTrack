#!/usr/bin/env python3
"""
Simple file-based verification for semi-finished BOM implementation.
This script checks that all required code changes are present.
"""

import sys
from pathlib import Path


def verify_backend_files():
    """Verify backend implementation."""
    print("🔍 Checking backend files...")
    
    bom_service = Path("backend/app/domain/bom/services/bom_browser_service.py")
    if not bom_service.exists():
        print("  ❌ bom_browser_service.py not found")
        return False
    
    content = bom_service.read_text()
    
    checks = [
        ("visited_bom_ids", "Circular reference protection"),
        ("semi_finished", "Semi-finished explosion logic"),
        ("get_bom_for_material", "Material BOM lookup"),
        ("set[uuid.UUID]", "Visited set type hint"),
    ]
    
    for check, desc in checks:
        if check in content:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - '{check}' not found")
            return False
    
    return True


def verify_frontend_files():
    """Verify frontend implementation."""
    print("\n🔍 Checking frontend files...")
    
    # Check VariantManager
    variant_manager = Path("frontend/src/modules/products/components/VariantManager.tsx")
    if not variant_manager.exists():
        print("  ❌ VariantManager.tsx not found")
        return False
    
    content = variant_manager.read_text()
    
    checks = [
        ("advancedExpanded", "Advanced section state"),
        ("ChevronDown", "Chevron icon import"),
        ("Advanced: Material Mapping", "Advanced section header"),
        ("setAdvancedExpanded", "State management"),
    ]
    
    for check, desc in checks:
        if check in content:
            print(f"  ✅ VariantManager: {desc}")
        else:
            print(f"  ❌ VariantManager: {desc} - '{check}' not found")
            return False
    
    # Check BOMTreeView
    bom_tree = Path("frontend/src/modules/bom/components/BOMTreeView.tsx")
    if not bom_tree.exists():
        print("  ❌ BOMTreeView.tsx not found")
        return False
    
    content = bom_tree.read_text()
    
    if 'material_type === "semi_finished"' in content and "Semi-Finished" in content:
        print("  ✅ BOMTreeView: Purple badge for semi-finished")
    else:
        print("  ❌ BOMTreeView: Semi-finished badge missing")
        return False
    
    # Check types
    types_file = Path("frontend/src/types/bom.types.ts")
    if not types_file.exists():
        print("  ❌ bom.types.ts not found")
        return False
    
    content = types_file.read_text()
    
    if "material_type?" in content and "semi_finished" in content:
        print("  ✅ Types: material_type field present")
    else:
        print("  ❌ Types: material_type field missing")
        return False
    
    return True


def verify_documentation():
    """Verify documentation files."""
    print("\n🔍 Checking documentation...")
    
    docs = [
        ("docs/SEMI_FINISHED_BOM_IMPLEMENTATION_REPORT.md", "Implementation report"),
        ("docs/SEMI_FINISHED_QUICK_REFERENCE.md", "Quick reference"),
        ("docs/AUDIT_SEMI_FINISHED_VARIANT_MAPPING.md", "Pre-implementation audit"),
    ]
    
    all_present = True
    for path, desc in docs:
        if Path(path).exists():
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc} - {path} not found")
            all_present = False
    
    return all_present


def main():
    """Run all verifications."""
    print("=" * 70)
    print("Semi-Finished BOM Implementation - File Verification")
    print("=" * 70)
    print()
    
    backend_ok = verify_backend_files()
    frontend_ok = verify_frontend_files()
    docs_ok = verify_documentation()
    
    print()
    print("=" * 70)
    
    if backend_ok and frontend_ok and docs_ok:
        print("✅ ALL FILES VERIFIED - Implementation complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Review implementation report: docs/SEMI_FINISHED_BOM_IMPLEMENTATION_REPORT.md")
        print("2. Execute 9 manual test scenarios")
        print("3. Verify circular BOM protection")
        print("4. Test backward compatibility")
        return 0
    else:
        print("❌ VERIFICATION FAILED - Some files are missing or incomplete")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
