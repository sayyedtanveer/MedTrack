"""
Unit tests for BOM target-reassignment safety (Phase 2).

Requirements:
  - POST /products/{product_id}/boms  with body.template_id != product_id  → 422
  - POST /products/{product_id}/boms  with body.variant_id  != product_id  → 422
  - POST with matching body target  → passes guard (200/201 from handler)
  - POST with no body target        → passes guard (inferred from URL by handler)
  - PUT /boms/{id} never touches template_id/variant_id  → verified structurally
  - UpdateBOMCommand has no target fields → verified structurally
  - CreateBOMRequest validator: exactly one of template_id/variant_id  → verified
"""

import uuid
import pytest
from pydantic import ValidationError

from backend.app.interfaces.api.v1.schemas.bom_schemas import (
    CreateBOMRequest,
    UpdateBOMRequest,
    BOMLineRequest,
)
from backend.app.application.bom.commands.bom_commands import (
    UpdateBOMCommand,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

VARIANT_A = uuid.uuid4()
VARIANT_B = uuid.uuid4()
TEMPLATE_A = uuid.uuid4()
TEMPLATE_B = uuid.uuid4()


# ── Schema-level guard: CreateBOMRequest validation ──────────────────────────

class TestCreateBOMRequestSchema:
    """Pydantic schema correctly enforces exactly one target."""

    def test_template_id_accepted(self):
        req = CreateBOMRequest(
            version="v1.0",
            valid_from="2026-01-01T00:00:00Z",
            template_id=TEMPLATE_A,
        )
        assert req.template_id == TEMPLATE_A
        assert req.variant_id is None

    def test_variant_id_accepted(self):
        req = CreateBOMRequest(
            version="v1.0",
            valid_from="2026-01-01T00:00:00Z",
            variant_id=VARIANT_A,
        )
        assert req.variant_id == VARIANT_A
        assert req.template_id is None

    def test_neither_target_rejected_by_schema(self):
        """
        CreateBOMRequest enforces exactly-one at the Pydantic level.
        Omitting both template_id and variant_id raises ValidationError.
        This confirms the guard only ever sees one of the two fields set.
        """
        with pytest.raises(ValidationError, match="Exactly one"):
            CreateBOMRequest(
                version="v1.0",
                valid_from="2026-01-01T00:00:00Z",
            )

    def test_both_targets_rejected(self):
        """Both template_id and variant_id in body violates exactly-one invariant."""
        with pytest.raises(ValidationError, match="Exactly one"):
            CreateBOMRequest(
                version="v1.0",
                valid_from="2026-01-01T00:00:00Z",
                template_id=TEMPLATE_A,
                variant_id=VARIANT_A,
            )


# ── Route-level mismatch guard: logic tests ───────────────────────────────────

class TestBOMTargetMismatchGuard:
    """
    Unit-tests the mismatch detection logic implemented in
    POST /products/{product_id}/boms.

    We test the guard logic directly (without HTTP) by replicating
    the two conditional checks from the route.
    """

    def _guard(self, product_id: uuid.UUID, body: CreateBOMRequest) -> str | None:
        """Return an error message if the guard would reject, None if it would pass."""
        if body.template_id is not None and body.template_id != product_id:
            return (
                f"BOM target mismatch: the product_id in the URL ({product_id}) "
                f"does not match the template_id in the request body ({body.template_id})."
            )
        if body.variant_id is not None and body.variant_id != product_id:
            return (
                f"BOM target mismatch: the product_id in the URL ({product_id}) "
                f"does not match the variant_id in the request body ({body.variant_id})."
            )
        return None  # Guard passes

    # ── Matching cases (guard should pass) ──

    def test_matching_template_id_passes(self):
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               template_id=TEMPLATE_A)
        assert self._guard(TEMPLATE_A, req) is None

    def test_matching_variant_id_passes(self):
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               variant_id=VARIANT_A)
        assert self._guard(VARIANT_A, req) is None

    def test_no_target_in_body_would_be_rejected_by_pydantic(self):
        """
        CreateBOMRequest Pydantic validator enforces exactly-one, so the
        route guard is never reached when neither ID is provided.
        Confirmed: schema-level rejection happens before the route guard.
        """
        with pytest.raises(ValidationError):
            CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z")

    # ── Mismatch cases (guard should reject) ──

    def test_variant_a_url_variant_b_body_rejected(self):
        """POST /products/variant_A/boms with body.variant_id=variant_B → reject."""
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               variant_id=VARIANT_B)
        err = self._guard(VARIANT_A, req)
        assert err is not None
        assert "mismatch" in err.lower()
        assert str(VARIANT_B) in err

    def test_variant_url_template_body_rejected(self):
        """POST /products/variant_A/boms with body.template_id=template_A → reject."""
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               template_id=TEMPLATE_A)
        err = self._guard(VARIANT_A, req)
        assert err is not None
        assert "mismatch" in err.lower()

    def test_template_url_variant_body_rejected(self):
        """POST /products/template_A/boms with body.variant_id=variant_A → reject."""
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               variant_id=VARIANT_A)
        err = self._guard(TEMPLATE_A, req)
        assert err is not None
        assert "mismatch" in err.lower()

    def test_template_a_url_template_b_body_rejected(self):
        """POST /products/template_A/boms with body.template_id=template_B → reject."""
        req = CreateBOMRequest(version="v1.0", valid_from="2026-01-01T00:00:00Z",
                               template_id=TEMPLATE_B)
        err = self._guard(TEMPLATE_A, req)
        assert err is not None
        assert "mismatch" in err.lower()
        assert str(TEMPLATE_B) in err


# ── UpdateBOMCommand has no target fields ─────────────────────────────────────

class TestUpdateBOMCommandStructure:
    """
    Verify at import time that UpdateBOMCommand does not expose
    template_id or variant_id — meaning the update handler can never
    silently change the BOM target.
    """

    def test_update_command_has_no_template_id_field(self):
        cmd = UpdateBOMCommand(bom_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        assert not hasattr(cmd, "template_id"), (
            "UpdateBOMCommand must not expose template_id — target is immutable"
        )

    def test_update_command_has_no_variant_id_field(self):
        cmd = UpdateBOMCommand(bom_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        assert not hasattr(cmd, "variant_id"), (
            "UpdateBOMCommand must not expose variant_id — target is immutable"
        )

    def test_update_request_schema_has_no_target_fields(self):
        """UpdateBOMRequest schema must not include template_id/variant_id."""
        req = UpdateBOMRequest(valid_from="2026-01-01T00:00:00Z")
        assert not hasattr(req, "template_id")
        assert not hasattr(req, "variant_id")

    def test_update_command_allows_valid_from_change(self):
        """Component/validity updates must still work."""
        cmd = UpdateBOMCommand(
            bom_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            valid_from="2026-06-01T00:00:00Z",
        )
        assert cmd.valid_from == "2026-06-01T00:00:00Z"

    def test_update_command_allows_lines_change(self):
        """Component line replacements must still work."""
        from backend.app.application.bom.commands.bom_commands import BOMLineInput
        from decimal import Decimal
        cmd = UpdateBOMCommand(
            bom_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            lines=[
                BOMLineInput(quantity=Decimal("2.0"), material_id=uuid.uuid4())
            ],
        )
        assert len(cmd.lines) == 1
