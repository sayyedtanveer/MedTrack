"""
Test to verify the worksheet selection fix for material onboarding.
Tests that _find_data_worksheet() correctly selects the "Raw Materials" worksheet
instead of the first worksheet (Field Guide).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import openpyxl
from backend.app.interfaces.api.v1.routes.material_onboarding import (
    _find_data_worksheet,
    _parse_file,
)

def test_find_raw_materials_worksheet():
    """Test that _find_data_worksheet finds 'Raw Materials' worksheet."""
    print("\n=== Test 1: Find 'Raw Materials' worksheet ===")
    
    # Test with newest template
    template_path = Path("data/templates/newest-template.xlsx")
    
    wb = openpyxl.load_workbook(template_path, data_only=True)
    print(f"Template worksheets: {wb.sheetnames}")
    print(f"Active worksheet (before fix): {wb.active.title}")
    
    # Test _find_data_worksheet
    try:
        ws = _find_data_worksheet(wb)
        print(f"Selected worksheet (after fix): {ws.title}")
        
        # Verify it's the Raw Materials sheet
        assert ws.title == "Raw Materials", f"Expected 'Raw Materials', got '{ws.title}'"
        
        # Verify it has the expected headers
        first_row = list(ws.iter_rows(max_row=1, values_only=True))[0]
        headers = [str(c).strip() if c else "" for c in first_row]
        print(f"Headers from Raw Materials: {headers[:5]}...")
        
        # Check for expected headers
        expected_headers = {"Item Code", "Material Name", "Category", "Base Unit", "Barcode"}
        found_headers = set(h for h in headers if h)
        common = expected_headers & found_headers
        assert len(common) >= 3, f"Expected at least 3 matching headers, found {len(common)}: {common}"
        
        print(f"✅ PASS: Found correct worksheet with expected headers")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    finally:
        wb.close()


def test_parse_file_gets_correct_data():
    """Test that _parse_file extracts data from Raw Materials worksheet."""
    print("\n=== Test 2: Parse file gets correct data ===")
    
    template_path = Path("data/templates/newest-template.xlsx")
    with open(template_path, "rb") as f:
        file_bytes = f.read()
    
    try:
        headers, rows = _parse_file(file_bytes, "newest-template.xlsx")
        
        print(f"Extracted headers: {headers[:5]}...")
        print(f"Number of rows: {len(rows)}")
        
        # Should NOT have "MedTrack ERP - Raw Material Field Guide" as first header
        assert headers[0] != "MedTrack ERP - Raw Material Field Guide", \
            "Extracting from Field Guide instead of Raw Materials!"
        
        # Should have material-related headers
        expected_headers = {"Item Code", "Material Name", "Category", "Base Unit"}
        found_headers = set(h for h in headers if h in expected_headers)
        assert len(found_headers) >= 3, f"Expected material headers, got: {headers[:5]}"
        
        print(f"✅ PASS: Correctly extracted data from Raw Materials worksheet")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_templates():
    """Test that all templates work correctly."""
    print("\n=== Test 3: Test all templates ===")
    
    templates = [
        "data/templates/newest-template.xlsx",
        "data/templates/test-template.xlsx",
        "data/templates/material-onboarding-template-ENHANCED.xlsx",
    ]
    
    results = []
    for template_path_str in templates:
        template_path = Path(template_path_str)
        try:
            with open(template_path, "rb") as f:
                file_bytes = f.read()
            
            headers, rows = _parse_file(file_bytes, template_path.name)
            
            # Verify headers are from Raw Materials, not Field Guide
            assert "Item Code" in headers or "Material Name" in headers, \
                f"Template {template_path.name}: No material headers found"
            
            assert headers[0] != "MedTrack ERP - Raw Material Field Guide", \
                f"Template {template_path.name}: Extracted from Field Guide!"
            
            results.append((template_path.name, True, f"✅ {len(headers)} headers, {len(rows)} rows"))
        except Exception as e:
            results.append((template_path.name, False, f"❌ {e}"))
    
    # Print results
    all_passed = all(r[1] for r in results)
    for name, passed, msg in results:
        print(f"  {name}: {msg}")
    
    if all_passed:
        print(f"✅ PASS: All templates processed correctly")
    else:
        print(f"❌ FAIL: Some templates failed")
    
    return all_passed


def main():
    print("=" * 70)
    print("Testing Excel Worksheet Selection Fix")
    print("=" * 70)
    
    results = []
    results.append(("Find Raw Materials Worksheet", test_find_raw_materials_worksheet()))
    results.append(("Parse File Gets Correct Data", test_parse_file_gets_correct_data()))
    results.append(("All Templates Work", test_all_templates()))
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("=" * 70))
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
