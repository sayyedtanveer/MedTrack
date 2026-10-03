"""Scan supply_chain.py for Pyright-style type issues."""
import ast
import sys

path = "backend/app/interfaces/api/v1/routes/supply_chain.py"
src = open(path, encoding="utf-8").read()
lines = src.splitlines()

issues = []

for i, line in enumerate(lines, 1):
    stripped = line.strip()

    # Pattern 1: Optional UUID passed directly to str() without guard
    # e.g. str(x.some_optional_id) where field is Optional
    # We check for known Optional fields used without 'if'
    optional_fields = [
        "bom_id", "output_batch_id", "approved_by", "batch_id",
        "from_location_id", "to_location_id", "warehouse_location_id",
        "source_location_id", "vendor_location_id", "location_id",
        "base_unit_id", "material_id", "variant_id", "template_id",
        "purchase_order_id", "category_id",
    ]
    # Pattern 2: direct attribute access on possibly-None object
    # e.g. mat.name without 'if mat'
    # Pattern 3: missing 'await' on coroutines (None used as UUID)

    # Check for _bom_id narrowing — should exist after our fix
    if "_bom_id" in stripped and "uuid.UUID" in stripped:
        issues.append((i, "OK  narrowing present", stripped))

    # Pattern: o.bom_id used in where clause without narrowing
    if "BOMModel.id ==" in stripped and "o.bom_id" in stripped and "_bom_id" not in stripped:
        issues.append((i, "WARN o.bom_id not narrowed in WHERE", stripped))

    # Pattern: str() called on something that could be None without guard
    for f in ["output_batch_id", "approved_by", "batch_id", "base_unit_id"]:
        if f"str(o.{f})" in stripped or f"str(i.{f})" in stripped or f"str(b.{f})" in stripped:
            issues.append((i, f"WARN  str({f}) without None guard", stripped))

print(f"Scanned {len(lines)} lines\n")
print("Issues found:")
for lineno, label, content in issues:
    print(f"  L{lineno:4d}  {label}")
    print(f"         {content[:100]}")
    print()
