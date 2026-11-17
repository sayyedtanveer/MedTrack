"""
Procurement pricing handlers (Phase 2 application layer).

Handlers orchestrate commands/queries, coordinate domain logic, and manage transactions.
All handler methods are async. Multi-tenancy is mandatory in every query/mutation.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.procurement.pricing.commands import (
    ApproveStandardCostRevisionCommand,
    ApproveSupplierPriceAgreementCommand,
    ActivateSupplierPriceAgreementCommand,
    CancelSupplierPriceAgreementCommand,
    CreateStandardCostRevisionCommand,
    CreateSupplierPriceAgreementCommand,
    InitializeStandardCostCommand,
    RecordMaterialCostChangeCommand,
    RecordPriceOverrideCommand,
    RejectStandardCostRevisionCommand,
    RejectSupplierPriceAgreementCommand,
    SubmitSupplierPriceAgreementForApprovalCommand,
)
from backend.app.application.procurement.pricing.queries import (
    GetActivePriceAgreementQuery,
    GetCostHistoryByChangeTypeQuery,
    GetMaterialCostHistoryQuery,
    GetPriceSuggestionQuery,
    GetStandardCostRevisionQuery,
    GetSupplierPriceAgreementQuery,
    ListMaterialCostRevisionsQuery,
    ListPendingCostRevisionsQuery,
    ListPriceOverridesQuery,
    ListSupplierPriceAgreementsQuery,
)
from backend.app.domain.procurement.pricing.entities import (
    MaterialCostHistory,
    PriceOverrideRecord,
    StandardCostRevision,
    StandardCostRevisionStatus,
    SupplierPriceAgreement,
    SupplierPriceAgreementStatus,
)
from backend.app.domain.procurement.pricing.exceptions import (
    AgreementAlreadyActiveError,
    CostRevisionAlreadyReviewedError,
    CostRevisionNotFoundError,
    InvalidAgreementStateTransitionError,
    OverlappingSupplierPriceAgreementError,
    PriceOverrideRecordNotFoundError,
    RequesterCannotApproveOwnRevisionError,
    StaleCostRevisionError,
    SupplierPriceAgreementNotFoundError,
)
from backend.app.domain.procurement.pricing.repositories import (
    IMaterialCostHistoryRepository,
    IPriceOverrideRecordRepository,
    IStandardCostRevisionRepository,
    ISupplierPriceAgreementRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)

logger = logging.getLogger(__name__)


# ── Response DTOs ──


@dataclass
class SupplierPriceAgreementResult:
    """Response DTO for supplier price agreement."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    material_id: uuid.UUID
    base_price: Decimal
    currency_code: str
    effective_from: datetime
    effective_to: Optional[datetime]
    quantity_tiers: Optional[List[dict]]
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    purchase_uom_id: Optional[uuid.UUID] = None
    minimum_order_quantity: Optional[Decimal] = None

    @staticmethod
    def from_entity(entity: SupplierPriceAgreement) -> "SupplierPriceAgreementResult":
        """Convert domain entity to response DTO."""
        tier_dicts = None
        if entity.quantity_tiers:
            tier_dicts = [
                {
                    "min_qty": float(tier.min_quantity),
                    "max_qty": float(tier.max_quantity) if tier.max_quantity else None,
                    "discount_percent": float(tier.discount_percent),
                }
                for tier in entity.quantity_tiers
            ]
        return SupplierPriceAgreementResult(
            id=entity.id,
            tenant_id=entity.tenant_id,
            supplier_id=entity.supplier_id,
            material_id=entity.material_id,
            base_price=entity.base_price,
            currency_code=entity.currency_code,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            quantity_tiers=tier_dicts,
            notes=entity.notes,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            purchase_uom_id=entity.purchase_uom_id,
            minimum_order_quantity=entity.minimum_order_quantity,
        )


