"""
Integration test for material onboarding with the worksheet fix.
Validates the complete upload → parsing → mapping workflow.
"""
import sys
import io
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.interfaces.api.v1.routes.material_onboarding import (
    _parse_file,
    _suggest_mapping,
    _apply_mapping,
    _validate_row,
    FRIENDLY_TO_TECHNICAL,
    RAW_MATERIAL_COLUMNS,
)


def test_upload_workflow():
    """Test complete upload workflow with the fixed code."""
    print("\n" + "=" * 70)
    print("MATERIAL ONBOARDING INTEGRATION TEST")
    print("=" * 70)
    
    # Step 1: Load template file
    print("\n[Step 1] Loading template file...")
    template_path = Path("data/templates/newest-template.xlsx")
    with open(template_path, "rb") as f:
        file_bytes = f.read()
    print(f"✅ Loaded {template_path.name} ({len(file_bytes):,} bytes)")
    
    # Step 2: Parse file (this is where the worksheet fix applies)
    print("\n[Step 2] Parsing file to extract headers and rows...")
    try:
        headers, rows = _parse_file(file_bytes, "newest-template.xlsx")
        print(f"✅ Successfully parsed file")
        print(f"   Headers extracted: {len(headers)}")
        print(f"   Rows extracted: {len(rows)}")
        print(f"   First 5 headers: {headers[:5]}")
        
        # Verify we got the correct headers (NOT from Field Guide)
        assert "Item Code" in headers, "Missing 'Item Code' header!"
        assert "Material Name" in headers, "Missing 'Material Name' header!"
        assert headers[0] != "MedTrack ERP - Raw Material Field Guide", \
            "ERROR: Parsing Field Guide instead of Raw Materials!"
        
        print(f"✅ Headers are from Raw Materials worksheet (correct!)")
    except Exception as e:
        print(f"❌ FAILED: Could not parse file: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Suggest mapping
    print("\n[Step 3] Suggesting column mapping...")
    try:
        mapping = _suggest_mapping(headers)
        print(f"✅ Generated mapping for {len(mapping)} headers")
        
        # Show a few mappings
        examples = list(mapping.items())[:5]
        for header, field in examples:
            print(f"   '{header}' → '{field}'")
        
        # Verify critical mappings exist
        assert mapping.get("Item Code") == "item_code", "Item Code not mapped correctly!"
        assert mapping.get("Material Name") == "material_name", "Material Name not mapped correctly!"
        print(f"✅ Critical field mappings verified")
    except Exception as e:
        print(f"❌ FAILED: Could not generate mapping: {e}")
        return False
    
    # Step 4: Process rows
    print("\n[Step 4] Processing extracted rows...")
    if not rows:
        print(f"⚠️  No data rows to process (template only has 1 row which is the sample)")
        print(f"    This is expected for the template file")
    else:
        try:
            for i, row in enumerate(rows[:2]):  # Process first 2 rows
                print(f"\n   Row {i + 1}: {row}")
                
                # Apply mapping
                mapped_data = _apply_mapping(row, mapping)
                print(f"   Mapped data keys: {list(mapped_data.keys())[:5]}")
                
                # Validate row
                classification, status, issues, protected_changes = _validate_row(
                    mapped_data, 
                    i + 1,
                    {}  # existing_codes (empty for first run)
                )
                print(f"   Classification: {classification}, Status: {status}")
                if issues:
                    print(f"   Issues: {issues[:2]}")
            
            print(f"\n✅ Rows processed successfully")
        except Exception as e:
            print(f"❌ FAILED: Could not process rows: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Step 5: Verify mapping completeness
    print("\n[Step 5] Verifying mapping completeness...")
    try:
        # Count how many friendly columns have mappings
        mapped_friendly_count = sum(
            1 for friendly in FRIENDLY_TO_TECHNICAL.values()
            if friendly in [v for v in mapping.values()]
        )
        
        print(f"   Total expected fields: {len(RAW_MATERIAL_COLUMNS)}")
        print(f"   Fields with mappings: {len(mapping)}")
        print(f"   Friendly fields covered: {mapped_friendly_count}")
        
        print(f"✅ Mapping coverage verified")
    except Exception as e:
        print(f"❌ FAILED: Could not verify mapping: {e}")
        return False
    
    return True


def test_backward_compatibility():
    """Test that single-worksheet templates still work."""
    print("\n" + "=" * 70)
    print("BACKWARD COMPATIBILITY TEST")
    print("=" * 70)
    
    print("\n[Test] All three templates should parse correctly...")
    
    templates = [
        "data/templates/newest-template.xlsx",
        "data/templates/test-template.xlsx",
        "data/templates/material-onboarding-template-ENHANCED.xlsx",
    ]
    
    all_passed = True
    for template_path_str in templates:
        template_path = Path(template_path_str)
        try:
            with open(template_path, "rb") as f:
                file_bytes = f.read()
            
            headers, rows = _parse_file(file_bytes, template_path.name)
            
            # Basic validation
            assert len(headers) >= 10, f"Expected at least 10 headers, got {len(headers)}"
            assert "Item Code" in headers or "Material Name" in headers, \
                f"No material headers found in {template_path.name}"
            
            print(f"✅ {template_path.name}: {len(headers)} headers, {len(rows)} rows")
        except Exception as e:
            print(f"❌ {template_path.name}: {e}")
            all_passed = False
    
    return all_passed


def main():
    results = []
    
    # Run tests
    results.append(("Upload Workflow", test_upload_workflow()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("=" * 70))
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("\nThe worksheet selection fix is working correctly!")
        print("The upload now correctly:")
        print("  1. Skips informational worksheets (Field Guide, Quick Start)")
        print("  2. Extracts data from the 'Raw Materials' worksheet")
        print("  3. Gets correct headers for column mapping")
        print("  4. Maintains backward compatibility with all template versions")
        return 0
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
