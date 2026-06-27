import uuid

import io
import pytest
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.material_model import MaterialModel


async def test_material_onboarding_full_flow(authenticated_async_client, db_session, test_tenant_id):
    """E2E: upload -> validate -> preview -> execute and assert DB insert with admin auth."""
    client = authenticated_async_client

    # Prepare CSV content (single row)
    csv_content = "item_code,material_name,material_category,uom\nMAT-TEST-001,Test Material,Raw Materials,KG\n"
    files = {"file": ("materials.csv", csv_content, "text/csv")}

    # 1) Create session (upload)
    resp = await client.post("/api/v1/inventory/material-onboarding/sessions", files=files)
    assert resp.status_code == 201, resp.text
    session_json = resp.json()
    session_id = session_json["session_id"]

    # 2) Validate with explicit mapping
    mapping = {
        "item_code": "item_code",
        "material_name": "material_name",
        "material_category": "material_category",
        "uom": "uom",
    }
    validate_resp = await client.post(f"/api/v1/inventory/material-onboarding/sessions/{session_id}/validate", json={"mapping": mapping})
    assert validate_resp.status_code == 200, validate_resp.text
    assert validate_resp.json().get("validated", 0) == 1

    # 3) Preview
    preview_resp = await client.get(f"/api/v1/inventory/material-onboarding/sessions/{session_id}/preview")
    assert preview_resp.status_code == 200, preview_resp.text
    preview_json = preview_resp.json()
    assert preview_json["summary"]["total_rows"] == 1
    row = preview_json["rows"][0]
    assert row["classification"] in ("new", "update")
    assert row["status"] == "ready"

    # 4) Execute (real run)
    exec_resp = await client.post(f"/api/v1/inventory/material-onboarding/sessions/{session_id}/execute", json={"dry_run": False})
    assert exec_resp.status_code == 200, exec_resp.text
    exec_json = exec_resp.json()
    assert exec_json.get("errors", 0) == 0, exec_json.get("error_messages")
    assert exec_json.get("created", 0) + exec_json.get("updated", 0) >= 1

    # 5) Verify DB: material exists for tenant
    result = await db_session.execute(
        select(MaterialModel).where(
            MaterialModel.tenant_id == test_tenant_id,
            MaterialModel.name == "Test Material",
            MaterialModel.is_deleted.is_(False),
        )
    )
    material = result.scalars().first()
    assert material is not None
    assert str(material.code) == "MAT-TEST-001"