@dataclass
class StandardCostRevisionResult:
    """Response DTO for cost revision."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    requested_by: uuid.UUID
    requested_cost: Decimal
    current_cost: Decimal
    variance_percent: Optional[Decimal]
    reason: str
    notes: Optional[str]
    status: str
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime

    @staticmethod
    def from_entity(entity: StandardCostRevision) -> "StandardCostRevisionResult":
        """Convert domain entity to response DTO."""
        return StandardCostRevisionResult(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            requested_by=entity.requested_by,
            requested_cost=entity.requested_cost,
            current_cost=entity.current_cost,
            variance_percent=entity.get_variance_percent(),
            reason=entity.reason,
            notes=entity.notes,
            status=entity.status.value,
            approved_by=entity.approved_by,
            approved_at=entity.approved_at,
            rejection_reason=entity.rejection_reason,
            created_at=entity.created_at,
        )


@dataclass
class SupplierPriceAgreementsPage:
    """Paginated supplier agreement results."""
    items: List[SupplierPriceAgreementResult]
    total: int
    page: int
    page_size: int


@dataclass
class StandardCostRevisionsPage:
    """Paginated standard cost revision results."""
    items: List[StandardCostRevisionResult]
    total: int
    page: int
    page_size: int


@dataclass
class MaterialCostHistoryResult:
    """Response DTO for cost history entry."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    old_cost: Optional[Decimal]
    new_cost: Decimal
    variance_percent: Optional[Decimal]
    change_type: str
    source_type: str
    source_id: Optional[str]
    approved_by: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime

    @staticmethod
    def from_entity(entity: MaterialCostHistory) -> "MaterialCostHistoryResult":
        """Convert domain entity to response DTO."""
        return MaterialCostHistoryResult(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            old_cost=entity.old_cost,
            new_cost=entity.new_cost,
            variance_percent=entity.get_variance_percent(),
            change_type=entity.change_type,
            source_type=entity.source_type,
            source_id=entity.source_id,
            approved_by=entity.approved_by,
            notes=entity.notes,
            created_at=entity.created_at,
        )


