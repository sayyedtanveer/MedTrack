"""Authorized direct cost setting shared by the Buy tab and onboarding.

The caller owns the transaction and permission check. This handler never commits.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    MaterialCostHistoryModel,
    StandardCostRevisionModel,
)
from backend.app.infrastructure.persistence.repositories.procurement_pricing_repository import (
    StandardCostRevisionRepository,
)
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

COST_QUANTUM = Decimal("0.0001")
MAX_STANDARD_COST = Decimal("999999999.9999")


class ConcurrentCostChangeError(ValueError):
    """The effective cost changed since the caller read it."""


def normalize_standard_cost(value: Decimal) -> Decimal:
    """Use the effective material column's four-decimal precision everywhere."""
    if not value.is_finite() or value < 0 or value > MAX_STANDARD_COST:
        raise ValueError(f"Standard cost must be between 0 and {MAX_STANDARD_COST}.")
    try:
        return value.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Invalid standard cost precision.") from exc


@dataclass(frozen=True)
class DirectStandardCostResult:
    previous_cost: Decimal | None
    new_cost: Decimal
    change_type: str
    cost_history_id: UUID
    revision_id: UUID


class DirectStandardCostHandler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.revisions = StandardCostRevisionRepository(session)

    async def handle(
        self,
        *,
        tenant_id: UUID,
        material_id: UUID,
        user_id: UUID,
        new_cost: Decimal,
        reason: str | None = None,
        expected_current_cost: Decimal | None = None,
        initial_only: bool = False,
    ) -> DirectStandardCostResult:
        effective_cost = normalize_standard_cost(new_cost)
        # The lock MUST precede both the old-cost read and the optimistic check.
        previous_cost = await self.revisions.get_material_current_cost(
            tenant_id, material_id, lock=True
        )
        if previous_cost is None:
            raise LookupError("Material not found")
        if expected_current_cost is not None and previous_cost != expected_current_cost:
            raise ConcurrentCostChangeError(
                "Concurrent modification detected. The standard cost changed; reload and try again."
            )
        approved = await self.revisions.get_approved_cost(tenant_id, material_id)
        first_setup = approved is None and previous_cost == 0
        if initial_only and not first_setup:
            raise ConcurrentCostChangeError("An effective standard cost already exists; import cannot overwrite it.")
        if not first_setup and not (reason and reason.strip()):
            raise ValueError("A reason is required when changing an existing standard cost.")
        reason_text = (reason or "INITIAL_SETUP").strip()
        if len(reason_text) > 500:
            raise ValueError("Cost change reason cannot exceed 500 characters.")
        change_type = "INITIAL_SETUP" if first_setup else "DIRECT_REVISION"
        if not await self.revisions.update_material_current_cost(
            tenant_id, material_id, effective_cost, user_id
        ):
            raise LookupError("Material not found")
        now = datetime.now(timezone.utc)
        revision = StandardCostRevisionModel(
            id=uuid4(), tenant_id=tenant_id, material_id=material_id,
            requested_by=user_id, requested_cost=effective_cost, current_cost=previous_cost,
            reason="INITIAL_SETUP" if first_setup else "MANUAL_ADJUSTMENT",
            notes=f"Authorized direct cost save. change_type={change_type}. {reason_text}",
            status="APPROVED", approved_by=None, approved_at=now,
            is_deleted=False, created_by=user_id, updated_by=user_id,
            created_at=now, updated_at=now,
        )
        history = MaterialCostHistoryModel(
            id=uuid4(), tenant_id=tenant_id, material_id=material_id,
            old_cost=None if first_setup else previous_cost, new_cost=effective_cost,
            change_type=change_type, source_type="MANUAL", source_id=str(revision.id),
            approved_by=None, notes=reason_text, created_at=now,
        )
        self.session.add_all([revision, history])
        await self.session.flush()
        logger.info("Direct standard cost prepared", extra={
            "tenant_id": str(tenant_id), "user_id": str(user_id),
            "material_id": str(material_id), "revision_id": str(revision.id),
            "change_type": change_type,
        })
        return DirectStandardCostResult(
            None if first_setup else previous_cost, effective_cost, change_type,
            history.id, revision.id,
        )
