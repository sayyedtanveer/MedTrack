"""
Phase 3 unit tests — Finished-Material Type Validation and
Active-BOM duplicate detection.

Part A — Active BOM duplicate detection (get_active_bom)
  - Valid single active BOM returns it
  - MultipleResultsFound is converted to clear ValueError
  - Correct message names the product and tenant

Part B — _resolve_finished_good_material_id material-link validation
  Approved behavior (from code review 2026-11-14):
    1. Explicit variant.material_id → validate tenant, type='finished', not soft-deleted
       - Valid link          → return material.id
       - Wrong tenant        → ValueError with explanation
       - Wrong type (raw)    → ValueError with explanation
       - Soft-deleted        → ValueError with explanation
    2. NULL material_id     → SKU-based fallback (unchanged, existing safe behavior)
    3. No matching SKU      → ValueError (unchanged)
  
  NOT tested here (unchanged behavior):
    - Stage 1: wo.product_id is a MaterialModel.id directly
    - SKU fallback multi-match (impossible due to UNIQUE(tenant_id, code) constraint)
"""

import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import MultipleResultsFound


# ── Helpers ───────────────────────────────────────────────────────────────────

TENANT_ID = uuid.uuid4()
VARIANT_ID = uuid.uuid4()
MATERIAL_ID = uuid.uuid4()
OTHER_TENANT_ID = uuid.uuid4()
WO_ID = uuid.uuid4()


def _make_work_order(product_id=None, tenant_id=None):
    wo = MagicMock()
    wo.product_id = product_id or VARIANT_ID
    wo.tenant_id = tenant_id or TENANT_ID
    wo.id = WO_ID
    wo.produced_quantity = 5.0
    return wo


def _make_variant(material_id=None):
    v = MagicMock()
    v.id = VARIANT_ID
    v.code = "FG-VARIANT-001"
    v.material_id = material_id
    return v


def _make_material(material_type="finished", is_deleted=False, tenant_id=None):
    m = MagicMock()
    m.id = MATERIAL_ID
    m.code = "FG-VARIANT-001"
    m.material_type = material_type
    m.is_deleted = is_deleted
    m.tenant_id = tenant_id or TENANT_ID
    return m


# ── Part A: get_active_bom duplicate detection ───────────────────────────────

class TestGetActiveBOMDuplicateDetection:
    """
    get_active_bom() must convert MultipleResultsFound into a clear ValueError
    so that the caller (BOM handlers, manufacturing integration) receives a
    business-context error rather than a raw SQLAlchemy exception.
    """

    @pytest.mark.asyncio
    async def test_multiple_active_boms_raises_value_error_with_context(self):
        """When multiple active BOMs exist, ValueError with clear message is raised."""
        from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository

        variant_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.side_effect = MultipleResultsFound()
        mock_session.execute = AsyncMock(return_value=execute_result)

        repo = BOMRepository.__new__(BOMRepository)
        repo._session = mock_session

        with pytest.raises(ValueError) as exc_info:
            await repo.get_active_bom(
                tenant_id=tenant_id,
                variant_id=variant_id,
            )

        message = str(exc_info.value)
        assert "multiple active boms" in message.lower()
        assert str(variant_id) in message
        assert str(tenant_id) in message
        assert "deactivate" in message.lower()

    @pytest.mark.asyncio
    async def test_multiple_active_template_boms_names_template_in_error(self):
        """Error message names template_id when that is the target."""
        from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository

        template_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.side_effect = MultipleResultsFound()
        mock_session.execute = AsyncMock(return_value=execute_result)

        repo = BOMRepository.__new__(BOMRepository)
        repo._session = mock_session

        with pytest.raises(ValueError) as exc_info:
            await repo.get_active_bom(
                tenant_id=tenant_id,
                template_id=template_id,
            )

        message = str(exc_info.value)
        assert "template" in message.lower()
        assert str(template_id) in message

    @pytest.mark.asyncio
    async def test_single_active_bom_returns_entity(self):
        """Normal path: single active BOM returns correctly without error."""
        from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
        from backend.app.infrastructure.persistence.models.bom_model import BOMModel
        from datetime import datetime, timezone

        bom_model = MagicMock(spec=BOMModel)
        bom_model.id = uuid.uuid4()
        bom_model.tenant_id = TENANT_ID
        bom_model.template_id = None
        bom_model.variant_id = VARIANT_ID
        bom_model.version = "v1.0"
        bom_model.is_active = True
        bom_model.is_deleted = False
        bom_model.valid_from = datetime.now(timezone.utc)
        bom_model.valid_to = None
        bom_model.created_by = uuid.uuid4()
        bom_model.approved_by = None
        bom_model.lines = []
        bom_model.operations = []

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = bom_model
        mock_session.execute = AsyncMock(return_value=execute_result)

        repo = BOMRepository.__new__(BOMRepository)
        repo._session = mock_session

        result = await repo.get_active_bom(
            tenant_id=TENANT_ID,
            variant_id=VARIANT_ID,
        )
        assert result is not None
        assert result.variant_id == VARIANT_ID

    @pytest.mark.asyncio
    async def test_no_active_bom_returns_none(self):
        """When no active BOM exists, None is returned without error."""
        from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository

        mock_session = MagicMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=execute_result)

        repo = BOMRepository.__new__(BOMRepository)
        repo._session = mock_session

        result = await repo.get_active_bom(
            tenant_id=TENANT_ID,
            variant_id=VARIANT_ID,
        )
        assert result is None


# ── Part B: _resolve_finished_good_material_id validation ────────────────────

