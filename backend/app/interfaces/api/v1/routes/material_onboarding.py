from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

import openpyxl
import openpyxl.comments
from openpyxl.utils import get_column_letter
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

from backend.app.application.inventory.services.onboarding_pricing import (
    agreement_dates, import_date, parse_import_decimal, plan_initial_cost,
)
from backend.app.application.procurement.pricing.direct_standard_cost import DirectStandardCostHandler
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel

router = APIRouter(prefix="/inventory/material-onboarding", tags=["Material Onboarding"])

# ── In-memory session store ───────────────────────────────────────────────────
_sessions: Dict[str, Dict[str, Any]] = {}

# ── Target field definitions ──────────────────────────────────────────────────
RAW_MATERIAL_COLUMNS = [
    "item_code", "material_name", "material_category", "material_type", "uom",
    "batch_tracking_enabled", "shelf_life", "expiry_tracking", "storage_location",
    "min_stock", "max_stock", "reorder_level", "reorder_quantity", "barcode", "traceability_enabled",
    "qc_required", "approved_supplier", "supplier_item_code", "purchase_uom", "lead_time", "moq",
    "length_uom", "cuttable_inventory", "remaining_quantity_tracking", "decimal_precision", "reusable_remainder",
    "opening_stock",
    # === SUPPLIER PRICING FIELDS (Phase 2) ===
    "supplier_name", "supplier_price", "supplier_currency", "supplier_moq", "supplier_uom",
    "effective_from_date", "effective_to_date", "proposed_initial_cost",
]

FRIENDLY_TO_TECHNICAL = {
    "Item Code": "item_code",
    "Material Name": "material_name",
    "Category": "material_category",
    "Base Unit": "uom",
    "Barcode": "barcode",
    "Storage Location": "storage_location",
    "Opening Stock": "opening_stock",
    "Minimum Stock": "min_stock",
    "Maximum Stock": "max_stock",
    "Reorder Level": "reorder_level",
    "Reorder Quantity": "reorder_quantity",
    "Track by Batch?": "batch_tracking_enabled",
    "Track Expiry?": "expiry_tracking",
    "Shelf Life": "shelf_life",
    "Track Traceability?": "traceability_enabled",
    "Quality Check Required?": "qc_required",
    "Preferred Supplier": "approved_supplier",
    "Supplier Item Code": "supplier_item_code",
    "Purchase Unit": "purchase_uom",
    "Lead Time (Days)": "lead_time",
    "Minimum Order Quantity": "moq",
    "Length Unit": "length_uom",
    "Can Be Cut?": "cuttable_inventory",
    "Track Remaining Quantity?": "remaining_quantity_tracking",
    "Decimal Places": "decimal_precision",
    "Reuse Remaining Material?": "reusable_remainder",
    # === SUPPLIER PRICING FIELDS (Phase 2) ===
    "Supplier Name": "supplier_name",
    "Supplier Price": "supplier_price",
    "Supplier Currency": "supplier_currency",
    "Supplier MOQ": "supplier_moq",
    "Supplier UOM": "supplier_uom",
    "Effective From": "effective_from_date",
    "Effective To": "effective_to_date",
    "Proposed Initial Cost": "proposed_initial_cost",
}
TECHNICAL_TO_FRIENDLY = {v: k for k, v in FRIENDLY_TO_TECHNICAL.items()}
FRIENDLY_COLUMNS = list(FRIENDLY_TO_TECHNICAL.keys())


# Fields that are considered protected (changing them on an existing material requires confirmation)
PROTECTED_FIELDS = {"material_type", "batch_tracking_enabled", "traceability_enabled", "uom"}

# Map target field → MaterialModel attribute
FIELD_TO_MODEL: Dict[str, str] = {
    "item_code": "item_code",
    "material_name": "name",
    "material_type": "material_type",
    "batch_tracking_enabled": "is_batch_tracked",
    "min_stock": "safety_stock",
    "reorder_level": "reorder_level",
    "lead_time": "lead_time_days",
    "length_uom": "length_uom",
    "qc_required": "qc_required_flag",
    "traceability_enabled": "is_serialized",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().replace(" ", "_"), b.lower().replace(" ", "_")).ratio()


