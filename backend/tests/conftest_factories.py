"""
Factory functions for creating test data.
Use these to create consistent, reusable test objects.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.infrastructure.persistence.database import Base


# ───────────────────────────────────────────────────────────────────────────────
# UUID & ID Generators
# ───────────────────────────────────────────────────────────────────────────────

def generate_uuid() -> str:
    """Generate a random UUID as string."""
    return str(uuid.uuid4())


def generate_test_id(prefix: str = "") -> str:
    """Generate a test ID with optional prefix."""
    if prefix:
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
    return uuid.uuid4().hex[:12]


# ───────────────────────────────────────────────────────────────────────────────
# User & Auth Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_user_data(
    email: str = "test@example.com",
    password_hash: Optional[str] = None,
    role: str = "operator",
    is_active: bool = True,
    is_superuser: bool = False,
) -> Dict[str, Any]:
    """Create test user data."""
    from backend.app.infrastructure.security.auth import hash_password
    
    return {
        "id": uuid.uuid4(),
        "email": email,
        "password_hash": password_hash or hash_password("TestPassword123!"),
        "role": role,
        "is_active": is_active,
        "is_superuser": is_superuser,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


# ───────────────────────────────────────────────────────────────────────────────
# Product Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_product_template_payload(
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: str = "Test product template",
    attributes: Optional[List[Dict[str, Any]]] = None,
    is_template: bool = True,
) -> Dict[str, Any]:
    """Create a product template payload for API testing."""
    if attributes is None:
        attributes = [
            {
                "name": "Color",
                "data_type": "text",
                "is_required": True,
                "allowed_values": ["Red", "Blue", "Green"],
            },
            {
                "name": "Size",
                "data_type": "text",
                "is_required": True,
                "allowed_values": ["S", "M", "L", "XL"],
            },
        ]
    
    return {
        "name": name or f"Template-{generate_test_id()}",
        "code": code or f"PROD-{generate_test_id()}",
        "description": description,
        "attributes": attributes,
        "is_template": is_template,
    }


def create_product_variant_payload(
    template_id: str,
    variant_key: Optional[str] = None,
    sku: Optional[str] = None,
    attributes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a product variant payload for API testing."""
    if attributes is None:
        attributes = {
            "Color": "Red",
            "Size": "M",
        }
    
    return {
        "template_id": template_id,
        "variant_key": variant_key or f"VAR-{generate_test_id()}",
        "sku": sku or f"SKU-{generate_test_id()}",
        "attributes": attributes,
    }


# ───────────────────────────────────────────────────────────────────────────────
# BOM Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_bom_payload(
    product_id: Optional[str] = None,
    version: str = "v1.0",
    valid_from: Optional[str] = None,
    valid_to: Optional[str] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
    is_template: bool = True,
) -> Dict[str, Any]:
    """Create a BOM creation payload."""
    if product_id is None:
        product_id = str(uuid.uuid4())
    
    if valid_from is None:
        valid_from = datetime.utcnow().isoformat()
    
    return {
        "version": version,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "template_id": product_id if is_template else None,
        "variant_id": None if is_template else product_id,
        "lines": lines or [],
    }


def create_bom_line_payload(
    material_id: Optional[str] = None,
    quantity: float = 1.0,
    scrap_percentage: float = 0.0,
    template_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a BOM line item payload."""
    return {
        "material_id": material_id or str(uuid.uuid4()),
        "template_id": template_id,
        "quantity": quantity,
        "scrap_percentage": scrap_percentage,
    }


def create_bom_with_lines_payload(
    product_id: str,
    num_lines: int = 2,
    version: str = "v1.0",
) -> Dict[str, Any]:
    """Create a BOM payload with sample line items."""
    lines = [
        create_bom_line_payload(
            material_id=str(uuid.uuid4()),
            quantity=float(i + 1),
        )
        for i in range(num_lines)
    ]
    return create_bom_payload(
        product_id=product_id,
        version=version,
        lines=lines,
    )


# ───────────────────────────────────────────────────────────────────────────────
# Material Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_material_payload(
    code: Optional[str] = None,
    name: Optional[str] = None,
    description: str = "Test material",
    unit_of_measure: str = "KG",
    unit_cost: float = 100.00,
) -> Dict[str, Any]:
    """Create a material payload for API testing."""
    return {
        "code": code or f"MAT-{generate_test_id()}",
        "name": name or f"Material-{generate_test_id()}",
        "description": description,
        "unit_of_measure": unit_of_measure,
        "unit_cost": unit_cost,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Operation Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_operation_payload(
    code: Optional[str] = None,
    name: Optional[str] = None,
    description: str = "Test operation",
    process_type: str = "assembly",
    estimated_time_hours: float = 1.0,
    estimated_labor_cost: float = 25.00,
    workstation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an operation payload for API testing."""
    return {
        "code": code or f"OP-{generate_test_id()}",
        "name": name or f"Operation-{generate_test_id()}",
        "description": description,
        "process_type": process_type,
        "estimated_time_hours": estimated_time_hours,
        "estimated_labor_cost": estimated_labor_cost,
        "workstation_id": workstation_id,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Inventory Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_stock_adjustment_payload(
    material_id: str,
    quantity_change: float,
    reason: str = "manual_adjustment",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a stock adjustment payload."""
    return {
        "material_id": material_id,
        "quantity_change": quantity_change,
        "reason": reason,
        "notes": notes or f"Test adjustment of {quantity_change}",
    }


# ───────────────────────────────────────────────────────────────────────────────
# Batch & Lot Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_batch_payload(
    material_id: str,
    batch_number: Optional[str] = None,
    quantity: float = 100.0,
    manufacturing_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a batch/lot payload."""
    if batch_number is None:
        batch_number = f"BATCH-{generate_test_id()}"
    
    if manufacturing_date is None:
        manufacturing_date = datetime.utcnow().isoformat()
    
    if expiration_date is None:
        expiration_date = (
            datetime.utcnow() + timedelta(days=365)
        ).isoformat()
    
    return {
        "material_id": material_id,
        "batch_number": batch_number,
        "quantity": quantity,
        "manufacturing_date": manufacturing_date,
        "expiration_date": expiration_date,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Workstation Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_workstation_payload(
    code: Optional[str] = None,
    name: Optional[str] = None,
    equipment_type: str = "assembly_line",
    hourly_rate: float = 50.00,
) -> Dict[str, Any]:
    """Create a workstation payload."""
    return {
        "code": code or f"WS-{generate_test_id()}",
        "name": name or f"Workstation-{generate_test_id()}",
        "equipment_type": equipment_type,
        "hourly_rate": hourly_rate,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Utility Factories
# ───────────────────────────────────────────────────────────────────────────────

def create_pagination_params(page: int = 1, page_size: int = 50) -> Dict[str, int]:
    """Create pagination parameters."""
    return {"page": page, "page_size": page_size}


def create_error_response(
    status_code: int,
    detail: str,
    error_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an expected error response for assertion."""
    response = {
        "detail": detail,
        "status_code": status_code,
    }
    if error_type:
        response["error_type"] = error_type
    return response