class TestResolveFinishedGoodMaterialId:
    """
    Tests for _resolve_finished_good_material_id in WorkflowOrchestrationService.

    We test only the variant path (stage 2 of the resolution).
    Stage 1 (product_id = material.id directly) is unchanged and not tested here.
    """

    def _make_service(self, session):
        """Build a WorkflowOrchestrationService with a mocked session."""
        from backend.app.application.manufacturing.services.workflow_orchestration_service import (
            WorkflowOrchestrationService,
        )
        svc = WorkflowOrchestrationService.__new__(WorkflowOrchestrationService)
        svc.session = session
        return svc

    def _make_session(self, *, stage1_material=None, variant=None, explicit_material=None, skufallback_material=None):
        """
        Mock a session that returns different values for each SELECT in order:
          call 1 — stage1 direct material lookup (None = not a direct material)
          call 2 — variant lookup
          call 3 — explicit material_id lookup (if variant.material_id is set)
          call 4 — SKU fallback (if explicit link absent or skipped)
        """
        session = MagicMock()

        def _result(value):
            r = MagicMock()
            r.scalar_one_or_none.return_value = value
            return r

        call_map = {
            0: _result(stage1_material),  # direct material check
            1: _result(variant),          # variant lookup
            2: _result(explicit_material), # explicit material_id lookup
            3: _result(skufallback_material),  # SKU fallback
        }
        call_count = [0]

        async def _execute(stmt):
            idx = call_count[0]
            call_count[0] += 1
            return call_map.get(idx, _result(None))

        session.execute = _execute
        return session

    @pytest.mark.asyncio
    async def test_valid_explicit_link_returns_material_id(self):
        """Variant with valid explicit material_id link returns it directly."""
        variant = _make_variant(material_id=MATERIAL_ID)
        material = _make_material(material_type="finished", is_deleted=False)
        session = self._make_session(
            stage1_material=None,
            variant=variant,
            explicit_material=material,
        )
        svc = self._make_service(session)
        result = await svc._resolve_finished_good_material_id(_make_work_order())
        assert result == MATERIAL_ID

    @pytest.mark.asyncio
    async def test_explicit_link_wrong_type_raises_error(self):
        """Variant linked to a raw material → controlled ValueError, no fallback."""
        variant = _make_variant(material_id=MATERIAL_ID)
        material = _make_material(material_type="raw", is_deleted=False)
        session = self._make_session(
            stage1_material=None,
            variant=variant,
            explicit_material=material,
        )
        svc = self._make_service(session)

        with pytest.raises(ValueError) as exc_info:
            await svc._resolve_finished_good_material_id(_make_work_order())

        message = str(exc_info.value)
        assert "type" in message.lower() or "material_type" in message.lower() or "raw" in message.lower()
        assert str(MATERIAL_ID) in message
        # Must NOT say "Cannot post" for a "not found" error — it should say "wrong type"
        # (the exact wording is in the implementation; here we just check IDs are named)
        assert str(variant.id) in message

    @pytest.mark.asyncio
    async def test_explicit_link_soft_deleted_raises_error(self):
        """Variant linked to a soft-deleted material → controlled ValueError, no fallback."""
        variant = _make_variant(material_id=MATERIAL_ID)
        # Soft-deleted materials are excluded by the query filter, so the lookup returns None
        session = self._make_session(
            stage1_material=None,
            variant=variant,
            explicit_material=None,   # query returns None for soft-deleted material
        )
        svc = self._make_service(session)

        with pytest.raises(ValueError) as exc_info:
            await svc._resolve_finished_good_material_id(_make_work_order())

        message = str(exc_info.value)
        assert "explicit" in message.lower() or "material_id" in message.lower()
        # Key assertion: must not silently fall through to SKU fallback
        assert "does not exist" in message.lower() or "tenant" in message.lower() or "Cannot post" in message.lower()

    @pytest.mark.asyncio
    async def test_null_material_id_uses_sku_fallback(self):
        """Variant with NULL material_id uses SKU-based fallback (preserved behavior)."""
        variant = _make_variant(material_id=None)
        fallback_material = _make_material(material_type="finished")
        # When material_id is None: calls are stage1(None), variant, SKU fallback
        # The explicit-link block is skipped entirely, so only 3 calls needed
        session = self._make_session(
            stage1_material=None,
            variant=variant,
            explicit_material=fallback_material,  # call 2 → SKU fallback when material_id is None
        )
        svc = self._make_service(session)
        result = await svc._resolve_finished_good_material_id(_make_work_order())
        assert result == MATERIAL_ID

    @pytest.mark.asyncio
    async def test_null_material_id_no_sku_match_raises_error(self):
        """Variant with NULL material_id and no matching SKU → controlled error."""
        variant = _make_variant(material_id=None)
        session = self._make_session(
            stage1_material=None,
            variant=variant,
            skufallback_material=None,
        )
        svc = self._make_service(session)

        with pytest.raises(ValueError) as exc_info:
            await svc._resolve_finished_good_material_id(_make_work_order())

        message = str(exc_info.value)
        assert "finished-good material" in message.lower() or "no finished" in message.lower()

    @pytest.mark.asyncio
    async def test_variant_not_found_raises_error(self):
        """WO product_id not found as material or variant → controlled error."""
        session = self._make_session(
            stage1_material=None,
            variant=None,
        )
        svc = self._make_service(session)

        with pytest.raises(ValueError) as exc_info:
            await svc._resolve_finished_good_material_id(_make_work_order())

        message = str(exc_info.value)
        assert "not found" in message.lower()
