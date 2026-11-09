---
name: "Data Import/Export Patterns"
description: "Excel/CSV parsing, file handling, column mapping, data validation, batch processing, and export workflows for bulk operations"
inclusion: fileMatch
fileMatchPattern:
  - "backend/app/interfaces/api/v1/routes/**import*.py"
  - "backend/app/interfaces/api/v1/routes/**onboarding*.py"
  - "backend/app/interfaces/api/v1/routes/**export*.py"
  - "backend/app/application/**/services/**import*.py"
  - "backend/app/application/**/services/**export*.py"
  - "backend/app/infrastructure/services/**export*.py"
  - "frontend/src/**/*Upload*.tsx"
  - "frontend/src/**/*Import*.tsx"
  - "frontend/src/**/*Onboarding*.tsx"
  - "frontend/src/services/**import*.ts"
  - "frontend/src/services/**export*.ts"
---

# Data Import/Export Patterns

**Updated:** November 9, 2026  
**Version:** 1.0.0  
**Canonical References:**
- [`AGENTS.md`](../../AGENTS.md) § 5-7, 9, 14
- [`tech.md`](./tech.md) — Backend stack, async I/O
- [`backend-ddd-patterns.md`](./backend-ddd-patterns.md) — DDD layers, error handling
- [`product.md`](./product.md) — Multi-tenancy, soft deletes, business rules
- [`file-organization-standards.md`](./file-organization-standards.md) — File placement rules

---

## 1. File Handling

### 1.1 Supported File Formats

**Excel:**
- `.xlsx` — Modern Excel (preferred, required for multi-worksheet support)
- `.xls` — Legacy Excel (supported for backward compatibility)
- Binary format, read-only mode recommended for performance

**CSV:**
- `.csv` — Comma-Separated Values
- UTF-8 encoding with BOM detection (handle `utf-8-sig`)
- Header row mandatory (first row)

**Not Supported:**
- ❌ `.ods` (OpenDocument Spreadsheet)
- ❌ `.json` (for import; CSV or Excel only)
- ❌ `.tsv` or other delimited formats

### 1.2 File Size and Content Validation

**File Size Limits:**
```python
# Define in constants
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ROWS_PER_IMPORT = 10000  # Batch processing threshold

# Validate before parsing
if file.size > MAX_IMPORT_FILE_SIZE:
    raise HTTPException(
        status_code=413,
        detail=f"File exceeds {MAX_IMPORT_FILE_SIZE / 1024 / 1024} MB limit"
    )
```

**Content Validation:**
- ✅ Non-empty file (≥100 bytes)
- ✅ Valid format (file signature/magic bytes)
- ✅ Readable encoding (UTF-8, Latin-1 fallback)
- ❌ Empty files → clear error message
- ❌ Corrupted files → error with recovery suggestion

### 1.3 Corrupted and Invalid File Handling

**Detection Pattern:**
```python
try:
    # Attempt to open and validate structure
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
except openpyxl.utils.exceptions.InvalidFileException as e:
    raise HTTPException(
        status_code=422,
        detail="File is corrupted or not a valid Excel file. Please re-download the template."
    )
except Exception as e:
    logger.error("File parsing error", extra={"error": str(e)})
    raise HTTPException(
        status_code=422,
        detail="Could not parse file. Ensure it's a valid Excel (.xlsx) or CSV file."
    )
```

**User-Facing Messages:**
- Clear, actionable language
- Avoid technical jargon (no "InvalidFileException")
- Suggest recovery steps (download template, re-export)

### 1.4 Secure File Processing and Cleanup

**Temporary File Handling:**
```python
# Use in-memory processing when possible
import io

file_bytes = await file.read()  # Load into memory
file_stream = io.BytesIO(file_bytes)
# Process stream
file_stream.close()  # Explicit cleanup
```

**Upload Session Management:**
```python
# Session data stored in-memory or Redis
_sessions: Dict[str, Dict[str, Any]] = {}

# Auto-cleanup after 24 hours or on completion
async def cleanup_old_sessions():
    """Remove sessions older than 24 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    expired = [
        sid for sid, data in _sessions.items()
        if data.get("created_at", datetime.utcnow()) < cutoff
    ]
    for sid in expired:
        del _sessions[sid]
```

**Security:**
- ❌ Never write uploaded files to disk without validation
- ❌ Never expose file paths to users
- ❌ Never allow direct file access (use byte streams)
- ✅ Always validate file content before processing
- ✅ Always clean up temporary data after use

---

## 2. Excel Worksheet Handling

### 2.1 Never Blindly Depend on `workbook.active`

**Problem Pattern (❌ Wrong):**
```python
# ❌ WRONG: Assumes first worksheet contains data
ws = wb.active  # Could be "Field Guide", "Quick Start", etc.
```

**Solution Pattern (✅ Correct):**
```python
# ✅ CORRECT: Explicit worksheet selection with intelligence
ws = _find_data_worksheet(wb)

def _find_data_worksheet(wb: openpyxl.Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
    """Find the correct worksheet containing raw material data."""
    
    # Priority 1: Look for configured worksheet name
    configured_name = "Raw Materials"  # Document this per import type
    for sheet_name in wb.sheetnames:
        if sheet_name.lower() == configured_name.lower():
            return wb[sheet_name]
    
    # Priority 2: Fall back to header-based detection
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if _has_valid_headers(ws):
            return ws
    
    # Priority 3: Error if no valid worksheet found
    raise ValueError(
        f"No valid data worksheet found. "
        f"Expected worksheet named '{configured_name}' or worksheet with material headers. "
        f"Found worksheets: {', '.join(wb.sheetnames)}"
    )
```