def _find_data_worksheet(wb: openpyxl.Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
    """
    Find the correct worksheet containing raw material data.
    
    Priority:
    1. Worksheet named "Raw Materials" (case-insensitive)
    2. First worksheet with valid material headers (at least 3 matching columns)
    3. Raise error if none found
    
    Args:
        wb: Loaded Excel workbook
        
    Returns:
        Worksheet containing material data
        
    Raises:
        ValueError: If no valid data worksheet found
    """
    # Priority 1: Look for "Raw Materials" worksheet (case-insensitive)
    for sheet_name in wb.sheetnames:
        if sheet_name.lower() == "raw materials":
            return wb[sheet_name]
    
    # Priority 2: Find first worksheet with valid material headers
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if ws.max_row == 0:
            continue
        
        # Get first row
        try:
            first_row_data = list(ws.iter_rows(max_row=1, values_only=True))
            if not first_row_data or not first_row_data[0]:
                continue
            
            first_row = first_row_data[0]
            headers = [str(c).strip() if c else "" for c in first_row]
            
            # Count matches against known columns
            matches = sum(
                1 for h in headers 
                if h and (h in FRIENDLY_TO_TECHNICAL or h in RAW_MATERIAL_COLUMNS)
            )
            
            # If at least 3 columns match, consider this a data worksheet
            if matches >= 3:
                return ws
        except Exception:
            # Skip worksheets that can't be read
            continue
    
    # No valid worksheet found
    raise ValueError(
        f"No valid data worksheet found. "
        f"Expected worksheet named 'Raw Materials' with material headers "
        f"(Item Code, Material Name, Category, Base Unit, etc.). "
        f"Found worksheets: {', '.join(wb.sheetnames)}"
    )


def _suggest_mapping(headers: List[str]) -> Dict[str, str]:
    """Auto-suggest column-to-field mappings based on name similarity."""
    mapping: Dict[str, str] = {}
    for header in headers:
        if header in FRIENDLY_TO_TECHNICAL:
            mapping[header] = FRIENDLY_TO_TECHNICAL[header]
            continue
        if header in RAW_MATERIAL_COLUMNS:
            mapping[header] = header
            continue

        best_field, best_score = "", 0.0
        for field in RAW_MATERIAL_COLUMNS:
            score = _similarity(header, field)
            if score > best_score:
                best_score, best_field = score, field
        for friendly_field, tech_field in FRIENDLY_TO_TECHNICAL.items():
            score = _similarity(header, friendly_field)
            if score > best_score:
                best_score, best_field = score, tech_field

        if best_score >= 0.6:
            mapping[header] = best_field
    return mapping


def _parse_file(file_bytes: bytes, file_name: str) -> tuple[List[str], List[Dict[str, str]]]:
    """Return (headers, rows) from an xlsx or csv file.
    
    For Excel files:
    - Automatically detects the data worksheet (prioritizes "Raw Materials")
    - Extracts headers from first row of data worksheet
    - Skips empty rows
    
    For CSV files:
    - Uses standard CSV parsing
    """
    name_lower = (file_name or "").lower()
    if name_lower.endswith(".csv"):
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        rows = [{k: (str(v).strip() if v else "") for k, v in row.items()} for row in reader]
        return headers, rows
    else:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            
            # Use smart worksheet selector to find the data worksheet
            ws = _find_data_worksheet(wb)
            
            if ws is None:
                raise ValueError("No data worksheet found in workbook")
            
            headers: List[str] = []
            rows: List[Dict[str, str]] = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    headers = [str(c).strip() if c is not None else f"col_{j}" for j, c in enumerate(row)]
                    continue
                if all(c is None for c in row):
                    continue
                rows.append({headers[j]: (str(c).strip() if c is not None else "") for j, c in enumerate(row) if j < len(headers)})
            wb.close()
            return headers, rows
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")


def _apply_mapping(raw_row: Dict[str, str], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Convert a raw row using the column mapping."""
    data: Dict[str, Any] = {}
    for source, target in mapping.items():
        if target and target != "_ignore":
            value = raw_row.get(source, "")
            data[target] = import_date(value) if target in {"effective_from_date", "effective_to_date"} else value
    return data


def _bool_val(v: Any) -> bool:
    return str(v).strip().lower() in ("true", "yes", "1", "y")


def _validate_row(
    data: Dict[str, Any],
    row_num: int,
    existing_codes: Dict[str, Dict[str, Any]],
) -> tuple[str, str, List[Dict], List[Dict]]:
    """
    Returns (classification, status, issues, protected_changes).
    classification: 'new' | 'update' | 'skip'
    """
    issues: List[Dict] = []
    protected_changes: List[Dict] = []

    name = str(data.get("material_name", "")).strip()
    item_code = str(data.get("item_code", "")).strip()
    uom = str(data.get("uom", "")).strip()
    category = str(data.get("material_category", "")).strip()

    def friendly(f: str) -> str:
        return TECHNICAL_TO_FRIENDLY.get(f, f)

    # Required field checks
    if not name:
        issues.append({"field": "material_name", "severity": "error", "message": "Material Name is required"})
    elif len(name) < 3:
        issues.append({"field": "material_name", "severity": "error", "message": "Material Name must be at least 3 characters"})
    elif len(name) > 200:
        issues.append({"field": "material_name", "severity": "error", "message": "Material Name cannot exceed 200 characters"})
    
    if not uom:
        issues.append({"field": "uom", "severity": "error", "message": "Base Unit is required"})
    elif len(uom) > 20:
        issues.append({"field": "uom", "severity": "error", "message": "Base Unit cannot exceed 20 characters"})
    
    if not category:
        issues.append({"field": "material_category", "severity": "warning", "message": "Category not specified — will be left blank"})
    
    # Item Code validation (for updates)
    if item_code and len(item_code) > 50:
        issues.append({"field": "item_code", "severity": "error", "message": "Item Code cannot exceed 50 characters"})
    
    # Barcode validation
    barcode = str(data.get("barcode", "")).strip()
    if barcode and len(barcode) > 100:
        issues.append({"field": "barcode", "severity": "error", "message": "Barcode cannot exceed 100 characters"})

    # Numeric validation
    min_stock_val = None
    max_stock_val = None
    reorder_level_val = None
    reorder_qty_val = None
    lead_time_val = None
    moq_val = None
    shelf_life_val = None
    decimal_precision_val = None
    
    # Stock and inventory numeric fields
    for field in ("reorder_level", "min_stock", "max_stock", "reorder_quantity", "moq"):
        val = data.get(field, "")
        if val:
            try:
                num_val = float(str(val).replace(",", ""))
                if num_val < 0:
                    issues.append({"field": field, "severity": "error", "message": f"{friendly(field)} cannot be negative"})
                elif num_val > 999_999_999.99:
                    issues.append({"field": field, "severity": "error", "message": f"{friendly(field)} cannot exceed 999,999,999.99"})
                else:
                    if field == "min_stock":
                        min_stock_val = num_val
                    elif field == "max_stock":
                        max_stock_val = num_val
                    elif field == "reorder_level":
                        reorder_level_val = num_val
                    elif field == "reorder_quantity":
                        reorder_qty_val = num_val
                    elif field == "moq":
                        moq_val = num_val
            except ValueError:
                issues.append({"field": field, "severity": "error", "message": f"{friendly(field)} must be a valid number"})
    
    # Lead time validation (days)
    lead_time_str = str(data.get("lead_time", "")).strip()
    if lead_time_str:
        try:
            lead_time_val = int(float(lead_time_str))
            if lead_time_val < 0:
                issues.append({"field": "lead_time", "severity": "error", "message": "Lead Time cannot be negative"})
            elif lead_time_val > 3650:  # 10 years
                issues.append({"field": "lead_time", "severity": "warning", "message": f"Lead Time ({lead_time_val} days) seems unusually long - please verify"})
        except ValueError:
            issues.append({"field": "lead_time", "severity": "error", "message": "Lead Time must be a whole number (days)"})
    
    # Shelf life validation (days)
    shelf_life_str = str(data.get("shelf_life", "")).strip()
    if shelf_life_str:
        try:
            shelf_life_val = int(float(shelf_life_str))
            if shelf_life_val < 0:
                issues.append({"field": "shelf_life", "severity": "error", "message": "Shelf Life cannot be negative"})
            elif shelf_life_val > 7300:  # 20 years
                issues.append({"field": "shelf_life", "severity": "warning", "message": f"Shelf Life ({shelf_life_val} days) seems unusually long - please verify"})
        except ValueError:
            issues.append({"field": "shelf_life", "severity": "error", "message": "Shelf Life must be a whole number (days)"})
    
    # Decimal precision validation
    decimal_str = str(data.get("decimal_precision", "")).strip()
    if decimal_str:
        try:
            decimal_precision_val = int(float(decimal_str))
            if decimal_precision_val < 0:
                issues.append({"field": "decimal_precision", "severity": "error", "message": "Decimal Places cannot be negative"})
            elif decimal_precision_val > 6:
                issues.append({"field": "decimal_precision", "severity": "warning", "message": f"Decimal Places ({decimal_precision_val}) is unusually high - typically 0-4"})
        except ValueError:
            issues.append({"field": "decimal_precision", "severity": "error", "message": "Decimal Places must be a whole number"})

    # Opening stock validation: numeric, >= 0, max 999,999,999.99
    opening_stock_val = str(data.get("opening_stock", "")).strip()
    opening_stock_num = None
    if opening_stock_val:
        try:
            opening_stock_num = float(opening_stock_val.replace(",", ""))
            if opening_stock_num < 0:
                issues.append({
                    "field": "opening_stock",
                    "severity": "error",
                    "message": f"{friendly('opening_stock')} must be a non-negative number",
                })
            elif opening_stock_num > 999_999_999.99:
                issues.append({
                    "field": "opening_stock",
                    "severity": "error",
                    "message": f"{friendly('opening_stock')} must not exceed 999,999,999.99",
                })
        except ValueError:
            issues.append({
                "field": "opening_stock",
                "severity": "error",
                "message": f"{friendly('opening_stock')} must be a non-negative number",
            })
    
    # Stock level logic validation: min_stock <= opening_stock (if provided) <= max_stock
    if min_stock_val is not None and max_stock_val is not None:
        if min_stock_val > max_stock_val:
            issues.append({
                "field": "min_stock",
                "severity": "error",
                "message": f"Minimum Stock ({min_stock_val}) cannot be greater than Maximum Stock ({max_stock_val})",
            })
        elif min_stock_val == max_stock_val and min_stock_val > 0:
            issues.append({
                "field": "min_stock",
                "severity": "warning",
                "message": f"Minimum Stock and Maximum Stock are equal ({min_stock_val}) - no buffer for stock fluctuation",
            })
    
    # Reorder level should be between min and max
    if reorder_level_val is not None:
        if min_stock_val is not None and reorder_level_val < min_stock_val:
            issues.append({
                "field": "reorder_level",
                "severity": "warning",
                "message": f"Reorder Level ({reorder_level_val}) is below Minimum Stock ({min_stock_val}) - may cause stockouts",
            })
        if max_stock_val is not None and reorder_level_val > max_stock_val:
            issues.append({
                "field": "reorder_level",
                "severity": "warning",
                "message": f"Reorder Level ({reorder_level_val}) exceeds Maximum Stock ({max_stock_val}) - will never trigger reorder",
            })
    
    # Reorder quantity validation
    if reorder_qty_val is not None and reorder_qty_val == 0:
        issues.append({
            "field": "reorder_quantity",
            "severity": "warning",
            "message": "Reorder Quantity is 0 - no quantity will be ordered when stock is low",
        })
    
    if opening_stock_num is not None and min_stock_val is not None:
        if opening_stock_num < min_stock_val:
            issues.append({
                "field": "opening_stock",
                "severity": "warning",
                "message": f"Opening Stock ({opening_stock_num}) is below Minimum Stock ({min_stock_val}) - will trigger low stock alert immediately",
            })
    
    if opening_stock_num is not None and max_stock_val is not None:
        if opening_stock_num > max_stock_val:
            issues.append({
                "field": "opening_stock",
                "severity": "warning",
                "message": f"Opening Stock ({opening_stock_num}) exceeds Maximum Stock ({max_stock_val}) - consider increasing max stock",
            })
    
    # MOQ vs Reorder Quantity check
    if moq_val is not None and reorder_qty_val is not None:
        if reorder_qty_val < moq_val:
            issues.append({
                "field": "reorder_quantity",
                "severity": "warning",
                "message": f"Reorder Quantity ({reorder_qty_val}) is less than Minimum Order Quantity ({moq_val}) - orders may be rejected by supplier",
            })
    
    # Yes/No field validation
    yes_no_fields = {
        "batch_tracking_enabled": "Track by Batch?",
        "expiry_tracking": "Track Expiry?",
        "traceability_enabled": "Track Traceability?",
        "qc_required": "Quality Check Required?",
        "cuttable_inventory": "Can Be Cut?",
        "remaining_quantity_tracking": "Track Remaining Quantity?",
        "reusable_remainder": "Reuse Remaining Material?",
    }
    
    for field, friendly_name in yes_no_fields.items():
        val = str(data.get(field, "")).strip().upper()
        if val and val not in ("YES", "NO", "Y", "N", "TRUE", "FALSE", "1", "0", ""):
            issues.append({
                "field": field,
                "severity": "error",
                "message": f"{friendly_name} must be Yes/No (found: '{data.get(field)}')",
            })
    
    # Expiry tracking logic validation
    expiry_tracking = str(data.get("expiry_tracking", "")).strip().upper()
    if expiry_tracking in ("YES", "Y", "TRUE", "1"):
        if not shelf_life_val:
            issues.append({
                "field": "shelf_life",
                "severity": "warning",
                "message": "Track Expiry is enabled but Shelf Life not specified - expiry dates cannot be calculated",
            })
    
    if shelf_life_val and expiry_tracking in ("NO", "N", "FALSE", "0"):
        issues.append({
            "field": "expiry_tracking",
            "severity": "warning",
            "message": f"Shelf Life specified ({shelf_life_val} days) but Track Expiry is disabled - shelf life will be ignored",
        })
    
    # Batch tracking + expiry tracking recommendation
    batch_tracking = str(data.get("batch_tracking_enabled", "")).strip().upper()
    if expiry_tracking in ("YES", "Y", "TRUE", "1") and batch_tracking not in ("YES", "Y", "TRUE", "1"):
        issues.append({
            "field": "batch_tracking_enabled",
            "severity": "warning",
            "message": "Expiry tracking is enabled without batch tracking - consider enabling batch tracking for better traceability",
        })
    
    # Cuttable inventory validation
    cuttable = str(data.get("cuttable_inventory", "")).strip().upper()
    track_remaining = str(data.get("remaining_quantity_tracking", "")).strip().upper()
    reusable = str(data.get("reusable_remainder", "")).strip().upper()
    
    if cuttable in ("YES", "Y", "TRUE", "1"):
        if track_remaining not in ("YES", "Y", "TRUE", "1"):
            issues.append({
                "field": "remaining_quantity_tracking",
                "severity": "warning",
                "message": "Can Be Cut is enabled but Track Remaining Quantity is disabled - remaining lengths will not be tracked",
            })
    
    if track_remaining in ("YES", "Y", "TRUE", "1") and cuttable not in ("YES", "Y", "TRUE", "1"):
        issues.append({
            "field": "cuttable_inventory",
            "severity": "warning",
            "message": "Track Remaining Quantity is enabled but Can Be Cut is disabled - this combination is unusual",
        })
    
    # ═════════════════════════════════════════════════════════════════════════════
    # SUPPLIER PRICING VALIDATION (Phase 2)
    # ═════════════════════════════════════════════════════════════════════════════
    if len(str(data.get("supplier_item_code", "")).strip()) > 120:
        issues.append({"field": "supplier_item_code", "severity": "error",
                       "message": "Supplier Item Code cannot exceed 120 characters"})

    pricing_fields = ("supplier_name", "supplier_price", "supplier_currency", "supplier_moq",
                      "supplier_uom", "effective_from_date", "effective_to_date")
    has_pricing = any(str(data.get(field, "")).strip() for field in pricing_fields)
    if has_pricing:
        for field in ("supplier_name", "supplier_price", "supplier_currency", "supplier_uom"):
            if not str(data.get(field, "")).strip():
                issues.append({"field": field, "severity": "error", "message": f"{friendly(field)} is required when providing supplier pricing"})
        currency = str(data.get("supplier_currency", "")).strip()
        if currency and not re.fullmatch(r"[A-Z]{3}", currency):
            issues.append({"field": "supplier_currency", "severity": "error", "message": "Supplier Currency must be a three-letter uppercase currency code"})
        if len(str(data.get("supplier_uom", ""))) > 20:
            issues.append({"field": "supplier_uom", "severity": "error", "message": "Supplier UOM cannot exceed 20 characters"})
        try:
            agreement_dates(data, datetime.now(timezone.utc).date())
        except ValueError:
            issues.append({"field": "effective_from_date", "severity": "error", "message": "Use valid YYYY-MM-DD dates with Effective To on or after Effective From"})
    for field in ("supplier_price", "supplier_moq", "proposed_initial_cost"):
        value = str(data.get(field, "")).strip()
        if value:
            try:
                number = parse_import_decimal(value)
                if field == "supplier_price" and number <= 0:
                    raise ValueError("Supplier Price must be greater than zero")
                if field in {"supplier_price", "supplier_moq"} and number.as_tuple().exponent < -6:
                    raise ValueError("Supplier price and MOQ support at most six decimal places")
            except ValueError as exc:
                issues.append({"field": field, "severity": "error", "message": f"{friendly(field)}: {exc}"})

    by_code = existing_codes.get(item_code.upper()) if item_code else None
    by_name = existing_codes.get(name.upper())
    if ((by_code and str(by_code.get("name", "")).upper() != name.upper())
        or (item_code and by_name and str(by_name.get("item_code") or by_name.get("code") or "").upper() != item_code.upper())):
        issues.append({"field": "item_code", "severity": "error", "message": "Material code/name identity conflict; use the existing material's matching code and name"})

    # Determine classification and protected changes
    lookup_key = item_code.upper() if item_code else name.upper()
    existing = existing_codes.get(lookup_key)

    if existing:
        classification = "update"
        # Check protected fields
        for pf in PROTECTED_FIELDS:
            new_val = str(data.get(pf, "")).strip()
            if not new_val:
                continue
            model_attr = FIELD_TO_MODEL.get(pf, pf)
            old_val = str(existing.get(model_attr, "")).strip()
            if old_val and old_val != new_val:
                protected_changes.append({"field": pf, "from": old_val, "to": new_val})
    else:
        classification = "new"

    for numeric_field in ("opening_stock", "min_stock", "max_stock", "reorder_level", "reorder_quantity", "moq"):
        value = str(data.get(numeric_field, "")).strip()
        if value:
            try:
                parse_import_decimal(value)
            except ValueError as exc:
                issues.append({"field": numeric_field, "severity": "error", "message": f"{friendly(numeric_field)}: {exc}"})

    has_errors = any(i["severity"] == "error" for i in issues)
    row_status = "error" if has_errors else "ready"
    if has_errors:
        classification = "skip"

    return classification, row_status, issues, protected_changes


# ── Schemas ───────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    mapping: Dict[str, str]


class ExecuteRequest(BaseModel):
    dry_run: bool = False


class RowUpdateRequest(BaseModel):
    class Config:
        extra = "allow"


# ── Helper: Fetch Storage Locations ───────────────────────────────────────────

async def _get_storage_locations(db_session: AsyncSession, tenant_id: uuid.UUID) -> List[str]:
    """
    Fetch all active storage locations for a tenant.
    Used for Excel data validation dropdown.
    Returns: List of location names/codes sorted alphabetically.
    """
    try:
        from backend.app.infrastructure.persistence.models.location_model import LocationModel
        
        # Priority: Use code if available, fallback to name
        stmt = (
            select(LocationModel)
            .where(
                LocationModel.tenant_id == tenant_id,
                LocationModel.is_deleted == False,
                LocationModel.is_active == True
            )
            .order_by(LocationModel.name.asc())
        )
        
        result = await db_session.execute(stmt)
        locations = result.scalars().all()
        
        # Return code or name (code preferred if available)
        location_values = [
            loc.code if loc.code else loc.name 
            for loc in locations 
            if loc.code or loc.name
        ]
        return location_values
    except Exception as e:
        logging.exception("Could not fetch storage locations", extra={"tenant_id": str(tenant_id)})
        raise


async def _get_unit_of_measures(db_session: AsyncSession, tenant_id: uuid.UUID) -> List[str]:
    """
    Fetch all active Units of Measure for a tenant.
    Used for Excel data validation dropdown.
    Returns: List of UOM codes sorted alphabetically.
    """
    try:
        stmt = (
            select(UnitOfMeasureModel.code)
            .where(
                UnitOfMeasureModel.tenant_id == tenant_id,
                UnitOfMeasureModel.is_deleted == False,
                UnitOfMeasureModel.is_active == True
            )
            .order_by(UnitOfMeasureModel.code.asc())
        )
        
        result = await db_session.execute(stmt)
        uom_codes = [row for row in result.scalars().all() if row]
        return uom_codes
    except Exception as e:
        logging.exception("Could not fetch UOMs", extra={"tenant_id": str(tenant_id)})
        raise


async def _get_default_storage_location(db_session: AsyncSession, tenant_id: uuid.UUID) -> Optional[str]:
    """
    Fetch the default storage location for a tenant.
    Returns: Location code or name, or None if no default configured.
    """
    try:
        from backend.app.infrastructure.persistence.models.location_model import LocationModel
        
        stmt = (
            select(LocationModel)
            .where(
                LocationModel.tenant_id == tenant_id,
                LocationModel.is_default == True,
                LocationModel.is_deleted == False,
                LocationModel.is_active == True
            )
        )
        
        result = await db_session.execute(stmt)
        location = result.scalars().first()
        
        if location:
            return location.code if location.code else location.name
        return None
    except Exception as e:
        logging.exception("Could not fetch default storage location", extra={"tenant_id": str(tenant_id)})
        raise


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/template",
    summary="Download the material onboarding template",
    # Master data must come from the authenticated tenant.
)
async def get_template(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    request: Request = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Return a downloadable template file with the expected column headers.
    
    Excel dropdowns include active master data from the authenticated tenant.
    """
    
    # Fetch storage locations, UOMs, and default location for dropdown (if authenticated)
    storage_locations = []
    unit_of_measures = []
    supplier_names = []
    # Same suggested currencies as company settings; other codes remain editable.
    currency_codes = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD", "CAD"]
    default_location = None
    try:
        if request and tenant_id:
            logging.info(f"🔍 Fetching master data for tenant: {tenant_id}")
            container = get_container(request)
            async with container.session_factory() as db:
                storage_locations = await _get_storage_locations(db, tenant_id)
                logging.info(f"✅ Fetched {len(storage_locations)} storage locations: {storage_locations[:5] if len(storage_locations) > 5 else storage_locations}")
                unit_of_measures = await _get_unit_of_measures(db, tenant_id)
                logging.info(f"✅ Fetched {len(unit_of_measures)} UOMs: {unit_of_measures[:10] if len(unit_of_measures) > 10 else unit_of_measures}")
                supplier_names = list((await db.execute(
                    select(SupplierModel.name).where(
                        SupplierModel.tenant_id == tenant_id,
                        SupplierModel.is_deleted.is_(False),
                        SupplierModel.is_active.is_(True),
                    ).order_by(SupplierModel.name.asc())
                )).scalars().all())
                supplier_names = list(dict.fromkeys(name for name in supplier_names if name))
                tenant_currency = (await db.execute(select(TenantModel.currency_code).where(
                    TenantModel.id == tenant_id, TenantModel.is_deleted.is_(False),
                ))).scalar_one_or_none()
                if tenant_currency and tenant_currency.strip().upper() not in currency_codes:
                    currency_codes.append(tenant_currency.strip().upper())
                default_location = await _get_default_storage_location(db, tenant_id)
                if default_location:
                    logging.info(f"✅ Fetched default storage location: {default_location}")
                else:
                    logging.info("ℹ️  No default storage location configured")
        else:
            logging.info("⚠️  No authentication - template will not include dropdowns")
    except Exception as e:
        logging.exception("Could not load template master data", extra={"tenant_id": str(tenant_id)})
        raise HTTPException(status_code=503, detail="Could not load template master data. Please retry.") from e
    if format == "xlsx":
        try:
            logging.info("🔍 Starting Excel template generation...")
            from openpyxl.worksheet.datavalidation import DataValidation
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            logging.info("✅ openpyxl imports successful")
            wb = openpyxl.Workbook()
            logging.info(f"✅ Workbook created")
            
            # ═══════════════════════════════════════════════════════════════
            # 1. FIELD GUIDE SHEET (Primary documentation)
            # ═══════════════════════════════════════════════════════════════
            logging.info("📄 Creating Field Guide sheet...")
            ws_guide = wb.active
            if ws_guide is None:
                raise ValueError("Could not create active worksheet")
            ws_guide.title = "Field Guide"
            logging.info("✅ Field Guide sheet created")
            
            # Title
            ws_guide.append(["MedTrack ERP - Raw Material Field Guide"])
            ws_guide["A1"].font = Font(size=16, bold=True, color="FFFFFF")
            ws_guide["A1"].fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            ws_guide.merge_cells('A1:D1')
            
            ws_guide.append([])
            ws_guide.append(["This guide explains each field in the template with examples and best practices."])
            ws_guide["A3"].font = Font(size=10, italic=True, color="64748B")
            ws_guide.merge_cells('A3:D3')
            
            ws_guide.append([])
            
            # Header row for guide
            header_row = ws_guide.max_row + 1
            ws_guide.append(["Field Name", "Required?", "Purpose & Usage", "Example / Notes"])
            for cell in ws_guide[header_row]:
                cell.font = Font(bold=True, color="FFFFFF", size=11)
                cell.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            
            # Field definitions with detailed explanations
            field_guide = [
                ("Item Code", "Optional", 
                 "Unique identifier for this material. Use this when UPDATING existing materials. Leave blank for new materials - system will auto-generate.",
                 "Example: RM-STEEL-001\n✓ Use when updating\n✗ Leave blank for new"),
                
                ("Material Name", "REQUIRED", 
                 "The display name of the material. This appears throughout the system. Must be unique.",
                 "Example: Steel Sheet 10mm\nTip: Be descriptive and consistent"),
                
                ("Category", "REQUIRED", 
                 "Material category for grouping and reporting. System will auto-create if doesn't exist.",
                 "Example: Metals, Plastics, Chemicals\nTip: Use consistent naming"),
                
                ("Base Unit", "REQUIRED (Dropdown)", 
                 "Primary measurement unit for this material. Select from dropdown (auto-populated from master). Cannot be changed after creation.",
                 "Example: KG, METER, LITER, PCS\n⚠️ PROTECTED: Choose carefully!\nTip: Select from dropdown list\nNote: If you need a new unit, contact admin to add it to master"),
                
                ("Barcode", "Optional", 
                 "Barcode/SKU for scanner integration. Must be unique if provided.",
                 "Example: 1234567890123\nTip: Leave blank if no barcode"),
                
                ("Storage Location", "Optional (Dropdown)", 
                 "Where this material is stored in the warehouse. Select from dropdown (auto-populated from master). System will prefill if possible.",
                 "Example: Select from dropdown list\nTip: Choose from available locations\nNote: Dropdown populated from storage master"),
                
                ("Opening Stock", "Optional", 
                 "Initial quantity when first creating this material. Only used for NEW materials.",
                 "Example: 100\nNote: Ignored for updates"),
                
                ("Minimum Stock", "Optional", 
                 "Safety stock level. System alerts when stock falls below this.",
                 "Example: 50\nUse: Prevents stockouts"),
                
                ("Maximum Stock", "Optional", 
                 "Maximum stock to maintain. Helps with inventory planning.",
                 "Example: 500\nUse: Prevents overstocking"),
                
                ("Reorder Level", "Optional", 
                 "Trigger point for purchase requisition. When stock hits this, system creates PR.",
                 "Example: 100\nTip: Set above Min Stock"),
                
                ("Reorder Quantity", "Optional", 
                 "How much to order when reorder level is hit. Suggested quantity for PR.",
                 "Example: 200\nTip: Consider MOQ & lead time"),
                
                ("Track by Batch?", "Optional", 
                 "YES = Track materials by batch numbers (for traceability, expiry). NO = Track only total quantity.",
                 "YES: Medicines, food items, chemicals\nNO: Screws, nuts, generic metals\n⚠️ PROTECTED: Hard to change later!"),
                
                ("Track Expiry?", "Optional", 
                 "YES = Material has expiry date (requires batch tracking). NO = No expiry.",
                 "YES: Adhesives, chemicals with shelf life\nNO: Metals, plastic sheets\nNote: Auto-enables batch tracking"),
                
                ("Shelf Life", "Optional", 
                 "Number of days material is usable after production/receipt. Used with expiry tracking.",
                 "Example: 180 (days)\nUse: System calculates expiry date"),
                
                ("Track Traceability?", "Optional", 
                 "YES = Track each individual item by serial number. NO = Track by quantity only.",
                 "YES: High-value items, warranty items\nNO: Low-value bulk materials\n⚠️ PROTECTED: Choose carefully!"),
                
                ("Quality Check Required?", "Optional", 
                 "YES = Requires QC inspection before use. NO = Can use immediately after receipt.",
                 "YES: Critical materials, safety items\nNO: Low-risk materials"),
                
                ("Preferred Supplier", "Optional", 
                 "Default supplier name for this material. Used in purchase requisitions.",
                 "Example: Acme Steel Corp\nTip: Must match existing supplier"),
                
                ("Supplier Item Code", "Optional", 
                 "Enter the supplier catalog code for this material manually. This is not the supplier master code.",
                 "Example: AC-STEEL-500\nTip: Copy from supplier catalog"),
                
                ("Purchase Unit", "Optional", 
                 "Legacy purchase-unit metadata. Use Supplier UOM for supplier quotes; onboarding performs no unit conversion.",
                 "Use the configured base unit for automatic initial cost setup"),
                
                ("Lead Time (Days)", "Optional", 
                 "Number of days from PO to delivery. Used for MRP planning.",
                 "Example: 7\nTip: Get from supplier"),
                
                ("Minimum Order Quantity", "Optional", 
                 "Minimum quantity supplier will accept per order.",
                 "Example: 100\nUse: Ensures PO meets supplier minimums"),
                
                ("Length Unit", "Optional", 
                 "For materials sold by length (pipes, cables). Unit for length measurement.",
                 "Example: METER, FOOT\nUse: For cuttable materials only"),
                
                ("Can Be Cut?", "Optional", 
                 "YES = Material can be cut into smaller lengths (pipes, fabric). NO = Sold as whole units.",
                 "YES: Pipes, cables, fabric, sheets\nNO: Pre-cut items, finished parts"),
                
                ("Track Remaining Quantity?", "Optional", 
                 "YES = After cutting, track the unused remainder. NO = Remainder is scrapped.",
                 "YES: Expensive materials (minimize waste)\nNO: Cheap materials (not worth tracking)\nRequires 'Can Be Cut?' = YES"),
                
                ("Decimal Places", "Optional", 
                 "Number of decimal places for quantity precision. 0 = whole numbers only.",
                 "0: PCS (45 pieces)\n2: KG (12.50 kg)\n3: GRAM (0.125 gram)\nDefault: 2"),
                
                ("Reuse Remaining Material?", "Optional", 
                 "YES = Unused remainder goes back to stock. NO = Remainder is discarded.",
                 "YES: Expensive materials\nNO: Contaminated or low-value scraps\nRequires 'Track Remaining Quantity?' = YES"),
                
                # === SUPPLIER PRICING FIELDS (Phase 2) ===
                ("Supplier Name", "Optional",
                 "Select an active supplier name from the dropdown. You may type a new name; existing onboarding creation rules still apply.",
                 "Example: Acme Steel Corp\nTip: Leave blank if no supplier pricing\nNote: Used to create SupplierPriceAgreement"),
                
                ("Supplier Price", "Optional",
                 "Unit price of this material from the supplier (in supplier's currency).",
                 "Example: 150.50\nMust be > 0 if provided\nWill be stored in SupplierPriceAgreement (DRAFT status)"),
                
                ("Supplier Currency", "Optional",
                 "Select a suggested currency or enter a three-letter uppercase code. Currency is quote-specific; the supplier master has no currency default.",
                 "Example: USD, INR, EUR\nMust be a valid 3-letter code\nRequired if Supplier Price provided"),
                
                ("Supplier MOQ", "Optional",
                 "Minimum Order Quantity from this supplier (in supplier's UOM).",
                 "Example: 100\nMust be >= 0\nOptional but recommended"),
                
                ("Supplier UOM", "Optional",
                 "Select the quoted purchase unit from the tenant UOM master dropdown. The supplier master has no default UOM.",
                 "Example: TON (if base unit is KG)\nNo conversion is performed\nRequired when a supplier price is provided"),
                
                ("Effective From", "Optional",
                 "Start date for this supplier agreement (YYYY-MM-DD format).",
                 "Example: 2024-11-09\nFormat: YYYY-MM-DD\nIf blank, defaults to today"),
                
                ("Effective To", "Optional",
                 "End date for this supplier agreement (YYYY-MM-DD format). Leave blank for ongoing.",
                 "Example: 2025-11-09\nFormat: YYYY-MM-DD\nIf blank, agreement is ongoing"),
                
                ("Proposed Initial Cost", "Optional",
                 "Initial standard cost per base unit in tenant currency for NEW materials. Requires cost-setting permission; saved directly with audit history.",
                 "Example: 120.00\nMust be >= 0\nCreates an APPROVED direct revision and cost history\nIf blank, one unambiguous current supplier rate can initialize cost when currency and UOM match\nExisting material costs are preserved; explicit zero is supported"),
            ]
            
            thin_border = Border(
                left=Side(style='thin', color='D1D5DB'),
                right=Side(style='thin', color='D1D5DB'),
                top=Side(style='thin', color='D1D5DB'),
                bottom=Side(style='thin', color='D1D5DB')
            )
            
            for field_name, required, purpose, example in field_guide:
                row_num = ws_guide.max_row + 1
                ws_guide.append([field_name, required, purpose, example])
                
                # Styling
                ws_guide[f"A{row_num}"].font = Font(bold=True, size=10)
                ws_guide[f"A{row_num}"].alignment = Alignment(vertical="top", wrap_text=True)
                ws_guide[f"A{row_num}"].border = thin_border
                
                # Required column color coding
                req_cell = ws_guide[f"B{row_num}"]
                req_cell.alignment = Alignment(horizontal="center", vertical="top")
                req_cell.border = thin_border
                if "REQUIRED" in required:
                    req_cell.font = Font(bold=True, color="FFFFFF", size=10)
                    req_cell.fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
                elif "PROTECTED" in example:
                    req_cell.font = Font(bold=True, color="FFFFFF", size=9)
                    req_cell.fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
                else:
                    req_cell.font = Font(size=10, color="64748B")
                
                ws_guide[f"C{row_num}"].alignment = Alignment(vertical="top", wrap_text=True)
                ws_guide[f"C{row_num}"].border = thin_border
                ws_guide[f"C{row_num}"].font = Font(size=10)
                
                ws_guide[f"D{row_num}"].alignment = Alignment(vertical="top", wrap_text=True)
                ws_guide[f"D{row_num}"].border = thin_border
                ws_guide[f"D{row_num}"].font = Font(size=9, color="1E40AF")
            
            # Column widths
            ws_guide.column_dimensions['A'].width = 25
            ws_guide.column_dimensions['B'].width = 12
            ws_guide.column_dimensions['C'].width = 55
            ws_guide.column_dimensions['D'].width = 45
            
            # Add legend at bottom
            ws_guide.append([])
            legend_row = ws_guide.max_row + 1
            ws_guide.append(["LEGEND:"])
            ws_guide[f"A{legend_row}"].font = Font(bold=True, size=11)
            ws_guide.append(["", "REQUIRED", "Must be provided for all materials"])
            ws_guide[f"B{legend_row + 1}"].fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
            ws_guide[f"B{legend_row + 1}"].font = Font(color="FFFFFF", bold=True)
            ws_guide.append(["", "⚠️ PROTECTED", "Cannot be changed easily once set - choose carefully!"])
            ws_guide.append(["", "Optional", "Recommended but not mandatory"])
            
            # ═══════════════════════════════════════════════════════════════
            # 2. INSTRUCTIONS SHEET (Quick start)
            # ═══════════════════════════════════════════════════════════════
            logging.info("📄 Creating Quick Start sheet...")
            ws_inst = wb.create_sheet(title="Quick Start")
            logging.info("✅ Quick Start sheet created")
            
            # Title
            ws_inst.append(["MedTrack ERP - Quick Start Guide"])
            ws_inst["A1"].font = Font(size=14, bold=True, color="FFFFFF")
            ws_inst["A1"].fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            ws_inst.merge_cells('A1:B1')
            
            ws_inst.append([])
            ws_inst.append(["📋 STEPS TO IMPORT:"])
            ws_inst["A3"].font = Font(bold=True, size=11)
            
            steps = [
                "1. Read the 'Field Guide' tab to understand each field",
                "2. Go to 'Raw Materials' tab",
                "3. Delete the sample row (DUMMY-SAMPLE)",
                "4. Enter your material data (one row per material)",
                "5. Save the file",
                "6. Upload in MedTrack ERP (Inventory → Material Onboarding)",
            ]
            for step in steps:
                ws_inst.append([step])
                ws_inst[f"A{ws_inst.max_row}"].font = Font(size=10)
                
            ws_inst.append([])
            ws_inst.append(["⚠️ IMPORTANT RULES:"])
            ws_inst[f"A{ws_inst.max_row}"].font = Font(bold=True, size=11, color="DC2626")
            
            rules = [
                "✓ Material Name, Category, and Base Unit are REQUIRED",
                "✓ Item Code: Leave blank for NEW materials (auto-generated)",
                "✓ Item Code: Fill in when UPDATING existing materials",
                "✓ Do not change column headers",
                "✓ Use Yes/No dropdowns (not yes/no or Y/N)",
                "✓ Protected fields (Base Unit, Batch Tracking, Traceability) cannot be changed after creation",
                "✗ Do not delete any sheet tabs",
            ]
            for rule in rules:
                ws_inst.append([rule])
                
            ws_inst.append([])
            ws_inst.append(["💡 EXAMPLE:"])
            ws_inst[f"A{ws_inst.max_row}"].font = Font(bold=True, size=11, color="047857")
            
            ws_inst.append(["Material Name:", "Steel Sheet 10mm x 1000mm"])
            ws_inst.append(["Category:", "Metals"])
            ws_inst.append(["Base Unit:", "KG"])
            ws_inst.append(["Track by Batch?:", "No"])
            ws_inst.append(["Minimum Stock:", "50"])
            ws_inst.append(["Reorder Level:", "100"])
            
            ws_inst.column_dimensions['A'].width = 25
            ws_inst.column_dimensions['B'].width = 70
            
            # ═══════════════════════════════════════════════════════════════
            # 3. RAW MATERIALS SHEET (Data entry)
            # ═══════════════════════════════════════════════════════════════
            logging.info("📄 Creating Raw Materials sheet...")
            ws = wb.create_sheet(title="Raw Materials")
            logging.info("✅ Raw Materials sheet created")
            
            # Header styling
            ws.append(FRIENDLY_COLUMNS)
            header_font = Font(bold=True, color="FFFFFF", size=10)
            header_fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                
            # Sample row
            ws.append([
                "", "Sample Raw Material (Delete Me)", "Metals", "KG", "",
                "LOC-001", "100", "10", "500", "20", "50",
                "No", "No", "", "No", "No",
                "", "", "", "7", "",
                "", "No", "No", "2", "No",
                # === SUPPLIER PRICING FIELDS ===
                "", "", "", "", "", "", "", ""
            ])
            
            # Add note in sample row
            ws["B2"].comment = openpyxl.comments.Comment(
                "⚠️ DELETE THIS ROW before adding your data!\n\nThis is just a sample to show the format.",
                "MedTrack ERP"
            )
            
            ws.freeze_panes = "A2"
            
            # Auto-fit columns
            for col_idx, column in enumerate(FRIENDLY_COLUMNS, 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = max(len(column) + 4, 15)
                
            # Add data validation for Yes/No columns
            yes_no_dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
            yes_no_dv.error = 'Please select Yes or No from the dropdown'
            yes_no_dv.errorTitle = 'Invalid Value'
            ws.add_data_validation(yes_no_dv)
            
            for col_idx, column in enumerate(FRIENDLY_COLUMNS, 1):
                if column.endswith("?"):
                    col_letter = get_column_letter(col_idx)
                    yes_no_dv.add(f"{col_letter}2:{col_letter}1048576")
            
            # Named ranges avoid Excel's 255-character inline-list limit and
            # preserve commas/quotes in master values. Keep three visible tabs.
            from openpyxl.workbook.defined_name import DefinedName

            master_ws = wb.create_sheet(title="_Master Data")
            master_ws.sheet_state = "hidden"
            master_ws.append(["Storage Locations", "Units of Measure", "Suppliers", "Currencies"])
            for source_column, values in enumerate(
                (storage_locations, unit_of_measures, supplier_names, currency_codes), 1
            ):
                for index, value in enumerate(values, 2):
                    master_ws.cell(row=index, column=source_column, value=value).data_type = "s"

            for heading, values, source_column, range_name, allow_blank, allow_manual in (
                ("Storage Location", storage_locations, "A", "StorageLocationOptions", True, False),
                ("Base Unit", unit_of_measures, "B", "BaseUnitOptions", False, False),
                ("Supplier Name", supplier_names, "C", "SupplierNameOptions", True, True),
                ("Supplier Currency", currency_codes, "D", "SupplierCurrencyOptions", True, True),
                ("Supplier UOM", unit_of_measures, "B", "SupplierUOMOptions", True, False),
            ):
                if not values:
                    logging.warning("No active master values for template dropdown",
                                    extra={"tenant_id": str(tenant_id), "field": heading})
                    continue
                defined_name = DefinedName(
                    range_name,
                    attr_text=f"'_Master Data'!${source_column}$2:${source_column}${len(values) + 1}",
                )
                wb.defined_names.add(defined_name)
                validation = DataValidation(type="list", formula1=f"={range_name}",
                                            allow_blank=allow_blank, showDropDown=False)
                validation.error = f"Please select {heading} from the dropdown."
                validation.errorTitle = "Invalid master value"
                validation.showErrorMessage = not allow_manual
                ws.add_data_validation(validation)
                column = get_column_letter(FRIENDLY_COLUMNS.index(heading) + 1)
                validation.add(f"{column}2:{column}1048576")
            if default_location:
                column = get_column_letter(FRIENDLY_COLUMNS.index("Storage Location") + 1)
                ws[f"{column}2"] = default_location

            logging.info(f"✅ Excel template complete with {len(wb.sheetnames)} sheets: {wb.sheetnames}")
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            logging.info(f"✅ Template saved to buffer ({buf.getbuffer().nbytes} bytes)")
            return StreamingResponse(
                buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=material-onboarding-template.xlsx"},
            )
        except ImportError as e:
            logging.error(f"❌ Import error during Excel template generation: {e}")
            raise HTTPException(status_code=503, detail="Excel template generation is unavailable. Please retry.") from e
        except Exception as e:
            logging.error(f"❌ Unexpected error during Excel template generation: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Could not generate the Excel template. Please retry.") from e

    # CSV - Simple single file (matches the single data tab in Excel)
    logging.info("📄 Generating CSV template")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(FRIENDLY_COLUMNS)
    
    # Sample row for raw material (only raw materials for bulk upload)
    sample_location = default_location if default_location else "LOC-001"
    writer.writerow([
        "", "Sample Raw Material (Delete Me)", "Metals", "KG", "",
        sample_location, "100", "10", "500", "20", "50",
        "No", "No", "", "No", "No",
        "", "", "", "7", "",
        "", "No", "No", "2", "No",
        # === SUPPLIER PRICING FIELDS ===
        "", "", "", "", "", "", "", ""
    ])
    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.read().encode('utf-8-sig')),  # UTF-8 with BOM for Excel compatibility
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=material-onboarding-template.csv"},
    )


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file and create an onboarding session",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def create_session(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Parse the uploaded file and return session_id, column headers, and
    a JSON-stringified auto-suggested column mapping.
    """
    import json

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    headers, raw_rows = _parse_file(file_bytes, file.filename or "upload")

    if not headers:
        raise HTTPException(status_code=422, detail="No header row found in file")
    if not raw_rows:
        raise HTTPException(status_code=422, detail="No data rows found. Ensure row 1 is a header and data starts from row 2.")

    suggested = _suggest_mapping(headers)

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "session_id": session_id,
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "file_name": file.filename or "upload",
        "headers": headers,
        "raw_rows": raw_rows,
        "mapping": {},
        "rows": [],
        "protected_confirmed": False,
        "status": "uploaded",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "session_id": session_id,
        "headers": headers,
        "mapping": json.dumps(suggested),
    }


@router.post(
    "/sessions/{session_id}/validate",
    summary="Apply column mapping and validate all rows",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def validate_session(
    session_id: str,
    body: ValidateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Apply column mapping, run validation rules, and classify each row."""
    session = _get_session(session_id, tenant_id)

    container = get_container(request)
    existing_codes: Dict[str, Dict[str, Any]] = {}
    try:
        async with container.session_factory() as db:
            result = await db.execute(
                select(
                    MaterialModel.code,
                    MaterialModel.item_code,
                    MaterialModel.name,
                    MaterialModel.material_type,
                    MaterialModel.is_batch_tracked,
                    MaterialModel.is_serialized,
                    MaterialModel.safety_stock,
                    MaterialModel.reorder_level,
                ).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
            for row in result.fetchall():
                rec = dict(row._mapping)
                key = (row.item_code or row.code or "").upper()
                if key:
                    existing_codes[key] = rec
                name_key = (row.name or "").upper()
                if name_key:
                    existing_codes[name_key] = rec
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to load existing materials for validation") from exc

    mapping = body.mapping
    processed_rows = []
    seen_material_keys: set[str] = set()
    for i, raw_row in enumerate(session["raw_rows"], start=2):
        data = _apply_mapping(raw_row, mapping)
        
        # Silently ignore the dummy sample row if the user forgot to delete it
        if data.get("item_code") == "DUMMY-SAMPLE" or data.get("material_name") == "Sample Material (Delete Me)":
            continue
            
        row_id = str(uuid.uuid4())
        classification, row_status, issues, protected_changes = _validate_row(data, i, existing_codes)
        item_key = str(data.get("item_code", "")).strip().upper()
        name_key = str(data.get("material_name", "")).strip().upper()
        duplicate_material = (
            (item_key and item_key in seen_material_keys)
            or (name_key and name_key in seen_material_keys)
        )
        if duplicate_material and row_status != "error":
            classification = "update"
        elif classification == "new":
            if item_key:
                seen_material_keys.add(item_key)
                existing_codes[item_key] = {"code": item_key, "name": name_key}
            if name_key:
                seen_material_keys.add(name_key)
                existing_codes[name_key] = {"code": item_key, "name": name_key}
        
        # === EXTRACT SUPPLIER PRICING DETAILS (Phase 2) ===
        supplier_pricing = None
        if data.get("supplier_name") and data.get("supplier_price"):
            try:
                supplier_pricing = {
                    "supplier_name": data.get("supplier_name", "").strip(),
                    "supplier_price": float(str(data.get("supplier_price", "0")).replace(",", "")),
                    "supplier_currency": data.get("supplier_currency", "").strip(),
                    "supplier_moq": float(str(data.get("supplier_moq", "0")).replace(",", "")) if data.get("supplier_moq") else None,
                    "supplier_uom": data.get("supplier_uom", "").strip() or None,
                    "effective_from_date": data.get("effective_from_date", "").strip() or None,
                    "effective_to_date": data.get("effective_to_date", "").strip() or None,
                    "proposed_initial_cost": float(str(data.get("proposed_initial_cost", "0")).replace(",", "")) if data.get("proposed_initial_cost") else None,
                }
            except (ValueError, TypeError):
                supplier_pricing = None
        
        processed_rows.append({
            "id": row_id,
            "row_number": i,
            "classification": classification,
            "status": row_status,
            "data": data,
            "issues": issues,
            "protected_changes": protected_changes,
            "supplier_pricing": supplier_pricing,  # Extracted for easier frontend display
            "pricing_status": (
                "supplier_draft_and_initial_cost_to_evaluate"
                if data.get("supplier_price") and data.get("proposed_initial_cost")
                else "supplier_draft_and_initial_cost_to_evaluate"
                if data.get("supplier_price")
                else "initial_cost_to_evaluate"
                if data.get("proposed_initial_cost")
                else "not_configured"
            ),
        })

    session["mapping"] = mapping
    session["rows"] = processed_rows
    session["status"] = "validated"

    # If no rows remain after filtering dummy data, return a helpful message
    if len(processed_rows) == 0:
        return {
            "validated": 0,
            "warning": "No valid data rows found. The uploaded file appears to contain only sample/dummy data. Please add your material data to the template before uploading."
        }

    return {"validated": len(processed_rows)}


@router.get(
    "/sessions/{session_id}/preview",
    summary="Get validation preview for the session",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def get_preview(
    session_id: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
):
    """Simulate the same row savepoints/constraints as execution, then roll back."""
    session = _get_session(session_id, tenant_id)
    if session.get("status") != "validated":
        raise HTTPException(status_code=400, detail="Validate the session first")
    outcome = await execute_session(session_id, ExecuteRequest(dry_run=True), request, tenant_id, user_id, role)
    rows = session.get("rows", [])
    return {
        "summary": {
            "total_rows": len(rows), "new": outcome["created"], "update": outcome["updated"],
            "skip": outcome["skipped"], "errors": outcome["rejected"],
            "warnings": len(outcome["warnings"]),
            "supplier_pricing": outcome["supplier_pricing_created"],
        },
        "rows": rows, "warnings": outcome["warnings"],
        "error_messages": outcome["error_messages"], "cost_outcomes": outcome["cost_outcomes"],
    }


@router.post(
    "/sessions/{session_id}/confirm-protected",
    summary="Confirm that protected field changes are intentional",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def confirm_protected(
    session_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    session = _get_session(session_id, tenant_id)
    session["protected_confirmed"] = True
    return {"confirmed": True}


@router.post(
    "/sessions/{session_id}/execute",
    summary="Execute the import (create/update materials)",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def execute_session(
    session_id: str,
    body: ExecuteRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    role: str = Depends(get_current_role),
):
    """
    Commit the onboarding session. With dry_run=True runs all logic without
    writing to the database.
    """
    session = _get_session(session_id, tenant_id)
    rows = session.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="Session has not been validated yet.")

    # Revalidate row values on every execution, including corrected rows and dry runs.
    for row in rows:
        _, row_status, issues, _ = _validate_row(row["data"], row["row_number"], {})
        if row_status == "error":
            row["status"] = "error"
            row["issues"] = issues
    can_set_cost = True
    try:
        await require_permission("procurement_pricing:cost:propose")(request, role, tenant_id)
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        can_set_cost = False
    cost_outcomes: List[Dict[str, Any]] = []
    warnings: List[str] = []
    grouped_rows: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped_rows.setdefault(str(row["data"].get("material_name", "")).strip().upper(), []).append(row)
    failed_groups: set[str] = set()
    new_materials: Dict[str, uuid.UUID] = {}

    names_by_code: Dict[str, set[str]] = {}
    codes_by_name: Dict[str, set[str]] = {}
    for row in rows:
        data = row["data"]
        code = str(data.get("item_code", "")).strip().upper()
        name = str(data.get("material_name", "")).strip().upper()
        if code:
            names_by_code.setdefault(code, set()).add(name)
            codes_by_name.setdefault(name, set()).add(code)
    for row in rows:
        code = str(row["data"].get("item_code", "")).strip().upper()
        name = str(row["data"].get("material_name", "")).strip().upper()
        if len(names_by_code.get(code, set())) > 1 or len(codes_by_name.get(name, set())) > 1:
            row["status"] = "error"
            row["classification"] = "skip"
            issue = {"field": "item_code", "severity": "error", "message": "Conflicting material code/name identities in this upload"}
            if issue not in row["issues"]:
                row["issues"].append(issue)

    actionable = [r for r in rows if r["classification"] in ("new", "update") and r["status"] != "error"]

    actionable.sort(key=lambda row: (
        str(row["data"].get("material_name", "")).strip().upper(),
        not bool(row["data"].get("item_code")), row["row_number"],
    ))

    created = updated = skipped = errors = 0
    rejected = sum(1 for r in rows if r["status"] == "error")
    supplier_agreements_created = 0
    cost_revisions_created = 0
    error_messages: List[str] = [
        f"Row {row['row_number']}: {issue['message']}"
        for row in rows if row["status"] == "error"
        for issue in row["issues"] if issue["severity"] == "error"
    ]
    skip_details: List[Dict[str, Any]] = []  # Track skip reasons with row details

    container = get_container(request)

    # Fetch UOM and category lookups, auto-create missing, and create materials all in ONE atomic transaction
    uom_map: Dict[str, uuid.UUID] = {}
    cat_map: Dict[str, uuid.UUID] = {}
    existing_map: Dict[str, MaterialModel] = {}

    try:
        async with container.session_factory() as db:
            # Phase 1: Load existing master data
            uom_result = await db.execute(
                select(UnitOfMeasureModel.code, UnitOfMeasureModel.id).where(
                    UnitOfMeasureModel.tenant_id == tenant_id,
                    UnitOfMeasureModel.is_deleted.is_(False),
                    UnitOfMeasureModel.is_active.is_(True),
                )
            )
            for r in uom_result:
                code = r.code.strip().upper()
                if code in uom_map and uom_map[code] != r.id:
                    raise ValueError(f"Ambiguous configured UOM: {code}")
                uom_map[code] = r.id

            cat_result = await db.execute(
                select(MaterialCategoryModel.name, MaterialCategoryModel.id).where(
                    MaterialCategoryModel.tenant_id == tenant_id,
                    MaterialCategoryModel.is_deleted.is_(False),
                )
            )
            for r in cat_result:
                cat_map[r.name.upper()] = r.id

            mat_result = await db.execute(
                select(MaterialModel).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
            for mat in mat_result.scalars():
                key = (mat.item_code or mat.code or "").upper()
                if key:
                    existing_map[key] = mat
                name_key = (mat.name or "").upper()
                if name_key:
                    existing_map[name_key] = mat

            original_material_ids = {mat.id for mat in existing_map.values()}
            costing_currency = (await db.execute(select(TenantModel.currency_code).where(
                TenantModel.id == tenant_id, TenantModel.is_deleted.is_(False),
            ))).scalar_one_or_none()

            # Phase 2: Auto-create missing UOMs (SAME TRANSACTION)
            for row in actionable:
                data = row["data"]
                uom_code = str(data.get("uom", "")).strip().upper()
                if uom_code and uom_code not in uom_map:
                    new_uom = UnitOfMeasureModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        code=uom_code,
                        name=uom_code,
                        precision=2,
                        is_active=True,
                        is_deleted=False,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.add(new_uom)
                    uom_map[uom_code] = new_uom.id

            # Phase 3: Auto-create missing categories (SAME TRANSACTION)
            for row in actionable:
                data = row["data"]
                cat_name = str(data.get("material_category", "")).strip().upper()
                if cat_name and cat_name not in cat_map:
                    new_cat = MaterialCategoryModel(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        name=cat_name,
                        code_prefix=cat_name[:3] if len(cat_name) >= 3 else cat_name,
                        description=None,
                        is_active=True,
                        is_deleted=False,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.add(new_cat)
                    cat_map[cat_name] = new_cat.id

            # Flush master data to prepare IDs
            await db.flush()

            # Phase 4: Create/Update materials (SAME TRANSACTION, after master data flushed)
            item_code_service = ItemCodeService(db)
            logger = logging.getLogger(__name__)

            for row in actionable:
                row_transaction = await db.begin_nested()
                row_counts = (
                    created,
                    updated,
                    supplier_agreements_created,
                    cost_revisions_created,
                )
                try:
                    data = row["data"]
                    name = str(data.get("material_name", "")).strip()
                    item_code = str(data.get("item_code", "")).strip()
                    uom_code = str(data.get("uom", "")).strip().upper()
                    cat_name = str(data.get("material_category", "")).strip().upper()

                    uom_id = uom_map.get(uom_code)
                    cat_id = cat_map.get(cat_name)

                    def _f(key: str) -> str | None:
                        val = data.get(key, "").strip()
                        return val if val else None

                    def _bool_val(val: str) -> bool:
                        return str(val).lower() in ("true", "1", "yes")

                    def _float_f(key: str) -> float | None:
                        try:
                            val = float(data.get(key, 0) or 0)
                            return val if val > 0 else None
                        except (TypeError, ValueError):
                            return None

                    def _int_f(key: str) -> int | None:
                        try:
                            val = int(data.get(key, 0) or 0)
                            return val if val > 0 else None
                        except (TypeError, ValueError):
                            return None

                    code_match = existing_map.get(item_code.upper()) if item_code else None
                    name_match = existing_map.get(name.upper())
                    if ((code_match and code_match.name.upper() != name.upper())
                        or (item_code and name_match and code_match is not name_match)):
                        raise ValueError("Material code/name identity conflict")
                    group_codes = {str(r["data"].get("item_code", "")).strip().upper()
                                   for r in grouped_rows[name.upper()] if r["data"].get("item_code")}
                    if len(group_codes) > 1:
                        raise ValueError("Conflicting material codes for the same material name")
                    existing = code_match or name_match
                    if existing:
                        # Serialize agreement checks/writes for this material.
                        existing = (await db.execute(select(MaterialModel).where(
                            MaterialModel.id == existing.id, MaterialModel.tenant_id == tenant_id,
                            MaterialModel.is_deleted.is_(False),
                        ).with_for_update().execution_options(populate_existing=True))).scalar_one()
                        if any(row.get("protected_changes") for row in grouped_rows[name.upper()]) and not session["protected_confirmed"] and not body.dry_run:
                            raise ValueError("Protected material changes require confirmation")
                    if not existing:
                        # Create
                        # Parse opening_stock for new materials
                        opening_stock_raw = str(data.get("opening_stock", "")).strip()
                        opening_stock_value: float = 0
                        if opening_stock_raw:
                            try:
                                opening_stock_value = float(opening_stock_raw.replace(",", ""))
                                if opening_stock_value < 0:
                                    opening_stock_value = 0
                            except (ValueError, TypeError):
                                opening_stock_value = 0

                        # Determine material_type for prefix resolution
                        material_type = "raw"  # Enforced for Raw Material upload

                        # Generate item code using Number Series Engine (Req 7.3, 14.2)
                        generated_code = ""
                        if item_code:
                            # CSV contains an item_code — respect manual_override policy
                            try:
                                result = await item_code_service.validate_manual_code_with_policy(
                                    tenant_id=tenant_id,
                                    entity_type="material",
                                    code=item_code,
                                    user_is_admin=False,  # Bulk upload doesn't assume admin
                                    sub_type=material_type,
                                    entity_name=name,
                                    user_id=user_id,
                                )
                                generated_code = result.code
                            except ValueError as code_err:
                                # If manual code is rejected (e.g. duplicate, format error),
                                # log warning and auto-generate instead
                                logger.warning(
                                    "Manual code '%s' rejected for row %d: %s. Auto-generating.",
                                    item_code, row["row_number"], code_err,
                                )
                                generated_code = await item_code_service.generate_for_entity(
                                    tenant_id=tenant_id,
                                    entity_type="material",
                                    sub_type=material_type,
                                    entity_name=name,
                                    user_id=user_id,
                                )
                        else:
                            # No item_code in CSV — auto-generate using Number Series Engine
                            generated_code = await item_code_service.generate_for_entity(
                                tenant_id=tenant_id,
                                entity_type="material",
                                sub_type=material_type,
                                entity_name=name,
                                user_id=user_id,
                            )

                        mat = MaterialModel(
                            id=uuid.uuid4(),
                            tenant_id=tenant_id,
                            code=generated_code,
                            name=name,
                            base_unit_id=uom_id,
                            category_id=cat_id,
                            is_batch_tracked=_bool_val(data.get("batch_tracking_enabled", "false")),
                            is_serialized=_bool_val(data.get("traceability_enabled", "false")),
                            qc_required_flag=_bool_val(data.get("qc_required", "false")),
                            reorder_level=_float_f("reorder_level"),
                            safety_stock=_float_f("min_stock"),
                            lead_time_days=_int_f("lead_time"),
                            length_uom=_f("length_uom"),
                            supplier_item_code=_f("supplier_item_code"),
                            current_cost=0,
                            current_stock=opening_stock_value,
                            reserved_stock=0,
                            is_active=True,
                            is_deleted=False,
                            created_by=user_id,
                            updated_by=user_id,
                            code_locked=True,
                        )
                        db.add(mat)

                        # Flush to ensure material exists in DB before creating dependent transaction
                        await db.flush()

                        # If opening_stock > 0, create Stock In transaction + StockLevelModel entry
                        if opening_stock_value > 0:
                            # Get default warehouse location
                            warehouse_location_id = await _get_default_warehouse_location(db, tenant_id)

                            # Create the transaction record
                            tx = InventoryTransactionModel(
                                id=uuid.uuid4(),
                                tenant_id=tenant_id,
                                material_id=mat.id,
                                transaction_type="in",
                                quantity=opening_stock_value,
                                reference_type="onboarding_opening_balance",
                                remarks="Opening balance via onboarding import",
                                created_by=user_id,
                                created_at=datetime.now(timezone.utc),
                                updated_at=datetime.now(timezone.utc),
                            )
                            db.add(tx)

                            # Create StockLevelModel entry at warehouse location (critical for stock-by-location visibility)
                            if warehouse_location_id:
                                stock_level = StockLevelModel(
                                    id=uuid.uuid4(),
                                    tenant_id=tenant_id,
                                    material_id=mat.id,
                                    location_id=warehouse_location_id,
                                    stock_status="available",
                                    quantity=opening_stock_value,
                                    is_deleted=False,
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc),
                                )
                                db.add(stock_level)

                        created += 1
                    else:
                        # Update
                        if session["protected_confirmed"]:
                            # material_type cannot be changed by raw material import
                            existing.is_batch_tracked = _bool_val(data.get("batch_tracking_enabled", str(existing.is_batch_tracked)))
                            existing.is_serialized = _bool_val(data.get("traceability_enabled", str(existing.is_serialized)))
                            base_unit = uom_id or existing.base_unit_id
                            if base_unit:
                                existing.base_unit_id = base_unit
                        category = cat_id or existing.category_id
                        if category:
                            existing.category_id = category
                        reorder = _float_f("reorder_level")
                        if reorder:
                            existing.reorder_level = reorder
                        safety = _float_f("min_stock")
                        if safety:
                            existing.safety_stock = safety
                        lead = _int_f("lead_time")
                        if lead:
                            existing.lead_time_days = lead
                        length = _f("length_uom")
                        if length:
                            existing.length_uom = length
                        supplier_item_code = _f("supplier_item_code")
                        if supplier_item_code:
                            existing.supplier_item_code = supplier_item_code
                        existing.updated_by = user_id
                        updated += 1

                    # Pricing records are independent of material creation and of each other.
                    supplier_name_raw = str(data.get("supplier_name", "")).strip()
                    supplier_price_str = str(data.get("supplier_price", "")).strip()
                    supplier_currency = str(data.get("supplier_currency", "")).strip()
                    supplier_uom_str = str(data.get("supplier_uom", "")).strip()
                    effective_from_str = str(data.get("effective_from_date", "")).strip()
                    effective_to_str = str(data.get("effective_to_date", "")).strip()
                    proposed_cost_str = str(data.get("proposed_initial_cost", "")).strip()

                    material = existing if existing else mat
                    material_id = material.id

                    if supplier_name_raw and supplier_price_str and supplier_currency:
                        from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
                            SupplierPriceAgreementModel,
                        )

                        supplier_result = await db.execute(
                            select(SupplierModel).where(
                                SupplierModel.tenant_id == tenant_id,
                                func.lower(SupplierModel.name) == supplier_name_raw.lower(),
                                SupplierModel.is_deleted.is_(False),
                            )
                        )
                        supplier = supplier_result.scalars().first()

                        if not supplier:
                            supplier_code = f"SUP-{uuid.uuid4().hex[:8].upper()}"
                            supplier = SupplierModel(
                                id=uuid.uuid4(),
                                tenant_id=tenant_id,
                                code=supplier_code,
                                name=supplier_name_raw,
                                is_active=True,
                                is_deleted=False,
                                created_by=user_id,
                                updated_by=user_id,
                            )
                            db.add(supplier)
                            await db.flush()

                        supplier_uom_code = supplier_uom_str.upper()
                        supplier_uom_id = uom_map.get(supplier_uom_code)
                        if supplier_uom_id is None:
                            raise ValueError(f"Supplier UOM '{supplier_uom_str}' is not configured and active for this tenant")

                        supplier_price = Decimal(supplier_price_str.replace(",", ""))
                        supplier_moq_str = str(data.get("supplier_moq", "")).strip()
                        supplier_moq = (
                            Decimal(supplier_moq_str.replace(",", ""))
                            if supplier_moq_str
                            else None
                        )
                        effective_from_date, effective_to_date = agreement_dates(
                            data, datetime.now(timezone.utc).date()
                        )

                        overlap_stmt = select(SupplierPriceAgreementModel).where(
                            SupplierPriceAgreementModel.tenant_id == tenant_id,
                            SupplierPriceAgreementModel.supplier_id == supplier.id,
                            SupplierPriceAgreementModel.material_id == material_id,
                            SupplierPriceAgreementModel.status != "CANCELLED",
                            SupplierPriceAgreementModel.is_deleted.is_(False),
                            SupplierPriceAgreementModel.effective_from
                            <= (effective_to_date or datetime.max.replace(tzinfo=timezone.utc)),
                            or_(
                                SupplierPriceAgreementModel.effective_to.is_(None),
                                SupplierPriceAgreementModel.effective_to >= effective_from_date,
                            ),
                        )
                        overlaps = (await db.execute(overlap_stmt)).scalars().all()
                        overlap = overlaps[0] if overlaps else None
                        if overlaps:
                            same_terms = len(overlaps) == 1 and (
                                Decimal(str(overlap.base_price)) == supplier_price
                                and str(overlap.currency_code).upper() == supplier_currency.upper()
                                and overlap.purchase_uom_id == supplier_uom_id
                                and overlap.minimum_order_quantity == supplier_moq
                                and (not effective_from_str or overlap.effective_from.date() == effective_from_date.date())
                                and ((overlap.effective_to is None and effective_to_date is None)
                                     or (overlap.effective_to is not None and effective_to_date is not None
                                         and overlap.effective_to.date() == effective_to_date.date()))
                                and not overlap.quantity_tier
                            )
                            if not same_terms:
                                raise ValueError("Supplier agreement overlaps existing pricing with changed price, UOM, MOQ, dates or tiers; review the existing agreement")
                            skip_details.append({
                                "row": row["row_number"], "material_name": name,
                                "item_code": item_code or material.code,
                                "supplier_name": supplier_name_raw,
                                "reason": "Identical supplier agreement already exists",
                                "details": f"{supplier_currency} {supplier_price}; all agreement terms unchanged",
                            })

                        # Only insert a new agreement when no overlapping agreement exists
                        if overlap is None:
                            db.add(
                                SupplierPriceAgreementModel(
                                    id=uuid.uuid4(),
                                    tenant_id=tenant_id,
                                    supplier_id=supplier.id,
                                    material_id=material_id,
                                    status="DRAFT",
                                    base_price=supplier_price,
                                    currency_code=supplier_currency.upper(),
                                    purchase_uom_id=supplier_uom_id,
                                    minimum_order_quantity=supplier_moq,
                                    quantity_tier=None,
                                    effective_from=effective_from_date,
                                    effective_to=effective_to_date,
                                    notes="Imported from material onboarding",
                                    is_deleted=False,
                                    created_by=user_id,
                                    updated_by=user_id,
                                )
                            )
                            supplier_agreements_created += 1

                    # Cost is resolved after ALL supplier rows have succeeded.
                    # Existing pending revisions/history are preserved; re-import creates none.
                    await row_transaction.commit()
                    existing_map[(material.code or "").upper()] = material
                    if item_code:
                        existing_map[item_code.upper()] = material
                    existing_map[name.upper()] = material
                    if material.id not in original_material_ids:
                        new_materials[name.upper()] = material.id
                    elif proposed_cost_str:
                        warnings.append(f"Row {row['row_number']}: existing material standard cost and pending revisions preserved; proposed initial cost ignored.")
                    
                except Exception as exc:
                    await row_transaction.rollback()
                    (
                        created,
                        updated,
                        supplier_agreements_created,
                        cost_revisions_created,
                    ) = row_counts
                    failed_groups.add(name.upper())
                    errors += 1
                    rejected += 1
                    error_messages.append(f"Row {row['row_number']}: {exc}")

            for group_name, material_id in new_materials.items():
                material = (await db.execute(select(MaterialModel).where(
                    MaterialModel.id == material_id, MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                ))).scalar_one()
                group = grouped_rows[group_name]
                plan = plan_initial_cost(
                    group, base_uom_id=material.base_unit_id, uom_ids=uom_map,
                    currency_code=costing_currency, can_set_cost=can_set_cost,
                )
                if group_name in failed_groups:
                    message = "Standard cost not initialized: another supplier row failed."
                    amount = None
                else:
                    message, amount = plan.message, plan.cost
                if amount is not None:
                    async with db.begin_nested():
                        result = await DirectStandardCostHandler(db).handle(
                            tenant_id=tenant_id, material_id=material_id, user_id=user_id,
                            new_cost=amount, expected_current_cost=Decimal("0"), initial_only=True,
                        )
                    cost_revisions_created += 1
                else:
                    warnings.append(f"{material.name}: {message}")
                cost_outcomes.append({"material_id": str(material_id), "material_name": material.name,
                                      "status": "CONFIGURED" if amount is not None else "NOT_CONFIGURED",
                                      "standard_cost": str(amount) if amount is not None else None,
                                      "message": message})

            skipped = sum(
                1 for r in rows
                if r["classification"] == "skip" and r["status"] != "error"
            )

            # Single atomic commit for entire transaction
            try:
                if body.dry_run:
                    await db.rollback()
                else:
                    await db.commit()
            except Exception as exc:
                await db.rollback()
                raise HTTPException(status_code=500, detail=f"Commit failed: {exc}")

    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Onboarding execution failed: {str(exc)}")
    finally:
        # Clean up session after execution (success or failure)
        if not body.dry_run:
            _sessions.pop(session_id, None)

    return {
        "dry_run": body.dry_run,
        "warnings": warnings,
        "cost_outcomes": cost_outcomes,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "errors": errors,
        "error_messages": error_messages,
        "skip_details": skip_details,  # Include skip details with reasons
        # === SUPPLIER PRICING SUMMARY ===
        "supplier_pricing_created": {
            "supplier_agreements_draft": supplier_agreements_created,
            "cost_revisions_pending": 0,
            "standard_costs_initialized": cost_revisions_created,
        },
    }


@router.patch(
    "/rows/{row_id}",
    summary="Correct a specific row's field values",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_row(
    row_id: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update a specific row's data fields and re-validate it."""
    body = await request.json()

    # Find the row across all sessions belonging to this tenant
    target_session = None
    target_row = None
    for sess in _sessions.values():
        if sess["tenant_id"] != str(tenant_id):
            continue
        for row in sess.get("rows", []):
            if row["id"] == row_id:
                target_session = sess
                target_row = row
                break
        if target_row:
            break

    if not target_row:
        raise HTTPException(status_code=404, detail="Row not found or session expired")

    # Apply updates
    for field, value in body.items():
        target_row["data"][field] = value

    # Re-validate the row
    existing_codes: Dict[str, Dict[str, Any]] = {}
    try:
        container = get_container(request)
        async with container.session_factory() as db:
            result = await db.execute(
                select(
                    MaterialModel.code, MaterialModel.item_code, MaterialModel.name,
                    MaterialModel.material_type, MaterialModel.is_batch_tracked,
                    MaterialModel.is_serialized, MaterialModel.safety_stock, MaterialModel.reorder_level,
                ).where(
                    MaterialModel.tenant_id == tenant_id,
                    MaterialModel.is_deleted.is_(False),
                )
            )
            for row in result.fetchall():
                rec = dict(row._mapping)
                key = (row.item_code or row.code or "").upper()
                if key:
                    existing_codes[key] = rec
    except Exception:
        pass

    classification, row_status, issues, protected_changes = _validate_row(
        target_row["data"], target_row["row_number"], existing_codes
    )
    target_row["classification"] = classification
    target_row["status"] = row_status
    target_row["issues"] = issues
    target_row["protected_changes"] = protected_changes

    return target_row


@router.get(
    "/sessions/{session_id}/validation-report",
    summary="Download a CSV validation report for the session",
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def validation_report(
    session_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    session = _get_session(session_id, tenant_id)
    rows = session.get("rows", [])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["row_number", "classification", "status", "material_name", "item_code", "uom", "issues"])
    for row in rows:
        data = row.get("data", {})
        
        def friendly(f: str) -> str:
            return TECHNICAL_TO_FRIENDLY.get(f, f)
            
        issues_text = "; ".join(f"[{i['severity']}] {friendly(i['field'])}: {i['message']}" for i in row.get("issues", []))
        writer.writerow([
            row["row_number"],
            row["classification"],
            row["status"],
            data.get("material_name", ""),
            data.get("item_code", ""),
            data.get("uom", ""),
            issues_text,
        ])

    buf.seek(0)
    return StreamingResponse(
        io.BytesIO(buf.read().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=material-onboarding-validation-{session_id}.csv"},
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_default_warehouse_location(
    db_session,
    tenant_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    """Get the first active warehouse location for the tenant."""
    stmt = (
        select(LocationModel.id)
        .where(
            LocationModel.tenant_id == tenant_id,
            LocationModel.type == "warehouse",
            LocationModel.is_deleted.is_(False),
            LocationModel.is_active.is_(True),
        )
        .limit(1)
    )
    result = await db_session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


def _get_session(session_id: str, tenant_id: uuid.UUID) -> Dict[str, Any]:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Onboarding session not found or expired")
    if session["tenant_id"] != str(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return session
