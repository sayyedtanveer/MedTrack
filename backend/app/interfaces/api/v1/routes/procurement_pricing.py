"""
Procurement pricing API routes (Phase 2).

REST endpoints for supplier price agreements, cost revisions, and pricing analytics.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.shared.permissions import Permission
from backend.app.application.procurement.pricing.commands import (
    ApproveStandardCostRevisionCommand,
    ApproveSupplierPriceAgreementCommand,
    ActivateSupplierPriceAgreementCommand,
    CancelSupplierPriceAgreementCommand,
    CreateStandardCostRevisionCommand,
    CreateSupplierPriceAgreementCommand,
    InitializeStandardCostCommand,
    RecordPriceOverrideCommand,
    RejectStandardCostRevisionCommand,
    RejectSupplierPriceAgreementCommand,
    SubmitSupplierPriceAgreementForApprovalCommand,
)
from backend.app.application.procurement.pricing.queries import (
    GetActivePriceAgreementQuery,
    GetMaterialCostHistoryQuery,
    GetPriceSuggestionQuery,
    GetStandardCostRevisionQuery,
    GetSupplierPriceAgreementQuery,
    ListMaterialCostRevisionsQuery,
    ListPendingCostRevisionsQuery,
    ListPriceOverridesQuery,
    ListSupplierPriceAgreementsQuery,
)
from backend.app.domain.procurement.pricing.exceptions import (
    AgreementAlreadyActiveError,
    CostRevisionAlreadyReviewedError,
    CostRevisionNotFoundError,
    InvalidAgreementStateTransitionError,
    PriceOverrideRecordNotFoundError,
    RequesterCannotApproveOwnRevisionError,
    SupplierPriceAgreementNotFoundError,
)
from backend.app.infrastructure.context import get_tenant_id
from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.infrastructure.persistence.repositories.procurement_pricing_repository import (
    MaterialCostHistoryRepository,
    PriceOverrideRecordRepository,
    StandardCostRevisionRepository,
    SupplierPriceAgreementRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.procurement.pricing.handlers import (
    ProcurementPricingHandlers,
)
from backend.app.interfaces.api.v1.schemas.procurement_pricing_schemas import (
    CancelAgreementRequest,
    CreateSupplierPriceAgreementRequest,
    CreateCostRevisionRequest,
    InitializeStandardCostRequest,
    RejectAgreementRequest,
    RejectCostRevisionRequest,
    RecordPriceOverrideRequest,
    RecordMaterialPriceOverrideRequest,
    CostRevisionResponse,
    CreateCostRevisionResponse,
    ListCostRevisionsResponse,
    ListSupplierAgreementsResponse,
    SupplierPriceAgreementResponse,
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/procurement/pricing", tags=["Procurement Pricing"])


# ── Dependency: Get Async Session ──


async def _get_db_session(request: Request):
    """Get database session from container."""
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


# ── Supplier Price Agreement Endpoints ──


@router.post(
    "/supplier-price-agreements",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_AGREEMENT_WRITE.value))],
)
async def create_supplier_price_agreement(
    request_body: CreateSupplierPriceAgreementRequest,
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new supplier price agreement (DRAFT state)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")

        # Initialize repositories
        repo = SupplierPriceAgreementRepository(session)
        
        # Create handler
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        # Create command
        cmd = CreateSupplierPriceAgreementCommand(
            tenant_id=tenant_uuid,
            supplier_id=request_body.supplier_id,
            material_id=request_body.material_id,
            base_price=request_body.base_price,
            currency_code=request_body.currency_code,
            purchase_uom_id=request_body.purchase_uom_id,
            minimum_order_quantity=request_body.minimum_order_quantity,
            effective_from=request_body.effective_from,
            effective_to=request_body.effective_to,
            quantity_tiers=[tier.dict() for tier in (request_body.quantity_tiers or [])],
            notes=request_body.notes,
            created_by=user_uuid,
        )

        # Execute handler
        agreement_id = await handlers.handle_create_supplier_price_agreement(cmd)
        await session.commit()

        logger.info(
            "Supplier price agreement created",
            extra={
                "tenant_id": str(tenant_uuid),
                "user_id": str(user_uuid),
                "agreement_id": str(agreement_id),
            },
        )

        return {"id": agreement_id, "status": "DRAFT"}

    except Exception as e:
        await session.rollback()
        logger.error("Failed to create supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/supplier-price-agreements/{agreement_id}",
    response_model=SupplierPriceAgreementResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_supplier_price_agreement(
    agreement_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get supplier price agreement details."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = GetSupplierPriceAgreementQuery(tenant_id=tenant_uuid, agreement_id=agreement_uuid)
        result = await handlers.handle_get_supplier_price_agreement(query)

        return result.__dict__

    except SupplierPriceAgreementNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found")
    except Exception as e:
        logger.error("Failed to get supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/supplier-price-agreements/{agreement_id}/submit-for-approval",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_AGREEMENT_WRITE.value))],
)
async def submit_supplier_price_agreement_for_approval(
    agreement_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Submit agreement for approval (DRAFT → PENDING)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = SubmitSupplierPriceAgreementForApprovalCommand(
            tenant_id=tenant_uuid,
            agreement_id=agreement_uuid,
            submitted_by=user_uuid,
        )

        result = await handlers.handle_submit_supplier_price_agreement_for_approval(cmd)
        await session.commit()

        return result.__dict__

    except (SupplierPriceAgreementNotFoundError, InvalidAgreementStateTransitionError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to submit supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/supplier-price-agreements/{agreement_id}/approve",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_APPROVE.value))],
)
async def approve_supplier_price_agreement(
    agreement_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Approve agreement (PENDING → APPROVED)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = ApproveSupplierPriceAgreementCommand(
            tenant_id=tenant_uuid,
            agreement_id=agreement_uuid,
            approved_by=user_uuid,
        )

        result = await handlers.handle_approve_supplier_price_agreement(cmd)
        await session.commit()

        return result.__dict__

    except (SupplierPriceAgreementNotFoundError, InvalidAgreementStateTransitionError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to approve supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/supplier-price-agreements/{agreement_id}/activate",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_AGREEMENT_WRITE.value))],
)
async def activate_supplier_price_agreement(
    agreement_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Activate agreement (APPROVED → ACTIVE)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = ActivateSupplierPriceAgreementCommand(
            tenant_id=tenant_uuid,
            agreement_id=agreement_uuid,
            activated_by=user_uuid,
        )

        result = await handlers.handle_activate_supplier_price_agreement(cmd)
        await session.commit()

        return result.__dict__

    except (SupplierPriceAgreementNotFoundError, AgreementAlreadyActiveError, InvalidAgreementStateTransitionError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to activate supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Standard Cost Revision Endpoints ──


@router.post(
    "/cost-revisions/initialize",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_COST_PROPOSE.value))],
)
async def initialize_standard_cost(
    request_body: InitializeStandardCostRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Initialize material standard cost (first time, requires approval)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = InitializeStandardCostCommand(
            tenant_id=tenant_uuid,
            material_id=request_body.material_id,
            initial_cost=request_body.initial_cost,
            notes=request_body.notes,
            requested_by=user_uuid,
        )

        revision_id = await handlers.handle_initialize_standard_cost(cmd)
        await session.commit()

        logger.info(
            "Material standard cost initialization pending",
            extra={"material_id": str(request_body.material_id), "revision_id": str(revision_id)},
        )

        return {"revision_id": revision_id, "status": "PENDING"}

    except Exception as e:
        await session.rollback()
        logger.error("Failed to initialize standard cost", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/cost-revisions/{revision_id}",
    response_model=CostRevisionResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_cost_revision(
    revision_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get cost revision details."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        revision_uuid = __parse_uuid(revision_id, "revision_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = GetStandardCostRevisionQuery(tenant_id=tenant_uuid, revision_id=revision_uuid)
        result = await handlers.handle_get_standard_cost_revision(query)

        return result.__dict__

    except CostRevisionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    except Exception as e:
        logger.error("Failed to get cost revision", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/cost-revisions/{revision_id}/approve",
    response_model=CostRevisionResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_APPROVE.value))],
)
async def approve_cost_revision(
    revision_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Approve cost revision (PENDING → APPROVED)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        revision_uuid = __parse_uuid(revision_id, "revision_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = ApproveStandardCostRevisionCommand(
            tenant_id=tenant_uuid,
            revision_id=revision_uuid,
            approved_by=user_uuid,
        )

        result = await handlers.handle_approve_standard_cost_revision(cmd)
        await session.commit()

        return result.__dict__

    except RequesterCannotApproveOwnRevisionError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Segregation of duties: Cannot approve your own revision")
    except (CostRevisionNotFoundError, CostRevisionAlreadyReviewedError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to approve cost revision", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/cost-history/{material_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_material_cost_history(
    material_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    limit: int = 100,
):
    """Get material cost history (immutable audit log)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = GetMaterialCostHistoryQuery(tenant_id=tenant_uuid, material_id=material_uuid, limit=limit)
        results = await handlers.handle_get_material_cost_history(query)

        return [r.__dict__ for r in results]

    except Exception as e:
        logger.error("Failed to get material cost history", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Helper Functions ──


def __parse_uuid(value: str, field_name: str) -> UUID:
    """Parse and validate UUID."""
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} format")