### 2.2 Support Intelligent Worksheet Detection

**Header-Based Detection:**
```python
def _has_valid_headers(ws: openpyxl.worksheet.worksheet.Worksheet) -> bool:
    """Check if worksheet has recognized material headers."""
    if ws.max_row < 1:
        return False
    
    first_row = list(ws.iter_rows(max_row=1, values_only=True))[0]
    headers = [str(c).strip() if c else "" for c in first_row]
    
    # Must have ≥3 recognized headers to be data worksheet
    recognized = sum(
        1 for h in headers
        if h and (h in FRIENDLY_TO_TECHNICAL or h in RAW_MATERIAL_COLUMNS)
    )
    
    return recognized >= 3
```

**Informational Worksheet Exclusion:**
- Skip worksheets with titles like "Field Guide", "Quick Start", "Instructions", "Help"
- Skip worksheets with metadata/documentation content in Row 1
- Document expected worksheet names in import template and UI

### 2.3 Identify Header Rows Correctly

**Header Detection:**
```python
def _extract_headers(ws: openpyxl.worksheet.worksheet.Worksheet) -> List[str]:
    """Extract headers from first row of worksheet."""
    if ws.max_row < 1:
        raise ValueError("Worksheet is empty")
    
    first_row = list(ws.iter_rows(max_row=1, values_only=True))[0]
    headers = [
        str(c).strip() if c is not None else f"col_{i}"
        for i, c in enumerate(first_row)
    ]
    
    # Validate headers exist (not just "None", "None", ...)
    if all(h.startswith("col_") for h in headers):
        raise ValueError(
            "No recognized column headers found in first row. "
            "Please use the provided template."
        )
    
    return headers
```

**Assumptions:**
- Header row is always Row 1
- Headers are non-empty and describe columns
- Column order may vary (do not depend on fixed positions)

### 2.4 Handle Informational and Instruction Worksheets

**Common Patterns:**
```
┌─ Worksheet 1: "Field Guide" (documentation)
├─ Worksheet 2: "Quick Start" (instructions)
└─ Worksheet 3: "Raw Materials" (actual data) ✓

Or:

┌─ Worksheet 1: "Raw Materials" (data) ✓
└─ Worksheet 2: "Instructions" (guidance)
```

**Detection Rules:**
```python
INSTRUCTIONAL_KEYWORDS = {
    "guide", "quick start", "instructions", "help", "template",
    "how to", "legend", "notes", "metadata"
}

def _is_instructional_worksheet(sheet_name: str) -> bool:
    """Check if worksheet name indicates instructional content."""
    lower_name = sheet_name.lower()
    return any(kw in lower_name for kw in INSTRUCTIONAL_KEYWORDS)
```

**Error Handling:**
```python
# If only instructional worksheets found
if all(_is_instructional_worksheet(name) for name in wb.sheetnames):
    raise ValueError(
        "File contains only instructional worksheets. "
        "Please add data to the 'Raw Materials' worksheet and re-upload."
    )
```

### 2.5 Clear Error Messages for Missing Data Worksheets

**Error Message Format:**
```python
raise ValueError(
    f"No valid data worksheet found. "
    f"\n\nExpected: A worksheet named 'Raw Materials' with columns like:"
    f"\n  Item Code | Material Name | Category | Base Unit | ..."
    f"\n\nFound worksheets: {', '.join(wb.sheetnames)}"
    f"\n\nSolution: Download the latest template and ensure data is in the 'Raw Materials' worksheet."
)
```

**Convert to HTTP Response:**
```python
try:
    ws = _find_data_worksheet(wb)
except ValueError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

---

## 3. Column Mapping

### 3.1 Map Columns Using Normalized Header Names

**Problem (❌ Wrong):**
```python
# ❌ WRONG: Fixed column positions
item_code = row[0]
material_name = row[1]
category = row[2]
```

**Solution (✅ Correct):**
```python
# ✅ CORRECT: Header-based mapping with normalization
mapping = _suggest_mapping(headers)
mapped_data = _apply_mapping(raw_row, mapping)
```

### 3.2 Handle Case Differences and Whitespace

**Normalization:**
```python
def _normalize_header(header: str) -> str:
    """Normalize header for comparison."""
    return header.strip().lower().replace("  ", " ")

# Example mappings:
# "Item Code" → "item_code"
# "item code" → "item_code"
# "ITEM CODE" → "item_code"
# "Item  Code" → "item_code"
# "Item_Code" → "item_code"
```

**Fuzzy Matching:**
```python
from difflib import SequenceMatcher

def _similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    a_norm = a.lower().replace(" ", "_")
    b_norm = b.lower().replace(" ", "_")
    return SequenceMatcher(None, a_norm, b_norm).ratio()

# If header doesn't match exactly, find closest field
if header not in FRIENDLY_TO_TECHNICAL:
    best_field, best_score = "", 0.0
    for field in FRIENDLY_TO_TECHNICAL.values():
        score = _similarity(header, field)
        if score > best_score:
            best_score, best_field = score, field
    
    if best_score >= 0.6:
        mapping[header] = best_field
