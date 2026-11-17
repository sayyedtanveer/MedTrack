from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.app.application.procurement.pricing.commands import (
    ApproveStandardCostRevisionCommand,
)
from backend.app.application.procurement.pricing.handlers import (
    ProcurementPricingHandlers,
)
from backend.app.domain.procurement.pricing.entities import StandardCostRevision
from backend.app.domain.procurement.pricing.exceptions import (
    RequesterCannotApproveOwnRevisionError,
    StaleCostRevisionError,
)


def _create_handlers(
    revision: StandardCostRevision,
    current_cost: Decimal,
) -> tuple[ProcurementPricingHandlers, SimpleNamespace]:
    revision_repo = SimpleNamespace(
        get_by_id_for_update=AsyncMock(return_value=revision),
        get_material_current_cost=AsyncMock(return_value=current_cost),
        update_material_current_cost=AsyncMock(return_value=True),
        save=AsyncMock(return_value=revision),
    )
    handler = ProcurementPricingHandlers(
        session=object(),
        supplier_agreement_repo=object(),
        cost_revision_repo=revision_repo,
        cost_history_repo=SimpleNamespace(add_entry=AsyncMock()),
        override_repo=object(),
    )
    return handler, revision_repo


@pytest.mark.asyncio
async def test_requester_cannot_approve_own_standard_cost_revision() -> None:
    tenant_id = uuid4()
    requester_id = uuid4()
    revision_id = uuid4()
    revision = StandardCostRevision(
        id=revision_id,
        tenant_id=tenant_id,
        material_id=uuid4(),
        requested_by=requester_id,
        requested_cost=Decimal("12"),
        current_cost=Decimal("10"),
        reason="MANUAL_ADJUSTMENT",
    )
    handler, revision_repo = _create_handlers(revision, Decimal("10"))

    with pytest.raises(RequesterCannotApproveOwnRevisionError):
        await handler.handle_approve_standard_cost_revision(
            ApproveStandardCostRevisionCommand(
                tenant_id=tenant_id,
                revision_id=revision_id,
                approved_by=requester_id,
            )
        )

    revision_repo.get_by_id_for_update.assert_awaited_once_with(tenant_id, revision_id)
    revision_repo.get_material_current_cost.assert_awaited_once_with(
        tenant_id, revision.material_id, lock=True
    )
    revision_repo.update_material_current_cost.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_standard_cost_revision_is_not_approved() -> None:
    tenant_id = uuid4()
    revision_id = uuid4()
    revision = StandardCostRevision(
        id=revision_id,
        tenant_id=tenant_id,
        material_id=uuid4(),
        requested_by=uuid4(),
        requested_cost=Decimal("12"),
        current_cost=Decimal("10"),
        reason="MANUAL_ADJUSTMENT",
    )
    handler, revision_repo = _create_handlers(revision, Decimal("11"))

    with pytest.raises(StaleCostRevisionError):
        await handler.handle_approve_standard_cost_revision(
            ApproveStandardCostRevisionCommand(
                tenant_id=tenant_id,
                revision_id=revision_id,
                approved_by=uuid4(),
            )
        )

    revision_repo.get_by_id_for_update.assert_awaited_once_with(tenant_id, revision_id)
    revision_repo.get_material_current_cost.assert_awaited_once_with(
        tenant_id, revision.material_id, lock=True
    )
    revision_repo.update_material_current_cost.assert_not_awaited()