# ── Additional Supplier Agreement Endpoints ──


@router.get(
    "/supplier-price-agreements",
    response_model=ListSupplierAgreementsResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def list_supplier_price_agreements(
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    supplier_id: Optional[str] = None,
    material_id: Optional[str] = None,
    agreement_status: Optional[str] = Query(None, alias="status"),
    page: int = 1,
    page_size: int = 20,
):
    """List supplier price agreements with optional filters."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id") if supplier_id else None
        material_uuid = __parse_uuid(material_id, "material_id") if material_id else None

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = ListSupplierPriceAgreementsQuery(
            tenant_id=tenant_uuid,
            supplier_id=supplier_uuid,
            material_id=material_uuid,
            status=agreement_status,
            page=page,
            page_size=page_size,
        )
        result = await handlers.handle_list_supplier_price_agreements(query)

        return {
            "items": [agreement.__dict__ for agreement in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    except Exception as e:
        logger.error("Failed to list supplier price agreements", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/supplier-price-agreements/{agreement_id}/reject",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_APPROVE.value))],
)
async def reject_supplier_price_agreement(
    agreement_id: str,
    request_body: RejectAgreementRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Reject agreement (PENDING → REJECTED or DRAFT → DRAFT with notes)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = RejectSupplierPriceAgreementCommand(
            tenant_id=tenant_uuid,
            agreement_id=agreement_uuid,
            rejected_by=user_uuid,
            rejection_reason=request_body.rejection_reason,
        )

        result = await handlers.handle_reject_supplier_price_agreement(cmd)
        await session.commit()

        return result.__dict__

    except (SupplierPriceAgreementNotFoundError, InvalidAgreementStateTransitionError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to reject supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/supplier-price-agreements/{agreement_id}/cancel",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_AGREEMENT_WRITE.value))],
)
async def cancel_supplier_price_agreement(
    agreement_id: str,
    request_body: CancelAgreementRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Cancel agreement (ACTIVE → CANCELLED)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        agreement_uuid = __parse_uuid(agreement_id, "agreement_id")

        repo = SupplierPriceAgreementRepository(session)
        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=repo,
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = CancelSupplierPriceAgreementCommand(
            tenant_id=tenant_uuid,
            agreement_id=agreement_uuid,
            cancelled_by=user_uuid,
            cancellation_reason=request_body.cancellation_reason,
        )

        result = await handlers.handle_cancel_supplier_price_agreement(cmd)
        await session.commit()

        return result.__dict__

    except (SupplierPriceAgreementNotFoundError, InvalidAgreementStateTransitionError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to cancel supplier price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/active-price-agreement",
    response_model=Optional[SupplierPriceAgreementResponse],
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_active_price_agreement(
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    supplier_id: str = Query(...),
    material_id: str = Query(...),
):
    """Get currently active price agreement for supplier-material pair."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        material_uuid = __parse_uuid(material_id, "material_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = GetActivePriceAgreementQuery(
            tenant_id=tenant_uuid,
            supplier_id=supplier_uuid,
            material_id=material_uuid,
        )
        result = await handlers.handle_get_active_price_agreement(query)

        return result.__dict__ if result else None

    except Exception as e:
        logger.error("Failed to get active price agreement", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Additional Cost Revision Endpoints ──


@router.get(
    "/cost-revisions",
    response_model=ListCostRevisionsResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def list_cost_revisions(
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    material_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """List cost revisions for a material or all pending revisions."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id") if material_id else None

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        if material_uuid:
            query = ListMaterialCostRevisionsQuery(
                tenant_id=tenant_uuid,
                material_id=material_uuid,
                page=page,
                page_size=page_size,
            )
            results = await handlers.handle_list_material_cost_revisions(query)
        else:
            query = ListPendingCostRevisionsQuery(
                tenant_id=tenant_uuid,
                page=page,
                page_size=page_size,
            )
            results = await handlers.handle_list_pending_cost_revisions(query)

        return {
            "items": [revision.__dict__ for revision in results.items],
            "total": results.total,
            "page": results.page,
            "page_size": results.page_size,
        }

    except Exception as e:
        logger.error("Failed to list cost revisions", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/cost-revisions",
    response_model=CreateCostRevisionResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_COST_PROPOSE.value))],
)
async def create_cost_revision(
    request_body: CreateCostRevisionRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Create a standard cost revision request (requires approval)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = CreateStandardCostRevisionCommand(
            tenant_id=tenant_uuid,
            material_id=request_body.material_id,
            requested_cost=request_body.requested_cost,
            reason=request_body.reason,
            notes=request_body.notes,
            requested_by=user_uuid,
        )

        revision_id = await handlers.handle_create_standard_cost_revision(cmd)
        revision = await handlers.handle_get_standard_cost_revision(
            GetStandardCostRevisionQuery(tenant_id=tenant_uuid, revision_id=revision_id)
        )
        await session.commit()

        return {**revision.__dict__, "revision_id": revision_id}

    except Exception as e:
        await session.rollback()
        logger.error("Failed to create cost revision", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/cost-revisions/{revision_id}/reject",
    response_model=CostRevisionResponse,
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_APPROVE.value))],
)
async def reject_cost_revision(
    revision_id: str,
    request_body: RejectCostRevisionRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Reject cost revision (PENDING → REJECTED)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        revision_uuid = __parse_uuid(revision_id, "revision_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = RejectStandardCostRevisionCommand(
            tenant_id=tenant_uuid,
            revision_id=revision_uuid,
            rejected_by=user_uuid,
            rejection_reason=request_body.rejection_reason,
        )

        result = await handlers.handle_reject_standard_cost_revision(cmd)
        await session.commit()

        return result.__dict__

    except (CostRevisionNotFoundError, CostRevisionAlreadyReviewedError) as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Failed to reject cost revision", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Price Suggestion & Override Endpoints ──


@router.get(
    "/price-suggestions/{material_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_price_suggestion(
    material_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    supplier_id: Optional[str] = None,
    quantity: Optional[int] = None,
):
    """Get suggested price for material (applies priority logic)."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id") if supplier_id else None

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = GetPriceSuggestionQuery(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
            quantity=quantity,
            include_source_info=True,
        )
        result = await handlers.handle_get_price_suggestion(query)

        return result.__dict__ if result else {"error": "No price available"}

    except Exception as e:
        logger.error("Failed to get price suggestion", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/price-overrides",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_OVERRIDE.value))],
)
async def record_price_override(
    request_body: RecordMaterialPriceOverrideRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Record a price override for a GRN or PO."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        user_uuid = __parse_uuid(user_id, "user_id")

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        cmd = RecordPriceOverrideCommand(
            tenant_id=tenant_uuid,
            material_id=request_body.material_id,
            override_price=request_body.override_price,
            override_reason=request_body.override_reason,
            grn_id=request_body.grn_id,
            suggested_price=request_body.suggested_price,
            notes=request_body.notes,
            override_by=user_uuid,
        )

        override_id = await handlers.handle_record_price_override(cmd)
        await session.commit()

        return {"override_id": override_id}

    except Exception as e:
        await session.rollback()
        logger.error("Failed to record price override", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/price-overrides",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def list_price_overrides(
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    material_id: Optional[str] = None,
    grn_id: Optional[str] = None,
    limit: int = 100,
):
    """List price override records for analytics."""
    try:
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id") if material_id else None
        grn_uuid = __parse_uuid(grn_id, "grn_id") if grn_id else None

        handlers = ProcurementPricingHandlers(
            session=session,
            supplier_agreement_repo=SupplierPriceAgreementRepository(session),
            cost_revision_repo=StandardCostRevisionRepository(session),
            cost_history_repo=MaterialCostHistoryRepository(session),
            override_repo=PriceOverrideRecordRepository(session),
        )

        query = ListPriceOverridesQuery(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            grn_id=grn_uuid,
            limit=limit,
        )
        results = await handlers.handle_list_price_overrides(query)

        return [r.__dict__ for r in results]

    except Exception as e:
        logger.error("Failed to list price overrides", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



# ── New 6-Level Pricing Engine Endpoints (Priority 2.4+) ──


@router.get(
    "/suggestions/six-level/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_six_level_pricing_suggestions(
    material_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get pricing suggestions using 6-level hierarchy fallback logic.
    
    Levels (in priority order):
    1. Active supplier agreement (HIGH confidence)
    2. Approved quotation (MEDIUM confidence)
    3. Latest purchase same supplier (MEDIUM confidence)
    4. Latest purchase any supplier - benchmarking (LOW confidence)
    5. Approved standard cost (LOW confidence)
    6. Manual (None - no suggestion)
    """
    try:
        from backend.app.application.procurement.pricing.po_pricing_engine import POPricingEngine
        from backend.app.application.procurement.pricing.quotation_lookup_service import SupplierQuotationLookupService
        from backend.app.application.procurement.pricing.purchase_history_lookup_service import PurchaseHistoryLookupService
        from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import AnySupplierHistoryLookupService
        from backend.app.interfaces.api.v1.schemas.procurement_pricing_schemas import PriceSuggestionResponse
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        
        # Create pricing engine with lookup services
        quotation_service = SupplierQuotationLookupService(session)
        history_service = PurchaseHistoryLookupService(session)
        any_supplier_service = AnySupplierHistoryLookupService(session)
        engine = POPricingEngine(
            quotation_service=quotation_service,
            history_service=history_service,
            any_supplier_service=any_supplier_service,
        )
        
        # Get pricing suggestions
        pricing = await engine.get_pricing_suggestions(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
        )
        
        if pricing:
            response = PriceSuggestionResponse(
                material_id=material_uuid,
                supplier_id=supplier_uuid,
                suggested_price=pricing.suggested_price,
                pricing_source=pricing.pricing_source,
                confidence_level=pricing.confidence_level,
                level_number=pricing.level_number,
                rationale=pricing.rationale,
            )
            return response.dict()
        else:
            # Level 6: Manual - no suggestion
            return {"message": "No pricing available - manual pricing required", "level_number": 6}
    
    except Exception as e:
        logger.error("Failed to get 6-level pricing suggestions", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/analysis/six-level/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_six_level_pricing_analysis(
    material_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get detailed analysis of all 6 pricing levels.
    Shows what's available at each level for transparency.
    """
    try:
        from backend.app.application.procurement.pricing.po_pricing_engine import POPricingEngine
        from backend.app.application.procurement.pricing.quotation_lookup_service import SupplierQuotationLookupService
        from backend.app.application.procurement.pricing.purchase_history_lookup_service import PurchaseHistoryLookupService
        from backend.app.application.procurement.pricing.any_supplier_history_lookup_service import AnySupplierHistoryLookupService
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        
        # Create pricing engine
        quotation_service = SupplierQuotationLookupService(session)
        history_service = PurchaseHistoryLookupService(session)
        any_supplier_service = AnySupplierHistoryLookupService(session)
        engine = POPricingEngine(
            quotation_service=quotation_service,
            history_service=history_service,
            any_supplier_service=any_supplier_service,
        )
        
        # Get full analysis
        analysis = await engine.get_pricing_analysis(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
        )
        
        return analysis.dict()
    
    except Exception as e:
        logger.error("Failed to get 6-level pricing analysis", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Price Override Tracking Endpoints (Priority 2.5) ──


@router.post(
    "/overrides/record-override/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_OVERRIDE.value))],
)
async def record_pricing_override(
    material_id: str,
    supplier_id: str,
    request_body: RecordPriceOverrideRequest,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_current_user_id),
):
    """Record when user overrides the suggested price (for audit trail)."""
    try:
        from backend.app.application.procurement.pricing.price_override_service import PriceOverrideService
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        user_uuid = __parse_uuid(user_id, "user_id")
        
        service = PriceOverrideService(session)
        
        record = await service.record_override(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
            original_suggested_price=request_body.original_suggested_price,
            override_price=request_body.override_price,
            override_reason=request_body.override_reason,
            override_source=request_body.override_source,
            overridden_by=user_uuid,
        )
        
        await session.commit()
        
        return {
            "id": record.id,
            "material_id": record.material_id,
            "supplier_id": record.supplier_id,
            "suggested_price": float(record.original_suggested_price),
            "override_price": float(record.override_price),
            "created_at": record.created_at.isoformat(),
        }
    
    except Exception as e:
        await session.rollback()
        logger.error("Failed to record price override", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/overrides/history/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_override_history(
    material_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get price override history for a material-supplier pair."""
    try:
        from backend.app.application.procurement.pricing.price_override_service import PriceOverrideService
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        
        service = PriceOverrideService(session)
        
        history = await service.get_override_history_for_material_supplier(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
        )
        
        return [record.to_dict() for record in history]
    
    except Exception as e:
        logger.error("Failed to get override history", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/overrides/statistics/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_override_statistics(
    material_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get statistics on price overrides for a material-supplier pair."""
    try:
        from backend.app.application.procurement.pricing.price_override_service import PriceOverrideService
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        
        service = PriceOverrideService(session)
        
        stats = await service.get_override_statistics(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
        )
        
        return stats
    
    except Exception as e:
        logger.error("Failed to get override statistics", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/overrides/trends/{material_id}/{supplier_id}",
    dependencies=[Depends(require_permission(Permission.PROCUREMENT_PRICING_READ.value))],
)
async def get_override_trends(
    material_id: str,
    supplier_id: str,
    session: AsyncSession = Depends(_get_db_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Analyze price override trends over time."""
    try:
        from backend.app.application.procurement.pricing.price_override_service import PriceOverrideService
        
        tenant_uuid = __parse_uuid(tenant_id, "tenant_id")
        material_uuid = __parse_uuid(material_id, "material_id")
        supplier_uuid = __parse_uuid(supplier_id, "supplier_id")
        
        service = PriceOverrideService(session)
        
        trend = await service.analyze_override_trends(
            tenant_id=tenant_uuid,
            material_id=material_uuid,
            supplier_id=supplier_uuid,
        )
        
        return trend
    
    except Exception as e:
        logger.error("Failed to analyze override trends", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