@dataclass
class PriceOverrideRecordResult:
    """Response DTO for price override record."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    grn_id: Optional[uuid.UUID]
    suggested_price: Decimal
    override_price: Decimal
    variance_percent: Decimal
    override_reason: str
    override_by: uuid.UUID
    notes: Optional[str]
    created_at: datetime

    @staticmethod
    def from_entity(entity: PriceOverrideRecord) -> "PriceOverrideRecordResult":
        """Convert domain entity to response DTO."""
        return PriceOverrideRecordResult(
            id=entity.id,
            tenant_id=entity.tenant_id,
            material_id=entity.material_id,
            grn_id=entity.grn_id,
            suggested_price=entity.suggested_price,
            override_price=entity.override_price,
            variance_percent=entity.get_variance_percent(),
            override_reason=entity.override_reason,
            override_by=entity.override_by,
            notes=entity.notes,
            created_at=entity.created_at,
        )


@dataclass
class PriceSuggestionResult:
    """Response DTO for price suggestion."""
    material_id: uuid.UUID
    suggested_price: Decimal
    currency_code: str
    source: str  # SUPPLIER_AGREEMENT, QUOTATION, GRN_SAME_SUPPLIER, GRN_ANY_SUPPLIER, STANDARD_COST, MANUAL
    source_id: Optional[str]  # Agreement ID, quotation ID, GRN ID, etc.
    source_date: Optional[datetime]  # When the source was created/effective
    notes: Optional[str]


# ── Handler Class ──


class ProcurementPricingHandlers:
    """Handlers for supplier price agreements and cost management."""

    def __init__(
        self,
        session: AsyncSession,
        supplier_agreement_repo: ISupplierPriceAgreementRepository,
        cost_revision_repo: IStandardCostRevisionRepository,
        cost_history_repo: IMaterialCostHistoryRepository,
        override_repo: IPriceOverrideRecordRepository,
    ):
        """Initialize handlers with injected repositories."""
        self._session = session
        self._supplier_agreement_repo = supplier_agreement_repo
        self._cost_revision_repo = cost_revision_repo
        self._cost_history_repo = cost_history_repo
        self._override_repo = override_repo
        self._uow: Optional[SQLAlchemyUnitOfWork] = None

    def with_uow(self, uow: SQLAlchemyUnitOfWork) -> "ProcurementPricingHandlers":
        """Set unit of work for event dispatch (fluent)."""
        self._uow = uow
        return self

    # ── Supplier Price Agreement Commands ──

    async def handle_create_supplier_price_agreement(
        self, cmd: CreateSupplierPriceAgreementCommand
    ) -> uuid.UUID:
        """Create new supplier price agreement in DRAFT state."""
        logger.info(
            "Creating supplier price agreement",
            extra={
                "tenant_id": str(cmd.tenant_id),
                "supplier_id": str(cmd.supplier_id),
                "material_id": str(cmd.material_id),
                "base_price": float(cmd.base_price),
            },
        )

        # Create domain entity
        agreement = SupplierPriceAgreement(
            tenant_id=cmd.tenant_id,
            supplier_id=cmd.supplier_id,
            material_id=cmd.material_id,
            base_price=cmd.base_price,
            currency_code=cmd.currency_code,
            purchase_uom_id=cmd.purchase_uom_id,
            minimum_order_quantity=cmd.minimum_order_quantity,
            effective_from=cmd.effective_from,
            effective_to=cmd.effective_to,
            quantity_tiers=cmd.quantity_tiers or [],
            notes=cmd.notes,
        )

        overlap = await self._supplier_agreement_repo.find_overlapping(
            cmd.tenant_id,
            cmd.supplier_id,
            cmd.material_id,
            agreement.effective_from,
            agreement.effective_to,
        )
        if overlap is not None:
            raise OverlappingSupplierPriceAgreementError(
                cmd.supplier_id, cmd.material_id
            )

        # Persist
        saved_agreement = await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement created",
            extra={"agreement_id": str(saved_agreement.id), "status": saved_agreement.status.value},
        )
        return saved_agreement.id

    async def handle_submit_supplier_price_agreement_for_approval(
        self, cmd: SubmitSupplierPriceAgreementForApprovalCommand
    ) -> SupplierPriceAgreementResult:
        """Submit agreement for approval (DRAFT → PENDING)."""
        agreement = await self._supplier_agreement_repo.get_by_id(cmd.tenant_id, cmd.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(cmd.agreement_id)

        try:
            agreement.submit_for_approval()
        except InvalidAgreementStateTransitionError as e:
            logger.warning(
                "Invalid state transition",
                extra={
                    "agreement_id": str(cmd.agreement_id),
                    "current_status": e.current_state,
                    "requested_status": e.requested_state,
                },
            )
            raise

        await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement submitted for approval",
            extra={"agreement_id": str(cmd.agreement_id)},
        )
        return SupplierPriceAgreementResult.from_entity(agreement)

    async def handle_approve_supplier_price_agreement(
        self, cmd: ApproveSupplierPriceAgreementCommand
    ) -> SupplierPriceAgreementResult:
        """Approve agreement (PENDING → APPROVED)."""
        agreement = await self._supplier_agreement_repo.get_by_id(cmd.tenant_id, cmd.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(cmd.agreement_id)

        try:
            agreement.approve()
        except InvalidAgreementStateTransitionError as e:
            logger.warning("Invalid state transition", extra={"agreement_id": str(cmd.agreement_id)})
            raise

        await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement approved",
            extra={"agreement_id": str(cmd.agreement_id), "approved_by": str(cmd.approved_by)},
        )
        return SupplierPriceAgreementResult.from_entity(agreement)

    async def handle_reject_supplier_price_agreement(
        self, cmd: RejectSupplierPriceAgreementCommand
    ) -> SupplierPriceAgreementResult:
        """Reject agreement back to DRAFT (PENDING → DRAFT)."""
        agreement = await self._supplier_agreement_repo.get_by_id(cmd.tenant_id, cmd.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(cmd.agreement_id)

        # Transition to DRAFT for resubmission
        try:
            agreement._transition_to(SupplierPriceAgreementStatus.DRAFT)
        except InvalidAgreementStateTransitionError:
            logger.warning(
                "Cannot reject agreement from current state",
                extra={"agreement_id": str(cmd.agreement_id), "status": agreement.status.value},
            )
            raise

        await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement rejected",
            extra={"agreement_id": str(cmd.agreement_id), "reason": cmd.rejection_reason},
        )
        return SupplierPriceAgreementResult.from_entity(agreement)

    async def handle_activate_supplier_price_agreement(
        self, cmd: ActivateSupplierPriceAgreementCommand
    ) -> SupplierPriceAgreementResult:
        """Activate agreement (APPROVED → ACTIVE). Check for conflicting active agreements."""
        agreement = await self._supplier_agreement_repo.get_by_id(cmd.tenant_id, cmd.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(cmd.agreement_id)

        overlap = await self._supplier_agreement_repo.find_overlapping(
            cmd.tenant_id,
            agreement.supplier_id,
            agreement.material_id,
            agreement.effective_from,
            agreement.effective_to,
            exclude_id=agreement.id,
        )
        if overlap is not None:
            raise OverlappingSupplierPriceAgreementError(
                agreement.supplier_id, agreement.material_id
            )

        try:
            agreement.activate()
        except InvalidAgreementStateTransitionError:
            logger.warning("Cannot activate agreement from current state", extra={"agreement_id": str(cmd.agreement_id)})
            raise

        await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement activated",
            extra={"agreement_id": str(cmd.agreement_id)},
        )
        return SupplierPriceAgreementResult.from_entity(agreement)

    async def handle_cancel_supplier_price_agreement(
        self, cmd: CancelSupplierPriceAgreementCommand
    ) -> SupplierPriceAgreementResult:
        """Cancel agreement from any non-terminal state."""
        agreement = await self._supplier_agreement_repo.get_by_id(cmd.tenant_id, cmd.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(cmd.agreement_id)

        try:
            agreement.cancel()
        except InvalidAgreementStateTransitionError:
            logger.warning("Cannot cancel agreement from current state", extra={"agreement_id": str(cmd.agreement_id)})
            raise

        await self._supplier_agreement_repo.save(agreement)

        logger.info(
            "Supplier price agreement cancelled",
            extra={"agreement_id": str(cmd.agreement_id), "reason": cmd.cancellation_reason},
        )
        return SupplierPriceAgreementResult.from_entity(agreement)

    # ── Standard Cost Revision Commands ──

    async def handle_initialize_standard_cost(
        self, cmd: InitializeStandardCostCommand
    ) -> uuid.UUID:
        """Initialize material standard cost (first time, requires approval)."""
        logger.info(
            "Initializing material standard cost",
            extra={
                "tenant_id": str(cmd.tenant_id),
                "material_id": str(cmd.material_id),
                "initial_cost": float(cmd.initial_cost),
            },
        )

        current_cost = await self._cost_revision_repo.get_material_current_cost(
            cmd.tenant_id, cmd.material_id
        )
        if current_cost is None:
            raise ValueError(f"Material {cmd.material_id} not found")

        # Create cost revision with PENDING status (requires approval)
        revision = StandardCostRevision(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            requested_by=cmd.requested_by,
            requested_cost=cmd.initial_cost,
            current_cost=current_cost,
            reason=cmd.reason,
            notes=cmd.notes,
            status=StandardCostRevisionStatus.PENDING,
        )

        saved_revision = await self._cost_revision_repo.save(revision)

        logger.info(
            "Material standard cost initialization pending approval",
            extra={"revision_id": str(saved_revision.id), "material_id": str(cmd.material_id)},
        )
        return saved_revision.id

    async def handle_create_standard_cost_revision(
        self, cmd: CreateStandardCostRevisionCommand
    ) -> uuid.UUID:
        """Create standard cost revision request (requires approval from Finance)."""
        logger.info(
            "Creating standard cost revision request",
            extra={
                "tenant_id": str(cmd.tenant_id),
                "material_id": str(cmd.material_id),
                "requested_cost": float(cmd.requested_cost),
            },
        )

        current_cost = await self._cost_revision_repo.get_material_current_cost(
            cmd.tenant_id, cmd.material_id
        )
        if current_cost is None:
            raise ValueError(f"Material {cmd.material_id} not found")

        revision = StandardCostRevision(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            requested_by=cmd.requested_by,
            requested_cost=cmd.requested_cost,
            current_cost=current_cost,
            reason=cmd.reason,
            notes=cmd.notes,
            status=StandardCostRevisionStatus.PENDING,
        )

        saved_revision = await self._cost_revision_repo.save(revision)

        logger.info(
            "Standard cost revision created",
            extra={"revision_id": str(saved_revision.id)},
        )
        return saved_revision.id

    async def handle_approve_standard_cost_revision(
        self, cmd: ApproveStandardCostRevisionCommand
    ) -> StandardCostRevisionResult:
        """Approve cost revision and update material standard cost."""
        revision = await self._cost_revision_repo.get_by_id_for_update(
            cmd.tenant_id, cmd.revision_id
        )
        if not revision:
            raise CostRevisionNotFoundError(cmd.revision_id)

        current_cost = await self._cost_revision_repo.get_material_current_cost(
            cmd.tenant_id, revision.material_id, lock=True
        )
        if current_cost is None:
            raise ValueError(f"Material {revision.material_id} not found")
        if current_cost != revision.current_cost:
            raise StaleCostRevisionError(cmd.revision_id)

        try:
            revision.approve(cmd.approved_by)
        except RequesterCannotApproveOwnRevisionError:
            logger.warning(
                "Segregation of duties violation: requester cannot approve own revision",
                extra={"revision_id": str(cmd.revision_id), "requester": str(revision.requested_by)},
            )
            raise
        except CostRevisionAlreadyReviewedError:
            logger.warning("Cost revision already reviewed", extra={"revision_id": str(cmd.revision_id)})
            raise

        if not await self._cost_revision_repo.update_material_current_cost(
            cmd.tenant_id,
            revision.material_id,
            revision.requested_cost,
            cmd.approved_by,
        ):
            raise ValueError(f"Material {revision.material_id} not found")

        await self._cost_revision_repo.save(revision)

        # Record the cost change to history (append-only audit log)
        history_entry = MaterialCostHistory(
            tenant_id=cmd.tenant_id,
            material_id=revision.material_id,
            old_cost=revision.current_cost if revision.current_cost > Decimal("0") else None,
            new_cost=revision.requested_cost,
            change_type="COST_REVISION_APPROVED",
            source_type="MANUAL",
            source_id=str(cmd.revision_id),
            approved_by=cmd.approved_by,
            notes=f"Cost revision approved: {revision.reason}",
        )
        await self._cost_history_repo.add_entry(history_entry)

        logger.info(
            "Standard cost revision approved and cost updated",
            extra={
                "revision_id": str(cmd.revision_id),
                "material_id": str(revision.material_id),
                "new_cost": float(revision.requested_cost),
                "approved_by": str(cmd.approved_by),
            },
        )
        return StandardCostRevisionResult.from_entity(revision)

    async def handle_reject_standard_cost_revision(
        self, cmd: RejectStandardCostRevisionCommand
    ) -> StandardCostRevisionResult:
        """Reject cost revision."""
        revision = await self._cost_revision_repo.get_by_id_for_update(
            cmd.tenant_id, cmd.revision_id
        )
        if not revision:
            raise CostRevisionNotFoundError(cmd.revision_id)

        try:
            revision.reject(cmd.rejection_reason)
        except CostRevisionAlreadyReviewedError:
            logger.warning("Cost revision already reviewed", extra={"revision_id": str(cmd.revision_id)})
            raise

        await self._cost_revision_repo.save(revision)

        logger.info(
            "Standard cost revision rejected",
            extra={"revision_id": str(cmd.revision_id), "reason": cmd.rejection_reason},
        )
        return StandardCostRevisionResult.from_entity(revision)

    # ── Query Handlers ──

    async def handle_get_supplier_price_agreement(
        self, query: GetSupplierPriceAgreementQuery
    ) -> SupplierPriceAgreementResult:
        """Get supplier price agreement details."""
        agreement = await self._supplier_agreement_repo.get_by_id(query.tenant_id, query.agreement_id)
        if not agreement:
            raise SupplierPriceAgreementNotFoundError(query.agreement_id)
        return SupplierPriceAgreementResult.from_entity(agreement)

    async def handle_list_supplier_price_agreements(
        self, query: ListSupplierPriceAgreementsQuery
    ) -> SupplierPriceAgreementsPage:
        """List supplier price agreements with optional filters."""
        agreements = await self._supplier_agreement_repo.list_filtered(
            query.tenant_id,
            supplier_id=query.supplier_id,
            material_id=query.material_id,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self._supplier_agreement_repo.count_filtered(
            query.tenant_id,
            supplier_id=query.supplier_id,
            material_id=query.material_id,
            status=query.status,
        )
        return SupplierPriceAgreementsPage(
            items=[SupplierPriceAgreementResult.from_entity(agreement) for agreement in agreements],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def handle_get_standard_cost_revision(
        self, query: GetStandardCostRevisionQuery
    ) -> StandardCostRevisionResult:
        """Get cost revision details."""
        revision = await self._cost_revision_repo.get_by_id(query.tenant_id, query.revision_id)
        if not revision:
            raise CostRevisionNotFoundError(query.revision_id)
        return StandardCostRevisionResult.from_entity(revision)

    async def handle_list_pending_cost_revisions(
        self, query: ListPendingCostRevisionsQuery
    ) -> StandardCostRevisionsPage:
        """List pending cost revisions awaiting approval."""
        revisions = await self._cost_revision_repo.list_pending(
            query.tenant_id, query.page, query.page_size
        )
        total = await self._cost_revision_repo.count_pending(query.tenant_id)
        return StandardCostRevisionsPage(
            items=[StandardCostRevisionResult.from_entity(revision) for revision in revisions],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def handle_get_material_cost_history(
        self, query: GetMaterialCostHistoryQuery
    ) -> List[MaterialCostHistoryResult]:
        """Get immutable cost change history for material."""
        entries = await self._cost_history_repo.list_by_material(
            query.tenant_id, query.material_id, query.limit
        )
        return [MaterialCostHistoryResult.from_entity(e) for e in entries]

    async def handle_list_price_overrides(
        self, query: ListPriceOverridesQuery
    ) -> List[PriceOverrideRecordResult]:
        """List price override records for analytics."""
        if query.material_id:
            records = await self._override_repo.list_by_material(
                query.tenant_id, query.material_id, query.limit
            )
        else:
            records = await self._override_repo.list_by_tenant(query.tenant_id, query.limit)
        return [PriceOverrideRecordResult.from_entity(r) for r in records]

    async def handle_get_active_price_agreement(
        self, query: GetActivePriceAgreementQuery
    ) -> Optional[SupplierPriceAgreementResult]:
        """Get currently active price agreement for supplier-material pair."""
        agreement = await self._supplier_agreement_repo.get_active_for_supplier_material(
            query.tenant_id, query.supplier_id, query.material_id
        )
        return SupplierPriceAgreementResult.from_entity(agreement) if agreement else None

    async def handle_list_material_cost_revisions(
        self, query: ListMaterialCostRevisionsQuery
    ) -> StandardCostRevisionsPage:
        """List all cost revisions for a material (all statuses)."""
        revisions = await self._cost_revision_repo.list_by_material(
            query.tenant_id, query.material_id, query.page, query.page_size
        )
        total = await self._cost_revision_repo.count_by_material(
            query.tenant_id, query.material_id
        )
        return StandardCostRevisionsPage(
            items=[StandardCostRevisionResult.from_entity(revision) for revision in revisions],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def handle_get_price_suggestion(
        self, query: GetPriceSuggestionQuery
    ) -> Optional[PriceSuggestionResult]:
        """Get suggested price for material (applies priority logic)."""
        # Priority logic:
        # 1. Active supplier price agreement (if supplier specified)
        # 2. Latest purchase price from same supplier
        # 3. Latest purchase price from any supplier
        # 4. Material standard cost
        
        if query.supplier_id:
            agreement = await self._supplier_agreement_repo.get_active_for_supplier_material(
                query.tenant_id, query.supplier_id, query.material_id
            )
            if agreement:
                return PriceSuggestionResult(
                    price=agreement.base_price,
                    currency=agreement.currency_code,
                    source="supplier_agreement",
                    source_id=agreement.id,
                    effective_from=agreement.effective_from,
                    effective_to=agreement.effective_to,
                )
        
        # Fallback to standard cost if no agreement found
        history = await self._cost_history_repo.list_by_material(
            query.tenant_id, query.material_id, limit=1
        )
        if history:
            entry = history[0]
            return PriceSuggestionResult(
                price=entry.new_cost,
                currency="USD",  # Default or from material
                source="standard_cost",
                source_id=entry.material_id,
                effective_from=entry.created_at,
                effective_to=None,
            )
        
        return None

    async def handle_record_price_override(
        self, cmd: RecordPriceOverrideCommand
    ) -> uuid.UUID:
        """Record a price override for analytics and audit."""
        from sqlalchemy import select
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        from backend.app.infrastructure.persistence.models.grn_model import GoodsReceiptNoteModel

        material_id = (await self._session.execute(select(MaterialModel.id).where(
            MaterialModel.id == cmd.material_id, MaterialModel.tenant_id == cmd.tenant_id,
            MaterialModel.is_deleted.is_(False),
        ))).scalar_one_or_none()
        if material_id is None:
            raise ValueError("Material not found for this tenant")
        if cmd.grn_id is not None:
            grn_id = (await self._session.execute(select(GoodsReceiptNoteModel.id).where(
                GoodsReceiptNoteModel.id == cmd.grn_id, GoodsReceiptNoteModel.tenant_id == cmd.tenant_id,
                GoodsReceiptNoteModel.is_deleted.is_(False),
            ))).scalar_one_or_none()
            if grn_id is None:
                raise ValueError("GRN not found for this tenant")
        override = PriceOverrideRecord(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            override_price=cmd.override_price,
            override_reason=cmd.override_reason,
            grn_id=cmd.grn_id,
            suggested_price=cmd.suggested_price,
            notes=cmd.notes,
            override_by=cmd.override_by,
        )
        saved = await self._override_repo.save(override)
        return saved.id
