"""
Phase 1 Integration Tests — Master Data Setup
===============================================
Tests for: POST /api/v1/suppliers
           POST /api/v1/inventory/materials  (raw + FG + opening stock)
           POST /api/v1/products/templates
           POST /api/v1/products/templates/{id}/variants
           POST /api/v1/products/{id}/boms
           POST /api/v1/sales/clients

Covers:
  TC-4.1  POST /suppliers creates a supplier with a unique code
  TC-4.2  POST /suppliers rejects duplicate supplier code
  TC-5.1  POST /inventory/materials creates a raw material
  TC-5.2  Raw material creation with opening_stock creates an inventory_transaction
  TC-6.1  POST /inventory/materials creates a finished goods material
  TC-7.1  POST /products/templates creates a product template
  TC-7.2  POST /products/templates/{id}/variants creates a variant linked to FG material
  TC-8.1  POST /products/{id}/boms creates a BOM with ≥1 line
  TC-9.1  POST /sales/clients creates a customer with a unique code
  TC-9.2  POST /sales/clients rejects duplicate customer code
  TC-FK   FK chain: variant.material_id → FG material.id; BOM.variant_id → variant.id

Requirements: 4–9
"""
from __future__ import annotations

import backend.app.main  # noqa: F401  (registers all ORM models)

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.inventory_transaction_model import (
    InventoryTransactionModel,
)


SUPPLIERS_URL = "/api/v1/suppliers"
MATERIALS_URL = "/api/v1/inventory/materials"
MASTER_DATA_URL = "/api/v1/inventory/master-data"
PRODUCTS_URL = "/api/v1/products"
CLIENTS_URL = "/api/v1/sales/clients"


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _create_unit(async_client: AsyncClient, headers: dict) -> str:
    """Create a Unit of Measure and return its id."""
    suffix = uuid.uuid4().hex[:6]
    resp = await async_client.post(
        f"{MASTER_DATA_URL}/units",
        json={"code": f"EA{suffix}", "name": f"Each-{suffix}", "is_active": True},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Unit creation failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


async def _create_category(async_client: AsyncClient, headers: dict) -> str:
    """Create a material category and return its id."""
    suffix = uuid.uuid4().hex[:6]
    resp = await async_client.post(
        f"{MASTER_DATA_URL}/categories",
        json={"name": f"Cat-{suffix}", "code_prefix": f"C{suffix[:4]}"},
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Category creation failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


async def _create_raw_material(
    async_client: AsyncClient,
    headers: dict,
    *,
    opening_stock: float = 0.0,
) -> dict:
    """Create a raw material and return the response JSON."""
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, headers)
    resp = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"Raw-Mat-{suffix}",
            "material_type": "raw",
            "base_unit_id": unit_id,
            "opening_stock": opening_stock,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Raw material creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def _create_fg_material(async_client: AsyncClient, headers: dict) -> dict:
    """Create a finished goods material and return the response JSON."""
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, headers)
    resp = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"FG-Mat-{suffix}",
            "material_type": "finished",
            "base_unit_id": unit_id,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"FG material creation failed: {resp.status_code} {resp.text}"
    return resp.json()


