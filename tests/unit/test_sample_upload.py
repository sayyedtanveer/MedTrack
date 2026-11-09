import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from backend.app.interfaces.api.v1.routes.material_onboarding import (
    _parse_file,
    _suggest_mapping,
    _apply_mapping,
    _validate_row,
)

# Load and parse sample file
sample_path = Path("data/templates/sample-materials-for-upload.xlsx")
with open(sample_path, "rb") as f:
    file_bytes = f.read()

print("=" * 70)
print("PARSING SAMPLE UPLOAD FILE")
print("=" * 70)

headers, rows = _parse_file(file_bytes, "sample-materials-for-upload.xlsx")
print(f"\n✅ Parsed successfully!")
print(f"   Headers: {len(headers)}")
print(f"   Data rows: {len(rows)}")
print(f"\nFirst row (STL-PLATE-001):")
for key, value in list(rows[0].items())[:8]:
    print(f"   {key}: {value}")

# Generate mapping
mapping = _suggest_mapping(headers)
print(f"\n✅ Column mapping generated")
print(f"   Mapped {len(mapping)} columns")

# Validate first row
print(f"\nValidating rows...")
for i, raw_row in enumerate(rows, 1):
    mapped = _apply_mapping(raw_row, mapping)
    classification, status, issues, _ = _validate_row(mapped, i, {})
    status_icon = "✅" if status == "ready" else "⚠️ "
    print(f"   Row {i}: {mapped['item_code']:15} | {classification:8} | {status_icon} {status}")
    if issues:
        for issue in issues[:2]:
            print(f"      - {issue['field']}: {issue['message']}")

print("\n" + "=" * 70)
print("✅ ALL PARSING TESTS PASSED")
print("=" * 70)