```

### 3.3 Support Reordered Columns

**Column Order Independence:**
```python
# ✅ Works regardless of column order
headers = ["Barcode", "Material Name", "Item Code", "Category"]

mapping = _suggest_mapping(headers)
# Result: {
#     "Barcode": "barcode",
#     "Material Name": "material_name",
#     "Item Code": "item_code",
#     "Category": "material_category"
# }

# Apply mapping to any column order
for raw_row in rows:
    mapped_data = _apply_mapping(raw_row, mapping)
    # Result includes all mapped fields regardless of input order
```

### 3.4 Identify Required and Optional Fields

**Field Classification:**
```python
REQUIRED_FIELDS = {"item_code", "material_name", "uom"}
OPTIONAL_FIELDS = {
    "barcode", "warehouse", "zone", "rack_bin",
    "min_stock", "max_stock", "reorder_level"
}

# Validate in mapping
for field in REQUIRED_FIELDS:
    if field not in mapping.values():
        raise ValueError(
            f"Required field '{TECHNICAL_TO_FRIENDLY[field]}' not found in Excel. "
            f"Please include this column in your file."
        )
```

### 3.5 Report Missing, Duplicate, and Unrecognized Columns

**Column Validation Report:**
```python
def _validate_headers(headers: List[str], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Validate headers and provide detailed report."""
    
    issues = {
        "missing_required": [],
        "unmapped_columns": [],
        "duplicate_mappings": [],
    }
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in mapping.values():
            issues["missing_required"].append(
                TECHNICAL_TO_FRIENDLY.get(field, field)
            )
    
    # Check for unmapped columns
    mapped_headers = set(mapping.keys())
    for header in headers:
        if header and header not in mapped_headers and header != "_ignore":
            issues["unmapped_columns"].append(header)
    
    # Check for duplicate target fields
    reverse_mapping = {}
    for source, target in mapping.items():
        if target and target != "_ignore":
            if target in reverse_mapping:
                issues["duplicate_mappings"].append({
                    "field": target,
                    "columns": [reverse_mapping[target], source]
                })
            reverse_mapping[target] = source
    
    return issues
```

### 3.6 Avoid Silently Mapping Incorrect Fields

**Mapping Confidence Threshold:**
```python
# Only auto-map if similarity is high (avoid guessing)
MAPPING_CONFIDENCE_THRESHOLD = 0.8

if best_score < MAPPING_CONFIDENCE_THRESHOLD:
    # Require user confirmation or explicit ignore
    mapping[header] = "_ignore"  # Explicit, not silent
    warnings.append({
        "column": header,
        "reason": f"Column name '{header}' doesn't match known fields. "
                  f"It will be ignored.",
        "severity": "warning"
    })
```

**User Feedback:**
```python
# Return mapping with warnings to frontend
{
    "mapping": mapping,
    "warnings": warnings,
    "errors": errors,
    "confidence_score": 0.95
}
```

---

## 4. Import Workflow

### 4.1 Complete Multi-Stage Workflow

**Workflow Stages:**
```
1. File Upload (user selects file)
   ↓
2. File Parsing (read bytes, detect format)
   ↓
3. Worksheet Selection (find data worksheet)
   ↓
4. Header Detection (extract headers from Row 1)
   ↓
5. Column Mapping (map Excel columns to fields)
   ↓
6. Data Transformation (normalize, type convert)
   ↓
7. Validation (business rules, duplicates, required fields)
   ↓
8. Preview (show user what will be imported)
   ↓
9. Confirmation (user approves or edits)
   ↓
10. Import Execution (save to database)
   ↓
11. Result Summary (success count, errors, audit log)
```

### 4.2 Stage Responsibilities

**Stage 1-5: File Handling (Backend)**
```python
@router.post("/material-onboarding/sessions")
async def create_session(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Dict[str, Any]:
    """Upload file, parse, detect worksheet, extract headers, suggest mapping."""
    
    # Read file
    file_bytes = await file.read()
    
    # Parse file (detect format, validate)
    headers, rows = _parse_file(file_bytes, file.filename)
    
    # Suggest mapping
    mapping = _suggest_mapping(headers)
    
    # Store in session
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "tenant_id": tenant_id,
        "headers": headers,
        "rows": rows,
        "mapping": mapping,
        "created_at": datetime.utcnow()
    }
    
    return {
        "session_id": session_id,
        "headers": headers,
        "mapping": mapping
    }
```

**Stage 6-7: Validation (Backend)**
```python
@router.post("/material-onboarding/sessions/{session_id}/validate")
async def validate_session(
    session_id: str,
    request: ValidateRequest,  # User's final mapping
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Dict[str, Any]:
    """Transform, validate all rows, prepare for preview."""
    
    session = _get_session(session_id, tenant_id)
    
    validated_rows = []
    errors = []
    
    for i, raw_row in enumerate(session["rows"], 1):
        try:
            # Transform (apply user's mapping)
            mapped_data = _apply_mapping(raw_row, request.mapping)
            
            # Validate row
            classification, status, issues, changes = _validate_row(
                mapped_data, i, existing_codes
            )
            
            validated_rows.append({
                "row_number": i,
                "classification": classification,  # "new" | "update" | "skip"
                "status": status,  # "ready" | "error"
                "data": mapped_data,
                "issues": issues
            })
        except Exception as e:
            errors.append({"row": i, "error": str(e)})
    
    return {
        "summary": {"valid": len([r for r in validated_rows if r["status"] == "ready"])},
        "rows": validated_rows,
        "errors": errors
    }
```

**Stage 8-11: Preview & Execution (Backend + Frontend)**
```python
# Frontend shows preview, user confirms
# Backend executes with user approval

@router.post("/material-onboarding/sessions/{session_id}/execute")
async def execute_import(
    session_id: str,
    request: ExecuteRequest,  # dry_run, duplicate_strategy
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> Dict[str, Any]:
    """Execute import with transaction safety."""
    
    session = _get_session(session_id, tenant_id)
    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    
    async with unit_of_work.transaction():
        for validated_row in session["validated_rows"]:
            try:
                if validated_row["classification"] == "new":
                    # Create material
                    material = Material.from_data(validated_row["data"])
                    await repo.save(material)
                    results["created"] += 1
                    
                elif validated_row["classification"] == "update":
                    # Update existing material
                    if request.duplicate_strategy == "UPDATE":
                        material = Material.from_data(validated_row["data"])
                        await repo.update(material)
                        results["updated"] += 1
                    else:
                        results["skipped"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "row": validated_row["row_number"],
                    "error": str(e)
                })
    
    return results
```

---

## 5. Data Validation

### 5.1 Required Field Validation

```python
def _validate_required_fields(data: Dict[str, Any]) -> List[Dict]:
    """Validate all required fields are present and non-empty."""
    issues = []
    
    for field in REQUIRED_FIELDS:
        value = str(data.get(field, "")).strip()
        
        if not value:
            issues.append({
                "field": field,
                "severity": "error",
                "message": f"{TECHNICAL_TO_FRIENDLY[field]} is required"
            })
    
    return issues
```

### 5.2 Data Types and Numeric/Date Parsing

```python
def _parse_numeric(value: str, field: str, min_val: int = None, max_val: int = None) -> tuple[float, List[Dict]]:
    """Parse and validate numeric value."""
    issues = []
    
    try:
        num_value = float(str(value).replace(",", "")) if value else 0.0
        
        if min_val is not None and num_value < min_val:
            issues.append({
                "field": field,
                "severity": "error",
                "message": f"{field} cannot be less than {min_val}"
            })
        
        if max_val is not None and num_value > max_val:
            issues.append({
                "field": field,
                "severity": "error",
                "message": f"{field} cannot exceed {max_val}"
            })
        
        return num_value, issues
    
    except ValueError:
        return 0.0, [{
            "field": field,
            "severity": "error",
            "message": f"{field} must be a valid number"
        }]
```

### 5.3 UOM and Category Validation

```python
async def _validate_references(data: Dict[str, Any]) -> List[Dict]:
    """Validate UOM and category exist in system."""
    issues = []
    
    # Validate UOM
    if data.get("uom"):
        uom = await uom_repo.get_by_code(data["uom"])
        if not uom:
            issues.append({
                "field": "uom",
                "severity": "error",
                "message": f"Unit '{data['uom']}' not found. "
                          f"Available: {', '.join(available_uoms)}"
            })
    
    # Validate Category
    if data.get("material_category"):
        category = await category_repo.get_by_name(data["material_category"])
        if not category:
            issues.append({
                "field": "material_category",
                "severity": "warning",
                "message": f"Category '{data['material_category']}' not found. "
                          f"Material will be created without category."
            })
    
    return issues
```

### 5.4 Business Rule Validation

```python
async def _validate_business_rules(data: Dict[str, Any], existing_codes: Dict) -> List[Dict]:
    """Validate business rules (duplicates, constraints, etc.)."""
    issues = []
    
    item_code = data.get("item_code", "").strip()
    
    # Duplicate check
    if item_code in existing_codes:
        issues.append({
            "field": "item_code",
            "severity": "warning",
            "message": f"Item code '{item_code}' already exists. "
                      f"This row will be marked as UPDATE."
        })
    
    # Logical constraints
    if data.get("min_stock") and data.get("max_stock"):
        min_s = float(data["min_stock"])
        max_s = float(data["max_stock"])
        if min_s >= max_s:
            issues.append({
                "field": "min_stock",
                "severity": "warning",
                "message": "Minimum stock should be less than maximum stock"
            })
    
    return issues
```

### 5.5 Duplicate Detection

**Strategy 1: Skip Duplicates**
```python
classification = "skip"  # Will not be imported
status = "ready"  # Can proceed, but won't change existing
```

**Strategy 2: Update Existing**
```python
classification = "update"  # Will overwrite existing record
status = "ready"  # Proceed with update
```

**Strategy 3: Fail on Duplicate**
```python
classification = "skip"
status = "error"  # Block entire import if duplicates found
issues.append({
    "field": "item_code",
    "severity": "error",
    "message": "Duplicate item code found. "
              "Set duplicate strategy to 'Update' to allow updates."
})
```

### 5.6 Row-Level Error Reports with Row Numbers

**Error Report Format:**
```python
{
    "row": 5,
    "item_code": "MAT-001",
    "errors": [
        {
            "field": "material_name",
            "severity": "error",
            "message": "Material Name is required"
        },
        {
            "field": "uom",
            "severity": "error",
            "message": "Unit 'PIECE' not found"
        }
    ]
}
```

**CSV Error Report for Download:**
```python
# Generate Excel with error details
def _generate_error_report(validated_rows: List[Dict]) -> bytes:
    """Generate Excel file with validation errors."""
    wb = openpyxl.Workbook()
    ws = wb.active
    
    ws.append(["Row Number", "Item Code", "Field", "Severity", "Message"])
    
    for row in validated_rows:
        if row["status"] == "error":
            for issue in row["issues"]:
                ws.append([
                    row["row_number"],
                    row["data"].get("item_code", ""),
                    issue["field"],
                    issue["severity"],
                    issue["message"]
                ])
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
```

---

## 6. Batch Processing

### 6.1 Follow Existing Repository Patterns

**Repository-Based Batch Insert:**
```python
async def batch_create_materials(
    tenant_id: UUID,
    materials: List[Material],
    unit_of_work: IUnitOfWork
) -> List[UUID]:
    """Create multiple materials in transaction."""
    
    ids = []
    async with unit_of_work.transaction():
        for material in materials:
            # Use existing repository pattern
            material_id = await material_repo.save(material)
            ids.append(material_id)
    
    return ids
```

### 6.2 Handle Partial Failures and Transaction Boundaries

**All-or-Nothing Strategy:**
```python
# Entire import succeeds or fails together
async with unit_of_work.transaction():
    for validated_row in validated_rows:
        # If any row fails, entire transaction rolls back
        try:
            material = Material.from_data(validated_row["data"])
            await material_repo.save(material)
        except Exception as e:
            # Rollback entire import
            raise ImportFailedError(f"Row {validated_row['row_number']}: {str(e)}")
```

**Partial Success Strategy (Optional):**
```python
# Import succeeds for valid rows, skips invalid ones
async with unit_of_work.transaction():
    for validated_row in validated_rows:
        if validated_row["status"] == "error":
            continue  # Skip rows with errors
        
        material = Material.from_data(validated_row["data"])
        await material_repo.save(material)
```

**User Choice via Duplicate Strategy:**
```python
if request.duplicate_strategy == "FAIL_IMPORT":
    # Fail if any duplicates found (all-or-nothing)
    if any(r["classification"] == "update" for r in validated_rows):
        raise ImportFailedError("Duplicates found and duplicate strategy is FAIL_IMPORT")
```

### 6.3 Avoid Duplicate Records and Repeated Imports

**Session-Based Import:**
```python
# Each session has unique ID
session_id = str(uuid.uuid4())

# Cannot import same session twice
if _sessions[session_id]["imported"]:
    raise HTTPException(
        status_code=409,
        detail="This import session has already been executed."
    )

# Mark as imported after execution
_sessions[session_id]["imported"] = True
_sessions[session_id]["executed_at"] = datetime.utcnow()
```

**Idempotency Key (Optional):**
```python
# For extra safety, use request ID
@router.post("/material-onboarding/sessions/{session_id}/execute")
async def execute_import(
    session_id: str,
    request: ExecuteRequest,
    idempotency_key: str = Header(None),  # Client provides
):
    """Prevent duplicate imports via idempotency key."""
    
    # Check if this import was already executed
    prior_result = _get_prior_execution(idempotency_key)
    if prior_result:
        return prior_result  # Return cached result
    
    # Execute import
    result = await _do_import(session_id, request)
    
    # Cache result
    _cache_execution(idempotency_key, result)
    
    return result
```

### 6.4 Preserve Tenant Isolation and Authorization

```python
async def execute_import(
    session_id: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Ensure tenant isolation and authorization."""
    
    session = _get_session(session_id, tenant_id)
    if session["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Check RBAC permission
    has_permission = await permission_service.check(
        user_id=user_id,
        resource="material:import"
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # All created materials inherit tenant_id
    for validated_row in session["validated_rows"]:
        validated_row["data"]["tenant_id"] = tenant_id
```

### 6.5 Maintain Audit Logging

**Audit Trail:**
```python
async def execute_import(...):
    """Log import execution."""
    
    audit_log = {
        "action": "bulk_import",
        "resource": "material",
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "import_session_id": session_id,
        "file_name": session.get("file_name"),
        "rows_processed": len(validated_rows),
        "rows_created": results["created"],
        "rows_updated": results["updated"],
        "rows_skipped": results["skipped"],
        "rows_failed": len(results["errors"]),
        "timestamp": datetime.utcnow(),
        "status": "success" if not results["errors"] else "partial_failure"
    }
    
    await audit_logger.log(audit_log)
```

---

## 7. Export Standards

### 7.1 Consistent Column Names and Ordering

**Export Format:**
```python
async def export_materials(
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> StreamingResponse:
    """Export materials to Excel with consistent format."""
    
    materials = await material_repo.list_by_tenant(tenant_id)
    
    # Use same column order as import template
    EXPORT_COLUMNS = [
        "item_code",
        "material_name",
        "material_category",
        "material_type",
        "uom",
        ...
    ]
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Write headers (friendly names)
    ws.append([TECHNICAL_TO_FRIENDLY[col] for col in EXPORT_COLUMNS])
    
    # Write data rows
    for material in materials:
        row = [getattr(material, col, "") for col in EXPORT_COLUMNS]
        ws.append(row)
    
    # ...return as StreamingResponse
```

### 7.2 Appropriate Date, Numeric, and Decimal Formats

```python
from openpyxl.styles import numbers

def _format_export_worksheet(ws: openpyxl.worksheet.worksheet.Worksheet):
    """Apply formatting to export worksheet."""
    
    # Header formatting
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4472C4", fill_type="solid")
    
    # Data formatting by column
    for row in ws.iter_rows(min_row=2):
        for i, cell in enumerate(row, 1):
            if i == 9:  # Decimal price column
                cell.number_format = '0.00'
            elif i == 4:  # Date column
                cell.number_format = 'yyyy-mm-dd'
            elif i in [5, 6, 7]:  # Numeric columns
                cell.number_format = '0'
```

### 7.3 Safe Handling of User-Provided Values

**Sanitization:**
```python
# Never trust user data in formulas
def _sanitize_cell_value(value: str) -> str:
    """Sanitize value for safe Excel export."""
    
    # Prevent Excel formula injection
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        value = "'" + value  # Prepend apostrophe to escape
    
    return value

# When writing to cells
for material in materials:
    row = [
        _sanitize_cell_value(str(getattr(material, col, "")))
        for col in EXPORT_COLUMNS
    ]
    ws.append(row)
```

### 7.4 Reusable Export Logic

**Service Layer:**
```python
class ExportService:
    """Centralized export service for consistent formatting."""
    
    @staticmethod
    async def export_materials_to_excel(
        materials: List[Material],
        include_archived: bool = False
    ) -> bytes:
        """Export materials to Excel."""
        # Implementation with consistent formatting
        pass
    
    @staticmethod
    async def export_materials_to_csv(
        materials: List[Material]
    ) -> str:
        """Export materials to CSV."""
        # Implementation with consistent formatting
        pass
```

**Reuse in Multiple Routes:**
```python
@router.get("/materials/export/excel")
async def export_materials_excel(tenant_id: UUID = Depends(...)):
    materials = await repo.list_by_tenant(tenant_id)
    file_bytes = await ExportService.export_materials_to_excel(materials)
    return StreamingResponse(content=file_bytes, ...)

@router.get("/materials/export/csv")
async def export_materials_csv(tenant_id: UUID = Depends(...)):
    materials = await repo.list_by_tenant(tenant_id)
    csv_content = await ExportService.export_materials_to_csv(materials)
    return StreamingResponse(content=csv_content, ...)
```

### 7.5 Clear Template and Downloadable File Generation

**Template Endpoint:**
```python
@router.get("/material-onboarding/template")
async def get_template(format: str = Query("xlsx", pattern="^(csv|xlsx)$")):
    """Download import template."""
    
    if format == "xlsx":
        file_bytes = _generate_excel_template()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "material-onboarding-template.xlsx"
    else:
        file_bytes = _generate_csv_template()
        media_type = "text/csv"
        filename = "material-onboarding-template.csv"
    
    return StreamingResponse(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

def _generate_excel_template() -> bytes:
    """Generate standard Excel template."""
    wb = openpyxl.Workbook()
    
    # Add Field Guide sheet
    ws_guide = wb.create_sheet("Field Guide", 0)
    ws_guide["A1"] = "MedTrack ERP - Raw Material Field Guide"
    # ... guidance content
    
    # Add Raw Materials sheet
    ws_data = wb.create_sheet("Raw Materials", 1)
    ws_data.append([TECHNICAL_TO_FRIENDLY[col] for col in EXPORT_COLUMNS])
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
```

---

## 8. Error Handling and User Experience

### 8.1 Actionable Error Messages

**Bad (❌):**
```python
raise HTTPException(status_code=500, detail="DuplicateComponentError")
```

**Good (✅):**
```python
raise HTTPException(
    status_code=422,
    detail="Item code 'MAT-001' already exists. "
           "To update existing materials, choose 'Update' in duplicate handling. "
           "To skip, choose 'Skip'."
)
```

### 8.2 Row-Level Error Reports

**Format:**
```json
{
  "row_number": 5,
  "item_code": "MAT-001",
  "errors": [
    {
      "field": "material_name",
      "severity": "error",
      "message": "Material Name is required"
    }
  ]
}
```

### 8.3 Import Success/Failure Summaries

**Summary Response:**
```python
{
  "status": "partial_success",
  "summary": {
    "total_rows": 100,
    "created": 85,
    "updated": 10,
    "skipped": 5,
    "failed": 0
  },
  "errors": [
    {
      "row": 5,
      "item_code": "DUP-001",
      "message": "Duplicate item code — skipped"
    }
  ],
  "download_error_report": "/api/v1/inventory/material-onboarding/sessions/{session_id}/validation-report"
}
```

### 8.4 Avoid Exposing Internal Exceptions

**Mapping Internal to User-Friendly:**
```python
try:
    material = Material(...)
    await repo.save(material)
except sqlalchemy.exc.IntegrityError as e:
    # ❌ Don't expose: "IntegrityError: Duplicate key value..."
    # ✅ Do expose:
    logger.error("Integrity violation", extra={"error": str(e)})  # Log internally
    raise HTTPException(
        status_code=422,
        detail="A material with this code already exists."
    )
except Exception as e:
    # ❌ Never:
    # raise HTTPException(status_code=500, detail=str(e))
    
    # ✅ Always:
    logger.error("Import error", extra={"error": str(e)})
    raise HTTPException(
        status_code=500,
        detail="An unexpected error occurred. Please contact support."
    )
```

---

## 9. Testing

### 9.1 Test Coverage Requirements

**Unit Tests (Pure Logic):**
```python
@pytest.mark.unit
def test_column_mapping_with_reordered_columns():
    """Test mapping handles reordered columns."""
    headers = ["Barcode", "Material Name", "Item Code"]
    mapping = _suggest_mapping(headers)
    
    assert mapping["Item Code"] == "item_code"
    assert mapping["Material Name"] == "material_name"
    assert mapping["Barcode"] == "barcode"

@pytest.mark.unit
def test_normalize_header_handles_case_and_whitespace():
    """Test header normalization."""
    assert _normalize_header("  Item Code  ") == "item code"
    assert _normalize_header("ITEM CODE") == "item code"
    assert _normalize_header("item_code") == "item code"
```

**Integration Tests (With Database):**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_bulk_import_preserves_tenant_isolation(db_session):
    """Test tenant data cannot leak between imports."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    # Import for tenant1
    materials_t1 = [...create test materials...]
    await execute_import(session_id_t1, tenant1_id)
    
    # Import for tenant2
    materials_t2 = [...different test materials...]
    await execute_import(session_id_t2, tenant2_id)
    
    # Verify isolation
    result_t1 = await repo.list_by_tenant(tenant1_id)
    assert len(result_t1) == 3
    
    result_t2 = await repo.list_by_tenant(tenant2_id)
    assert len(result_t2) == 3
    assert result_t1 != result_t2
```

### 9.2 Test Scenarios

| Scenario | Test | Purpose |
|----------|------|---------|
| Multiple worksheets | `test_worksheet_selection_prioritizes_raw_materials` | Finds correct sheet |
| Incorrect worksheet | `test_error_when_no_valid_worksheet` | Clear error message |
| Reordered columns | `test_mapping_handles_reordered_columns` | Order-independent |
| Missing headers | `test_error_when_required_header_missing` | Validation |
| Empty file | `test_error_on_empty_file` | Graceful handling |
| Invalid format | `test_error_on_invalid_excel_format` | File validation |
| Invalid data | `test_validation_errors_on_invalid_rows` | Data validation |
| Duplicates | `test_duplicate_handling_strategies` | SKIP/UPDATE/FAIL |
| Template compatibility | `test_existing_template_backward_compatibility` | Regression |
| Tenant isolation | `test_tenant_isolation_in_bulk_import` | Security |
| Authorization | `test_rbac_permission_checked_on_import` | Auth |

---

## Key Checklist

When implementing import/export features:

- [ ] **File Handling:** Support .xlsx and .csv only; validate file size
- [ ] **Worksheet Selection:** Never use `wb.active`; implement intelligent detection
- [ ] **Column Mapping:** Header-based, case-insensitive, support reordering
- [ ] **Validation:** Required fields, types, references, business rules, duplicates
- [ ] **Error Reporting:** Row-level errors, actionable messages, downloadable reports
- [ ] **Batch Processing:** Transaction-safe, partial failure strategy, prevent duplicates
- [ ] **Audit Logging:** Track all imports with user, tenant, row counts, status
- [ ] **Tenant Isolation:** Every operation scoped by tenant_id, verified in tests
- [ ] **Export Format:** Consistent columns, proper formatting, safe from formula injection
- [ ] **Testing:** Unit, integration, E2E; template compatibility; tenant isolation
- [ ] **User Experience:** Clear errors, progress feedback, downloadable templates

---

## Reference

- **DDD & CQRS Patterns:** [`backend-ddd-patterns.md`](./backend-ddd-patterns.md)
- **Technical Stack:** [`tech.md`](./tech.md)
- **Business Rules:** [`product.md`](./product.md)
- **Multi-tenancy & Security:** [AGENTS.md § 14](../../AGENTS.md)
- **Existing Implementation Reference:** `backend/app/interfaces/api/v1/routes/material_onboarding.py`

---

**Status:** Production Ready | Last Updated: November 9, 2026  
**Canonical Authority:** This steering file reflects verified patterns from MedTrack's existing Material Onboarding implementation and applies to all future data import/export features.


---

## 10. Test File Organization

### 10.1 Repository Test Structure

**Directory Layout:**
```
tests/
├── conftest.py              # Shared fixtures, mocks
├── __init__.py
├── unit/                    # Unit tests (pure logic)
│   ├── test_worksheet_fix.py
│   ├── test_material_onboarding_integration.py
│   ├── test_sample_upload.py
│   └── create_sample_upload_file.py  # Helper scripts
├── e2e/                     # End-to-end tests
│   ├── phase_2a_fg_available/
│   └── test_fg_reservation.py
└── debug/                   # Debug utilities
```

### 10.2 Test File Placement Rules

**Location Rules:**
- ✅ **Unit tests** → `tests/unit/test_*.py`
- ✅ **Integration tests** → `tests/unit/test_*.py` (with `@pytest.mark.integration`)
- ✅ **E2E tests** → `tests/e2e/test_*.py`
- ✅ **Helper scripts** → `tests/unit/` (for setup, fixtures, sample data)
- ❌ **Never** in repository root
- ❌ **Never** mixed with source code (`backend/`, `frontend/`)

**File Naming:**
```python
# ✅ Correct
test_worksheet_fix.py           # What is being tested
test_material_onboarding_integration.py
test_sample_upload.py

# ❌ Wrong
worksheet_test.py              # Wrong order
material_test_onboarding.py
sample_upload_test.py
```

### 10.3 Pytest Markers for Test Organization

```python
# tests/conftest.py
import pytest

# Mark tests for filtering
pytest.mark.unit        # Pure logic, no I/O
pytest.mark.integration # With database/services
pytest.mark.e2e         # Full workflow
pytest.mark.slow        # Long-running tests
pytest.mark.security    # Auth/RBAC tests
```

**Running Tests by Type:**
```bash
# Unit tests only
pytest tests/unit -m unit

# Integration tests only
pytest tests/unit -m integration

# E2E tests only
pytest tests/e2e

# All except slow tests
pytest -m "not slow"

# Security tests
pytest -m security
```

### 10.4 Test Discovery and Execution

**Pytest Configuration (pytest.ini):**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Pure logic tests (no I/O)
    integration: Database/service tests
    e2e: End-to-end workflow tests
    slow: Long-running tests
    security: Auth/RBAC tests
```

**Running All Tests:**
```bash
pytest tests/ --cov=backend/app --cov-report=term-missing
```

### 10.5 Example: Bulk Import Test Organization

**File Structure:**
```
tests/unit/
├── test_worksheet_fix.py
│   ├── test_worksheet_selection_prioritizes_raw_materials()
│   ├── test_error_when_no_valid_worksheet()
│   └── test_informational_worksheets_excluded()
│
├── test_material_onboarding_integration.py
│   ├── test_bulk_import_preserves_tenant_isolation()
│   ├── test_duplicate_handling_strategies()
│   └── test_rbac_permission_checked_on_import()
│
└── test_sample_upload.py
    ├── test_column_mapping_handles_reordering()
    ├── test_validation_errors_on_invalid_rows()
    └── test_error_report_download()
```

**Example Test File:**
```python
# tests/unit/test_worksheet_fix.py
import pytest
import io
import openpyxl
from backend.app.interfaces.api.v1.routes.material_onboarding import _find_data_worksheet

@pytest.mark.unit
def test_worksheet_selection_prioritizes_raw_materials():
    """Test that _find_data_worksheet finds 'Raw Materials' sheet."""
    # Create mock workbook with multiple sheets
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default
    
    ws_guide = wb.create_sheet("Field Guide", 0)
    ws_data = wb.create_sheet("Raw Materials", 1)
    
    # Should select "Raw Materials", not "Field Guide"
    result = _find_data_worksheet(wb)
    assert result.title == "Raw Materials"

@pytest.mark.unit
def test_error_when_no_valid_worksheet():
    """Test clear error when no data worksheet found."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    ws_guide = wb.create_sheet("Instructions", 0)
    ws_help = wb.create_sheet("Help", 1)
    
    with pytest.raises(ValueError, match="No valid data worksheet found"):
        _find_data_worksheet(wb)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_import_preserves_tenant_isolation(db_session, tenant_factory):
    """Test tenant data isolation in bulk import."""
    tenant1 = await tenant_factory.create()
    tenant2 = await tenant_factory.create()
    
    # Import for tenant1
    session_id = await create_upload_session(file_bytes, tenant_id=tenant1.id)
    await execute_import(session_id, tenant_id=tenant1.id)
    
    # Import for tenant2
    session_id = await create_upload_session(file_bytes, tenant_id=tenant2.id)
    await execute_import(session_id, tenant_id=tenant2.id)
    
    # Verify isolation
    materials_t1 = await repo.list_by_tenant(tenant1.id)
    materials_t2 = await repo.list_by_tenant(tenant2.id)
    
    assert len(materials_t1) == 3
    assert len(materials_t2) == 3
    assert all(m.tenant_id == tenant1.id for m in materials_t1)
    assert all(m.tenant_id == tenant2.id for m in materials_t2)
```

### 10.6 Cleanup: Remove Test Artifacts from Root

**Before Committing:**
```bash
# Remove test files from root
rm test_*.py
rm create_sample_upload_file.py
rm check_*.py
rm inspect_*.py

# Verify they're in tests/unit/
ls tests/unit/test_*.py
```

**Git Workflow:**
```bash
# Stage test files in new location
git add tests/unit/test_*.py

# Remove from root tracking
git rm -f test_*.py create_sample_upload_file.py

# Commit
git commit -m "chore: Move test files to tests/unit directory"
```

---

## Summary: Import/Export Development Checklist

**Before Starting:**
- [ ] Read this entire steering file (Sections 1-9)
- [ ] Check test organization (Section 10)
- [ ] Verify AGENTS.md multi-tenancy and DDD requirements

**During Implementation:**
- [ ] File handling: xlsx/csv only, validate format
- [ ] Worksheet selection: Explicit detection, not `wb.active`
- [ ] Column mapping: Header-based, fuzzy-matched, case-insensitive
- [ ] Validation: Required fields, types, references, business rules
- [ ] Error reporting: Row-level, actionable messages
- [ ] Batch processing: Transaction-safe, prevent duplicates
- [ ] Audit logging: All imports logged with details

**Testing:**
- [ ] Unit tests in `tests/unit/`
- [ ] Integration tests with `@pytest.mark.integration`
- [ ] E2E tests in `tests/e2e/`
- [ ] Min 75% code coverage

**Before Merging:**
- [ ] All tests passing
- [ ] Test files in proper directory
- [ ] No debug files in root
- [ ] Audit logs verified
- [ ] Tenant isolation tested