async def _create_template(
    async_client: AsyncClient,
    headers: dict,
    category_id: str,
) -> dict:
    """Create a product template and return the response JSON."""
    suffix = uuid.uuid4().hex[:8]
    resp = await async_client.post(
        f"{PRODUCTS_URL}/templates",
        json={
            "name": f"Template-{suffix}",
            "category_id": category_id,
            "attributes": [{"key": "SIZE", "label": "Size"}],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert resp.status_code == 201, f"Template creation failed: {resp.status_code} {resp.text}"
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# TC-4.1  POST /suppliers creates a supplier with a unique code
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_supplier_success(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /suppliers with a unique supplier code must create the
    supplier and return HTTP 201 with the supplier ID.

    Validates: Requirements 4 AC 1, 2
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "code": f"SUPP-{suffix}",
        "name": f"Test Supplier {suffix}",
        "contact_person": "John Doe",
        "payment_terms": "Net 30",
    }

    response = await async_client.post(
        SUPPLIERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 for new supplier, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "id" in data, "Response must include the supplier id"
    assert data["code"] == payload["code"], "Supplier code must match what was submitted"
    assert data["name"] == payload["name"], "Supplier name must match what was submitted"


# ─────────────────────────────────────────────────────────────────────────────
# TC-4.2  POST /suppliers rejects duplicate supplier code
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_supplier_rejects_duplicate_code(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 3: When the Admin submits a duplicate supplier code within the same
    tenant, the System SHALL reject the submission with a duplication error.

    Validates: Requirements 4 AC 3
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "code": f"DUPSUPP-{suffix}",
        "name": f"Dup Supplier {suffix}",
    }

    resp1 = await async_client.post(
        SUPPLIERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp1.status_code == 201, (
        f"First supplier creation should succeed: {resp1.status_code} {resp1.text}"
    )

    resp2 = await async_client.post(
        SUPPLIERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp2.status_code == 409, (
        f"Expected 409 for duplicate supplier code, "
        f"got {resp2.status_code}: {resp2.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-5.1  POST /inventory/materials creates a raw material
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_raw_material_success(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1: POST /inventory/materials with material_type='raw' must create
    the material and return HTTP 201.

    Validates: Requirements 5 AC 1
    """
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, admin_user["headers"])

    response = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"Raw-Material-{suffix}",
            "material_type": "raw",
            "base_unit_id": unit_id,
        },
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 for new raw material, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "id" in data, "Response must include the material id"
    assert data["material_type"] == "raw", "material_type must be 'raw'"


# ─────────────────────────────────────────────────────────────────────────────
# TC-5.2  Raw material with opening_stock creates an inventory transaction
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_raw_material_with_opening_stock(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
    e2e_db_session,
    test_tenant,
):
    """
    AC 2 & 3: POST /inventory/materials with opening_stock > 0 must:
    - Create a record in the materials table
    - Create an inventory_transactions record with transaction_type in
      ('in', 'onboarding_opening_balance')
    - Reflect opening_stock in materials.current_stock

    Validates: Requirements 5 AC 2, 3
    """
    opening_qty = 50.0
    mat = await _create_raw_material(
        async_client,
        admin_user["headers"],
        opening_stock=opening_qty,
    )
    material_id = uuid.UUID(mat["id"])

    # Verify current_stock reflects opening quantity
    assert float(mat.get("current_stock", 0)) == opening_qty, (
        f"current_stock must equal opening_stock={opening_qty}, "
        f"got {mat.get('current_stock')}"
    )

    # Verify an inventory_transaction was created
    await e2e_db_session.rollback()
    tx = await e2e_db_session.scalar(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.material_id == material_id,
            InventoryTransactionModel.tenant_id == test_tenant.id,
        )
    )
    assert tx is not None, (
        "An inventory_transaction record must be created for opening stock"
    )
    assert tx.transaction_type in ("in", "onboarding_opening_balance"), (
        f"Expected transaction_type 'in' or 'onboarding_opening_balance', "
        f"got '{tx.transaction_type}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-6.1  POST /inventory/materials creates a finished goods material
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_fg_material_success(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /inventory/materials with material_type='finished' must
    create the material and return HTTP 201 with material_type='finished'.

    Validates: Requirements 6 AC 1, 2
    """
    suffix = uuid.uuid4().hex[:8]
    unit_id = await _create_unit(async_client, admin_user["headers"])

    response = await async_client.post(
        MATERIALS_URL,
        json={
            "name": f"FG-Material-{suffix}",
            "material_type": "finished",
            "base_unit_id": unit_id,
        },
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 for new FG material, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["material_type"] == "finished", (
        f"material_type must be 'finished', got '{data['material_type']}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-7.1  POST /products/templates creates a product template
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_product_template_success(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /products/templates must create a template and return
    HTTP 201 with the template ID.

    Validates: Requirements 7 AC 1, 2
    """
    category_id = await _create_category(async_client, admin_user["headers"])
    template = await _create_template(async_client, admin_user["headers"], category_id)

    assert "id" in template, "Response must include the template id"
    assert "name" in template, "Response must include the template name"


# ─────────────────────────────────────────────────────────────────────────────
# TC-7.2  POST /products/templates/{id}/variants creates a variant linked to FG material
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_variant_linked_to_fg_material(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 3 & 4: POST /products/templates/{id}/variants must:
    - Create a variant with a unique variant_key from attribute values
    - Accept a material_id FK pointing to a finished goods material

    Validates: Requirements 7 AC 3, 4
    """
    # Create prerequisite data
    category_id = await _create_category(async_client, admin_user["headers"])
    fg_material = await _create_fg_material(async_client, admin_user["headers"])
    template = await _create_template(async_client, admin_user["headers"], category_id)

    template_id = template["id"]
    fg_material_id = fg_material["id"]

    # Create variant linking to FG material
    suffix = uuid.uuid4().hex[:8]
    variant_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates/{template_id}/variants",
        json={
            "attribute_values": {"SIZE": f"L-{suffix}"},
            "material_id": fg_material_id,
            "standard_cost": 10.0,
        },
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert variant_resp.status_code == 201, (
        f"Expected 201 for variant creation, "
        f"got {variant_resp.status_code}: {variant_resp.text}"
    )
    variant_data = variant_resp.json()
    assert "id" in variant_data, "Response must include variant id"
    assert variant_data.get("material_id") == fg_material_id, (
        f"Variant material_id must be set to the FG material id '{fg_material_id}', "
        f"got '{variant_data.get('material_id')}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-8.1  POST /products/{id}/boms creates a BOM with ≥1 line
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_bom_with_at_least_one_line(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /products/{id}/boms must create a BOM with at least one
    BOM line and return HTTP 201.

    Validates: Requirements 8 AC 1, 2
    """
    # Create prerequisite data
    category_id = await _create_category(async_client, admin_user["headers"])
    raw_material = await _create_raw_material(async_client, admin_user["headers"])
    template = await _create_template(async_client, admin_user["headers"], category_id)

    template_id = template["id"]
    raw_material_id = raw_material["id"]

    bom_payload = {
        "version": "v1.0",
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "template_id": template_id,
        "lines": [
            {
                "material_id": raw_material_id,
                "quantity": 2.5,
            }
        ],
    }

    bom_resp = await async_client.post(
        f"{PRODUCTS_URL}/{template_id}/boms",
        json=bom_payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert bom_resp.status_code == 201, (
        f"Expected 201 for BOM creation, got {bom_resp.status_code}: {bom_resp.text}"
    )
    bom_data = bom_resp.json()
    assert "id" in bom_data, "BOM response must include an id"
    assert len(bom_data.get("lines", [])) >= 1, (
        "BOM must have at least one line"
    )
    assert bom_data["lines"][0]["material_id"] == raw_material_id, (
        "BOM line must reference the raw material"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-9.1  POST /sales/clients creates a customer with a unique code
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_customer_success(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /sales/clients with a unique customer code must create
    the customer and return HTTP 201 with the customer ID.

    Validates: Requirements 9 AC 1, 2
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "code": f"CUST-{suffix}",
        "name": f"Test Customer {suffix}",
    }

    response = await async_client.post(
        CLIENTS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 for new customer, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "id" in data, "Response must include the customer id"
    assert data["code"] == payload["code"], "Customer code must match what was submitted"
    assert data["name"] == payload["name"], "Customer name must match what was submitted"


# ─────────────────────────────────────────────────────────────────────────────
# TC-9.2  POST /sales/clients rejects duplicate customer code
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_customer_rejects_duplicate_code(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 3: When the Admin submits a duplicate customer code within the same
    tenant, the System SHALL reject the submission with a duplication error.

    Validates: Requirements 9 AC 3
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "code": f"DUPCUST-{suffix}",
        "name": f"Dup Customer {suffix}",
    }

    resp1 = await async_client.post(
        CLIENTS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp1.status_code == 201, (
        f"First customer creation should succeed: {resp1.status_code} {resp1.text}"
    )

    resp2 = await async_client.post(
        CLIENTS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp2.status_code in (400, 409), (
        f"Expected 400 or 409 for duplicate customer code, "
        f"got {resp2.status_code}: {resp2.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-FK  FK chain assertion: variant → FG material; BOM → variant
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fk_chain_variant_fg_material_bom(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    Assert the full FK dependency chain required by the design document:

      Raw Material (Req 5)
            ↓
      Finished Goods Material (Req 6)
            ↓
      Product Template (Req 7)
            ↓
      Product Variant → material_id FK → FG Material (Req 7)
            ↓
      BOM → variant_id FK → Variant (Req 8)

    Steps:
      1. POST a finished goods material
      2. POST a product template
      3. POST a variant linking to the FG material → assert variant.material_id == fg.id
      4. POST a raw material (BOM input)
      5. POST a BOM on the template with variant_id → assert bom.variant_id == variant.id
      6. Assert bom.lines[0].material_id == raw_material.id

    Validates: Requirements 5–8 (FK chain / dependency chain)
    """
    headers = admin_user["headers"]

    # Step 1: Create FG material
    fg_mat = await _create_fg_material(async_client, headers)
    fg_mat_id = fg_mat["id"]

    # Step 2: Create product template
    category_id = await _create_category(async_client, headers)
    template = await _create_template(async_client, headers, category_id)
    template_id = template["id"]

    # Step 3: Create variant linked to FG material
    suffix = uuid.uuid4().hex[:8]
    var_resp = await async_client.post(
        f"{PRODUCTS_URL}/templates/{template_id}/variants",
        json={
            "attribute_values": {"SIZE": f"XL-{suffix}"},
            "material_id": fg_mat_id,
            "standard_cost": 15.0,
        },
        headers=headers,
        follow_redirects=True,
    )
    assert var_resp.status_code == 201, (
        f"Variant creation failed: {var_resp.status_code} {var_resp.text}"
    )
    variant = var_resp.json()
    variant_id = variant["id"]

    # Assert FK: variant.material_id → FG material
    assert variant.get("material_id") == fg_mat_id, (
        f"variant.material_id must equal fg_mat_id '{fg_mat_id}', "
        f"got '{variant.get('material_id')}'"
    )

    # Step 4: Create raw material (BOM component)
    raw_mat = await _create_raw_material(async_client, headers)
    raw_mat_id = raw_mat["id"]

    # Step 5: Create BOM linked to variant_id
    bom_resp = await async_client.post(
        f"{PRODUCTS_URL}/{template_id}/boms",
        json={
            "version": "v1.0",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "variant_id": variant_id,
            "lines": [
                {
                    "material_id": raw_mat_id,
                    "quantity": 3.0,
                }
            ],
        },
        headers=headers,
        follow_redirects=True,
    )
    assert bom_resp.status_code == 201, (
        f"BOM creation failed: {bom_resp.status_code} {bom_resp.text}"
    )
    bom = bom_resp.json()

    # Assert FK: BOM.variant_id → variant
    assert str(bom.get("variant_id")) == variant_id, (
        f"bom.variant_id must equal variant_id '{variant_id}', "
        f"got '{bom.get('variant_id')}'"
    )

    # Assert BOM line references the raw material
    assert len(bom.get("lines", [])) >= 1, "BOM must have at least one line"
    assert bom["lines"][0]["material_id"] == raw_mat_id, (
        f"BOM line material_id must equal raw_mat_id '{raw_mat_id}', "
        f"got '{bom['lines'][0].get('material_id')}'"
    )
