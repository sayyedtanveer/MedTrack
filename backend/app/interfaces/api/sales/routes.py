"""Sales API routes (FastAPI endpoints) with full Dependency Injection."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from backend.app.domain.sales.repositories.client_repository import ClientRepository
from backend.app.domain.sales.repositories.sales_order_repository import SalesOrderRepository
from backend.app.domain.sales.repositories.price_list_repository import PriceListRepository
from backend.app.infrastructure.persistence.models.sales_models import ClientModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.finance.notification_service import NotificationService
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.application.rbac.service import role_has_permission
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

from backend.app.interfaces.api.sales.schemas import (
    ClientCreateRequest,
    ClientUpdateRequest,
    ClientResponse,
    ClientListResponse,
    ClientCreditCheckResponse,
    PriceListRequest,
    PriceListUpdateRequest,
    PriceListLineRequest,
    PriceListResponse,
    PriceListListResponse,
    SalesOrderCreateRequest,
    SalesOrderResponse,
    SalesOrderListResponse,
    SalesOrderLineCreateRequest,
    ApplyDiscountRequest,
    ApprovalActionRequest,
    ConfirmOrderRequest,
    ShipOrderRequest,
    CancelOrderRequest,
    OrderStatusResponse,
)
from backend.app.application.sales.commands import _PRICE_LIST_UNSET
from backend.app.application.sales import (
    # Commands
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
    UpdatePriceListCommand,
    CreateSalesOrderCommand,
    AddLineToSalesOrderCommand,
    RemoveLineFromSalesOrderCommand,
    ApplyDiscountToOrderCommand,
    SubmitSalesOrderForApprovalCommand,
    ApproveSalesOrderCommand,
    RejectSalesOrderCommand,
    ConfirmSalesOrderCommand,
    CancelSalesOrderCommand,
    ShipOrderCommand,
    DeliverOrderCommand,
    # Queries
    GetClientByIdQuery,
    GetClientByCodeQuery,
    ListClientsQuery,
    GetSalesOrderByIdQuery,
    GetSalesOrderByNumberQuery,
    ListClientOrdersQuery,
    ListOrdersByDateRangeQuery,
    ListDraftOrdersQuery,
    ListOrdersByDeliveryDateQuery,
    GetProductPriceQuery,
    CheckClientCreditQuery,
    GetPriceListByIdQuery,
    ListPriceListsQuery,
    GetOrderCountByStatusQuery,
    # Handlers
    CreateClientCommandHandler,
    UpdateClientCommandHandler,
    DeactivateClientCommandHandler,
    CreatePriceListCommandHandler,
    AddPriceListLineCommandHandler,
    UpdatePriceListLineCommandHandler,
    RemovePriceListLineCommandHandler,
    UpdatePriceListCommandHandler,
    CreateSalesOrderCommandHandler,
    AddLineToSalesOrderCommandHandler,
    RemoveLineFromSalesOrderCommandHandler,
    ApplyDiscountToOrderCommandHandler,
    SubmitSalesOrderForApprovalCommandHandler,
    ApproveSalesOrderCommandHandler,
    RejectSalesOrderCommandHandler,
    ConfirmSalesOrderCommandHandler,
    CancelSalesOrderCommandHandler,
    ShipOrderCommandHandler,
    DeliverOrderCommandHandler,
    GetClientByIdQueryHandler,
    GetClientByCodeQueryHandler,
    ListClientsQueryHandler,
    GetSalesOrderByIdQueryHandler,
    GetSalesOrderByNumberQueryHandler,
    ListClientOrdersQueryHandler,
    ListOrdersByDateRangeQueryHandler,
    ListDraftOrdersQueryHandler,
    ListOrdersByDeliveryDateQueryHandler,
    GetProductPriceQueryHandler,
    CheckClientCreditQueryHandler,
    GetPriceListByIdQueryHandler,
    ListPriceListsQueryHandler,
    GetOrderCountByStatusQueryHandler,
)

# Create router
router = APIRouter(prefix="/sales", tags=["sales"])
logger = logging.getLogger(__name__)


def _normalize_email(email: Optional[str]) -> Optional[str]:
    cleaned = (email or "").strip().lower()
    return cleaned or None


async def _ensure_client_email_available(
    session,
    tenant_id: UUID,
    email: Optional[str],
    exclude_client_id: Optional[UUID] = None,
) -> Optional[str]:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None

    existing_users = (
        await session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
                func.lower(UserModel.email) == normalized_email,
            )
        )
    ).scalars().all()

    for user in existing_users:
        if exclude_client_id and user.client_id == exclude_client_id:
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists as a user login. Use a different client email or link the existing user to this client.",
        )

    client_stmt = select(ClientModel.id).where(
        ClientModel.tenant_id == tenant_id,
        ClientModel.is_deleted.is_(False),
        func.lower(ClientModel.email) == normalized_email,
    )
    if exclude_client_id:
        client_stmt = client_stmt.where(ClientModel.id != exclude_client_id)

    existing_client_id = (await session.execute(client_stmt)).scalar_one_or_none()
    if existing_client_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists for another client.",
        )

    return normalized_email


async def _resolve_order_approver_id(session, tenant_id: UUID) -> Optional[UUID]:
    """Find the first active user whose role can approve sales orders."""
    users = (
        await session.execute(
            select(UserModel)
            .where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_active.is_(True),
                UserModel.is_deleted.is_(False),
            )
            .order_by(UserModel.created_at.asc())
        )
    ).scalars().all()
    for user in users:
        if await role_has_permission(session, tenant_id, user.role, "sales:approve_order"):
            return user.id
    return None


def _status_name(order) -> str:
    status_value = getattr(order, "status", "")
    return getattr(status_value, "name", str(status_value)).upper()


def _build_dispatch_notification_service(session):
    """Create a NotificationService for dispatch_queue_updated notifications (Gap #4)."""
    from backend.app.application.notifications.notification_service import (
        NotificationService as OperationalNotificationService,
    )
    return OperationalNotificationService(session)


async def _notify_client_order_status(
    session,
    container,
    tenant_id: UUID,
    order,
    *,
    notification_type: str,
    title: str,
    message: str,
) -> None:
    """Notify users linked to the order client, scoped by tenant/client."""
    notification_service = NotificationService(
        session,
        email_service=getattr(container, "email_service", None),
        connection_manager=getattr(container, "connection_manager", None),
    )
    user_ids = (
        await session.execute(
            select(UserModel.id).where(
                UserModel.tenant_id == tenant_id,
                UserModel.client_id == order.client_id,
                UserModel.is_active.is_(True),
                UserModel.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    for client_user_id in user_ids:
        await notification_service.send(
            tenant_id=tenant_id,
            user_id=client_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            reference_type="sales_order",
            reference_id=order.id,
        )


async def _notify_order_action_owner(
    session,
    container,
    tenant_id: UUID,
    order,
) -> None:
    """Notify the next internal role that needs to act on the order."""
    notification_service = NotificationService(
        session,
        email_service=getattr(container, "email_service", None),
        connection_manager=getattr(container, "connection_manager", None),
    )
    order_status = _status_name(order)
    order_number = str(order.order_number)

    if order_status in {"PRODUCTION", "PROCESSING"}:
        work_order_ids = {
            line.work_order_id
            for line in getattr(order, "lines", [])
            if getattr(line, "work_order_id", None)
        }
        if work_order_ids:
            for work_order_id in work_order_ids:
                await notification_service.broadcast_to_permission(
                    tenant_id=tenant_id,
                    permission="manufacturing:write",
                    notification_type="WORK_ORDER_ACTION_REQUIRED",
                    title=f"Production action required for {order_number}",
                    message=f"Sales order {order_number} was approved and needs production work order execution.",
                    reference_type="work_order",
                    reference_id=work_order_id,
                )
            await _notify_purchase_order_owners(
                session=session,
                container=container,
                tenant_id=tenant_id,
                work_order_ids=work_order_ids,
                order_number=order_number,
            )
            return

        await notification_service.broadcast_to_permission(
            tenant_id=tenant_id,
            permission="manufacturing:write",
            notification_type="PRODUCTION_ACTION_REQUIRED",
            title=f"Production action required for {order_number}",
            message=f"Sales order {order_number} was approved and is waiting for production execution.",
            reference_type="sales_order",
            reference_id=order.id,
        )
        return

    if order_status in {"READY", "CONFIRMED"}:
        await notification_service.broadcast_to_permission(
            tenant_id=tenant_id,
            permission="inventory:write",
            notification_type="ORDER_READY_TO_FULFILL",
            title=f"Order {order_number} is ready to fulfill",
            message=f"Sales order {order_number} has stock allocated and is ready for shipment handling.",
            reference_type="sales_order",
            reference_id=order.id,
        )


async def _notify_purchase_order_owners(
    *,
    session,
    container,
    tenant_id: UUID,
    work_order_ids: set[UUID],
    order_number: str,
) -> None:
    """Notify only the supplier users linked to auto-created shortage POs."""
    if not work_order_ids:
        return

    from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel

    notification_service = NotificationService(
        session,
        email_service=getattr(container, "email_service", None),
        connection_manager=getattr(container, "connection_manager", None),
    )
    filters = [
        PurchaseOrderModel.notes.ilike(f"%{work_order_id}%")
        for work_order_id in work_order_ids
    ]
    purchase_orders = (
        await session.execute(
            select(PurchaseOrderModel.id, PurchaseOrderModel.po_number, PurchaseOrderModel.supplier_id).where(
                PurchaseOrderModel.tenant_id == tenant_id,
                PurchaseOrderModel.is_deleted.is_(False),
                or_(*filters),
            )
        )
    ).all()

    for po_id, po_number, supplier_id in purchase_orders:
        supplier_user_ids = (
            await session.execute(
                select(UserModel.id).where(
                    UserModel.tenant_id == tenant_id,
                    UserModel.supplier_id == supplier_id,
                    UserModel.is_active.is_(True),
                    UserModel.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        for supplier_user_id in supplier_user_ids:
            await notification_service.send(
                tenant_id=tenant_id,
                user_id=supplier_user_id,
                notification_type="SUPPLIER_PO_ACTION_REQUIRED",
                title=f"Purchase order {po_number} needs supplier action",
                message=f"Sales order {order_number} created a material shortage PO. Please review and acknowledge it.",
                reference_type="purchase_order",
                reference_id=po_id,
            )


async def _notify_sales_order_submitted(session, container, tenant_id: UUID, order) -> None:
    notification_service = NotificationService(
        session,
        email_service=getattr(container, "email_service", None),
        connection_manager=getattr(container, "connection_manager", None),
    )
    client_label = getattr(order, "client_name", None) or str(order.client_id)
    if getattr(order, "client_code", None):
        client_label = f"{client_label} ({order.client_code})"
    item_summary = getattr(order, "item_summary", None) or "No line items"
    await notification_service.broadcast_to_permission(
        tenant_id=tenant_id,
        permission="sales:approve_order",
        notification_type="SALES_ORDER_PENDING_APPROVAL",
        title=f"Order {order.order_number} needs approval",
        message=(
            f"{client_label} requested {item_summary}. "
            f"Open sales order {order.order_number} to review and approve."
        ),
        reference_type="sales_order",
        reference_id=order.id,
    )


# ==================== CLIENT ENDPOINTS ====================

@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales:write"))])
async def create_client(
    body: ClientCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new client."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateClientCommandHandler(client_repo, uow)
        try:
            email = await _ensure_client_email_available(session, tenant_id, body.email)
            
            # Fetch user role for policy validation
            user = await session.get(UserModel, user_id)
            user_is_admin = user.role == "admin" if user else False

            item_code_service = ItemCodeService(session)
            if body.code:
                code_result = await item_code_service.validate_manual_code_with_policy(
                    tenant_id=tenant_id,
                    entity_type="customer",
                    code=body.code,
                    user_is_admin=user_is_admin,
                    entity_name=body.name,
                    user_id=user_id,
                )
                final_code = code_result.code
            else:
                final_code = await item_code_service.generate_for_entity(
                    tenant_id=tenant_id,
                    entity_type="customer",
                    entity_name=body.name,
                    user_id=user_id,
                )

            client_id = await handler.handle(
                CreateClientCommand(
                    tenant_id=tenant_id,
                    code=final_code,
                    name=body.name,
                    email=email,
                    phone=body.phone,
                    address=body.address,
                    gst_number=body.gst_number,
                    credit_limit=body.credit_limit,
                    payment_terms_days=body.payment_terms_days,
                )
            )
            client = await client_repo.get_by_id(UUID(str(client_id)), tenant_id)
            return client.to_dict() if client else None
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating client: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/clients/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_client(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get client details."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = GetClientByIdQueryHandler(client_repo)
        try:
            return await handler.handle(
                GetClientByIdQuery(
                    tenant_id=tenant_id,
                    client_id=client_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/clients", response_model=ClientListResponse, dependencies=[Depends(require_permission("sales:read"))])
async def list_clients(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List clients with pagination and filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = ListClientsQueryHandler(client_repo)
        try:
            items = await handler.handle(
                ListClientsQuery(
                    tenant_id=tenant_id,
                    is_active=is_active,
                    search=search,
                    limit=limit,
                    offset=offset,
                )
            )
            total = len(items)  # Would typically come from repository count method
            return ClientListResponse(items=items, total=total, limit=limit, offset=offset)
        except Exception as e:
            import traceback
            with open("C:/Users/sayye/source/repos/MedTrack/backend/debug_trace.txt", "w") as f:
                f.write(traceback.format_exc())
            logger.exception(f"Error listing clients: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.patch("/clients/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_permission("sales:write"))])
async def update_client(
    client_id: UUID,
    body: ClientUpdateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update client information."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateClientCommandHandler(client_repo, uow)
        try:
            email = await _ensure_client_email_available(session, tenant_id, body.email, client_id)

            # Determine which fields were explicitly provided in the request body
            patch = body.model_dump(exclude_unset=True)

            # Cross-tenant validation for default_price_list_id when a non-null value is sent
            if "default_price_list_id" in patch and patch["default_price_list_id"] is not None:
                price_list_repo = PriceListRepository(session)
                pl = await price_list_repo.get_by_id(patch["default_price_list_id"], tenant_id)
                if pl is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Price list not found or belongs to a different tenant",
                    )

            # Build the command — pass the sentinel when the field was not sent,
            # or the actual value (UUID or None) when it was explicitly included.
            await handler.handle(
                UpdateClientCommand(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name=body.name,
                    email=email,
                    phone=body.phone,
                    address=body.address,
                    gst_number=body.gst_number,
                    credit_limit=body.credit_limit,
                    payment_terms_days=body.payment_terms_days,
                    default_price_list_id=(
                        patch["default_price_list_id"]
                        if "default_price_list_id" in patch
                        else _PRICE_LIST_UNSET
                    ),
                )
            )
            client = await client_repo.get_by_id(client_id, tenant_id)
            return client.to_dict() if client else None
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error updating client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("sales:write"))])
async def deactivate_client(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Deactivate a client (soft delete)."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = DeactivateClientCommandHandler(client_repo, uow)
        try:
            await handler.handle(
                DeactivateClientCommand(
                    tenant_id=tenant_id,
                    client_id=client_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error deactivating client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Deactivation failed")


@router.get("/clients/{client_id}/credit", response_model=ClientCreditCheckResponse, dependencies=[Depends(require_permission("sales:read"))])
async def check_client_credit(
    client_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    order_total: Optional[float] = None,
):
    """Check client credit availability."""
    container = get_container(request)
    async with container.session_factory() as session:
        client_repo = ClientRepository(session)
        handler = CheckClientCreditQueryHandler(client_repo)
        try:
            return await handler.handle(
                CheckClientCreditQuery(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    order_total=order_total,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error checking credit for client {client_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Credit check failed")


# ==================== SALES ORDER ENDPOINTS ====================

@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales:write"))])
async def create_order(
    body: SalesOrderCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new sales order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateSalesOrderCommandHandler(order_repo, uow)
        try:
            approver_id = await _resolve_order_approver_id(session, tenant_id)
            order_id = await handler.handle(
                CreateSalesOrderCommand(
                    tenant_id=tenant_id,
                    client_id=body.client_id,
                    order_date=body.order_date,
                    delivery_date=body.delivery_date,
                    created_by=str(user_id),
                    notes=body.notes,
                    approver_id=approver_id,
                )
            )
            order = await order_repo.get_by_id(UUID(str(order_id)), tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating sales order: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/orders/draft", response_model=SalesOrderListResponse, dependencies=[Depends(require_permission("sales:read"))])
async def list_draft_orders(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    limit: int = Query(50, ge=1, le=200),
):
    """List draft orders waiting for confirmation."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = ListDraftOrdersQueryHandler(order_repo)
        try:
            items = await handler.handle(
                ListDraftOrdersQuery(
                    tenant_id=tenant_id,
                    limit=limit,
                )
            )
            total = len(items)
            return SalesOrderListResponse(items=items, total=total, limit=limit, offset=0)
        except Exception as e:
            logger.exception(f"Error listing draft orders: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.get("/orders/{order_id}", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_order(
    order_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order details with full information."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetSalesOrderByIdQueryHandler(order_repo)
        try:
            return await handler.handle(
                GetSalesOrderByIdQuery(
                    tenant_id=tenant_id,
                    order_id=order_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/orders/number/{order_number}", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_order_by_number(
    order_number: str,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order by order number."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetSalesOrderByNumberQueryHandler(order_repo)
        try:
            return await handler.handle(
                GetSalesOrderByNumberQuery(
                    tenant_id=tenant_id,
                    order_number=order_number,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving order by number {order_number}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/orders", response_model=SalesOrderListResponse, dependencies=[Depends(require_permission("sales:read"))])
async def list_orders(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    client_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List orders with filtering by client or date range."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        
        try:
            if client_id:
                handler = ListClientOrdersQueryHandler(order_repo)
                items = await handler.handle(
                    ListClientOrdersQuery(
                        tenant_id=tenant_id,
                        client_id=client_id,
                        status=status_filter,
                        limit=limit,
                        offset=offset,
                    )
                )
            elif start_date and end_date:
                handler = ListOrdersByDateRangeQueryHandler(order_repo)
                items = await handler.handle(
                    ListOrdersByDateRangeQuery(
                        tenant_id=tenant_id,
                        start_date=start_date,
                        end_date=end_date,
                        status=status_filter,
                        limit=limit,
                        offset=offset,
                    )
                )
            else:
                raise ValueError("Provide client_id or both start_date and end_date")
            
            total = len(items)  # Would typically come from repository count method
            return SalesOrderListResponse(items=items, total=total, limit=limit, offset=offset)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error listing orders: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")

@router.post("/orders/{order_id}/lines", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales:write"))])
async def add_order_line(
    order_id: UUID,
    body: SalesOrderLineCreateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Add a line item to an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        price_list_repo = PriceListRepository(session)
        from functools import partial
        from backend.app.domain.sales.services.pricing_service import PricingService
        from backend.app.infrastructure.services.sales_providers import get_variant_selling_price
        variant_price_provider = partial(get_variant_selling_price, session)
        pricing_service = PricingService(price_list_repo, variant_price_provider)
        
        handler = AddLineToSalesOrderCommandHandler(order_repo, pricing_service, uow)
        try:
            await handler.handle(
                AddLineToSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    uom_id=body.uom_id,
                    quantity=body.quantity,
                    tax_rate=body.tax_rate,
                    unit_price=body.unit_price,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error adding line to order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line addition failed")


@router.delete("/orders/{order_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("sales:write"))])
async def remove_order_line(
    order_id: UUID,
    line_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Remove a line from an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemoveLineFromSalesOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                RemoveLineFromSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    line_id=line_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error removing line {line_id} from order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line removal failed")


@router.post("/orders/{order_id}/discount", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def apply_discount(
    order_id: UUID,
    body: ApplyDiscountRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Apply discount to order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = ApplyDiscountToOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                ApplyDiscountToOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    discount_amount=body.discount_amount,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error applying discount to order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Discount application failed")


@router.post("/orders/{order_id}/submit-approval", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def submit_order_for_approval(
    order_id: UUID,
    body: ApprovalActionRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Submit a draft order to the manager/admin approval queue."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = SubmitSalesOrderForApprovalCommandHandler(order_repo, uow)
        try:
            approver_id = await _resolve_order_approver_id(session, tenant_id)
            await handler.handle(
                SubmitSalesOrderForApprovalCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    submitted_by=str(user_id),
                    approver_id=approver_id,
                    notes=body.notes,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                await _notify_sales_order_submitted(session, container, tenant_id, order)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error submitting order for approval: {str(e)}")
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Approval submission failed: {str(e)} - {tb}")


@router.post(
    "/orders/{order_id}/approve",
    response_model=SalesOrderResponse,
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
async def approve_order(
    order_id: UUID,
    body: ApprovalActionRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Approve an order and immediately start execution."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        approve_handler = ApproveSalesOrderCommandHandler(order_repo, uow)

        from backend.app.domain.sales.services.credit_validation_service import CreditValidationService
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService

        credit_service = CreditValidationService(client_repo)
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(
            wo_handler,
            uow,
            created_by=user_id,
        ).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)
        confirm_handler = ConfirmSalesOrderCommandHandler(order_repo, client_repo, credit_service, inv_service, uow, notification_service=_build_dispatch_notification_service(session))

        try:
            await approve_handler.handle(
                ApproveSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    approver_id=user_id,
                    notes=body.notes,
                )
            )
            await confirm_handler.handle(
                ConfirmSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    confirmed_by=str(user_id),
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                order_status = _status_name(order).replace("_", " ").title()
                await _notify_client_order_status(
                    session,
                    container,
                    tenant_id,
                    order,
                    notification_type="ORDER_APPROVED",
                    title=f"Order {order.order_number} approved",
                    message=f"Your order has been approved and is now {order_status}.",
                )
                await _notify_order_action_owner(session, container, tenant_id, order)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error approving order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Approval failed")


@router.post(
    "/orders/{order_id}/reject",
    response_model=SalesOrderResponse,
    dependencies=[Depends(require_permission("sales:approve_order"))],
)
async def reject_order(
    order_id: UUID,
    body: ApprovalActionRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Reject a submitted order and stop execution."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RejectSalesOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                RejectSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    approver_id=user_id,
                    notes=body.notes,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                await _notify_client_order_status(
                    session,
                    container,
                    tenant_id,
                    order,
                    notification_type="ORDER_REJECTED",
                    title=f"Order {order.order_number} rejected",
                    message="Your order was rejected during approval review. Please contact support for details.",
                )
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error rejecting order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rejection failed")


@router.post("/orders/{order_id}/confirm", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def confirm_order(
    order_id: UUID,
    body: ConfirmOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Confirm order (APPROVED → CONFIRMED) with FG availability check (Gap #2)."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        from backend.app.domain.sales.services.credit_validation_service import CreditValidationService
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import (
            SalesInventoryIntegrationService,
            FGAvailabilityCheckService,
        )
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService

        credit_service = CreditValidationService(client_repo)
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(
            wo_handler,
            uow,
            created_by=user_id,
        ).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)

        # Gap #2: wire FGAvailabilityCheckService (all-or-nothing per line, SELECT FOR UPDATE)
        fg_check_service = FGAvailabilityCheckService(
            inv_integ,
            mfg_integ,
            created_by=user_id,
        )

        handler = ConfirmSalesOrderCommandHandler(
            order_repo,
            client_repo,
            credit_service,
            inv_service,
            uow,
            fg_check_service=fg_check_service,
            notification_service=_build_dispatch_notification_service(session),
        )
        from backend.app.domain.manufacturing.exceptions import InsufficientStockError as _StockError
        try:
            await handler.handle(
                ConfirmSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    confirmed_by=body.confirmed_by,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                order_status = _status_name(order).replace("_", " ").title()
                await _notify_client_order_status(
                    session,
                    container,
                    tenant_id,
                    order,
                    notification_type="ORDER_CONFIRMED",
                    title=f"Order {order.order_number} confirmed",
                    message=f"Your order has entered execution and is now {order_status}.",
                )
                await _notify_order_action_owner(session, container, tenant_id, order)
            return order.to_dict() if order else None
        except _StockError as e:
            # Concurrent reservation conflict — Req 14.6 / Cross-Cutting Req A
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient stock — concurrent reservation conflict",
            )
        except ValueError as e:
            logger.warning(f"Confirm order {order_id} rejected: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error confirming order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Confirmation failed")


@router.post("/orders/{order_id}/ship", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def ship_order(
    order_id: UUID,
    body: ShipOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Record shipment for order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService
        
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(
            wo_handler,
            uow,
            created_by=user_id,
        ).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)
        
        handler = ShipOrderCommandHandler(order_repo, inv_service, uow)
        try:
            await handler.handle(
                ShipOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    line_shipments=body.line_shipments,
                    shipped_by=body.shipped_by,
                )
            )
            try:
                from backend.app.application.delivery.delivery_service import DeliveryService

                await DeliveryService(session).record_sales_shipment_document(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    created_by=user_id,
                    line_shipments=body.line_shipments,
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning(
                    "Delivery document was not recorded for order %s. "
                    "Run the delivery module migration to enable delivery documents.",
                    order_id,
                    exc_info=True,
                )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                await _notify_client_order_status(
                    session,
                    container,
                    tenant_id,
                    order,
                    notification_type="ORDER_SHIPPED",
                    title=f"Order {order.order_number} shipped",
                    message="Your order has shipped and is on the way.",
                )
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error shipping order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Shipment recording failed")


@router.post("/orders/{order_id}/deliver", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def deliver_order(
    order_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Record delivery of order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = DeliverOrderCommandHandler(order_repo, uow)
        try:
            await handler.handle(
                DeliverOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    delivered_by=str(user_id),
                )
            )
            from backend.app.application.finance.finance_service import FinanceService

            await FinanceService(session).create_invoice_from_sales_order(
                tenant_id=tenant_id,
                sales_order_id=order_id,
                created_by=user_id,
                notes="Auto-generated on sales order delivery.",
            )
            try:
                from backend.app.application.delivery.delivery_service import DeliveryService

                await DeliveryService(session).mark_sales_order_delivered_documents(tenant_id, order_id)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.warning(
                    "Delivery documents were not marked delivered for order %s. "
                    "Run the delivery module migration to enable delivery documents.",
                    order_id,
                    exc_info=True,
                )
            order = await order_repo.get_by_id(order_id, tenant_id)
            if order:
                await _notify_client_order_status(
                    session,
                    container,
                    tenant_id,
                    order,
                    notification_type="ORDER_DELIVERED",
                    title=f"Order {order.order_number} delivered",
                    message="Your order has been delivered and the invoice is now available.",
                )
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error delivering order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delivery recording failed")


@router.post("/orders/{order_id}/close", dependencies=[Depends(require_permission("sales:write"))])
async def close_order(
    order_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Force-complete a sales order and release any remaining reservations."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.manufacturing.services.workflow_orchestration_service import (
            WorkflowOrchestrationService,
        )

        try:
            service = WorkflowOrchestrationService(session)
            result = await service.close_sales_order(
                tenant_id=tenant_id,
                sales_order_id=order_id,
                closed_by=user_id,
            )
            await session.commit()
            return result
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except Exception as exc:
            await session.rollback()
            logger.exception("Failed to close sales order %s: %s", order_id, exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sales order close failed") from exc


@router.post("/orders/{order_id}/cancel", response_model=SalesOrderResponse, dependencies=[Depends(require_permission("sales:write"))])
async def cancel_order(
    order_id: UUID,
    body: CancelOrderRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Cancel an order."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        client_repo = ClientRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        from backend.app.domain.sales.services.credit_validation_service import CreditValidationService
        from backend.app.domain.sales.services.inventory_reservation_service import InventoryReservationService
        from backend.app.application.sales.manufacturing_integration import SalesManufacturingIntegrationService
        from backend.app.application.sales.inventory_integration import SalesInventoryIntegrationService
        from backend.app.application.manufacturing.handlers.work_order_handler import WorkOrderHandler
        from backend.app.application.manufacturing.services.inventory_service import InventoryService as StockInventoryService
        
        credit_service = CreditValidationService(client_repo)
        stock_inventory = StockInventoryService(session)
        wo_handler = WorkOrderHandler(session).with_uow(uow)
        inv_integ = SalesInventoryIntegrationService(stock_inventory, created_by=user_id)
        mfg_integ = SalesManufacturingIntegrationService(
            wo_handler,
            uow,
            created_by=user_id,
        ).with_event_dispatcher(container.event_dispatcher)
        inv_service = InventoryReservationService(inv_integ, mfg_integ)

        handler = CancelSalesOrderCommandHandler(order_repo, credit_service, inv_service, uow)
        try:
            await handler.handle(
                CancelSalesOrderCommand(
                    tenant_id=tenant_id,
                    sales_order_id=order_id,
                    reason=body.reason,
                    cancelled_by=body.cancelled_by,
                )
            )
            order = await order_repo.get_by_id(order_id, tenant_id)
            return order.to_dict() if order else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error cancelling order {order_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cancellation failed")


@router.get("/orders/stats/by-status", response_model=OrderStatusResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_order_count_by_status(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get order counts by status."""
    container = get_container(request)
    async with container.session_factory() as session:
        order_repo = SalesOrderRepository(session)
        handler = GetOrderCountByStatusQueryHandler(order_repo)
        try:
            counts = await handler.handle(
                GetOrderCountByStatusQuery(
                    tenant_id=tenant_id,
                )
            )
            return OrderStatusResponse(**counts)
        except Exception as e:
            logger.exception(f"Error getting order counts by status: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stats retrieval failed")


# ==================== PRICE LIST ENDPOINTS ====================

@router.post("/price-lists", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales:write"))])
async def create_price_list(
    body: PriceListRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreatePriceListCommandHandler(price_list_repo, uow)
        try:
            price_list_id = await handler.handle(
                CreatePriceListCommand(
                    tenant_id=tenant_id,
                    name=body.name,
                    is_default=body.is_default,
                    valid_from=body.valid_from,
                    valid_to=body.valid_to,
                )
            )
            price_list = await price_list_repo.get_by_id(UUID(str(price_list_id)), tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error creating price list: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Creation failed")


@router.get("/price-lists/{price_list_id}", response_model=PriceListResponse, dependencies=[Depends(require_permission("sales:read"))])
async def get_price_list(
    price_list_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get price list details."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        handler = GetPriceListByIdQueryHandler(price_list_repo)
        try:
            return await handler.handle(
                GetPriceListByIdQuery(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error retrieving price list {price_list_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval failed")


@router.get("/price-lists", response_model=PriceListListResponse, dependencies=[Depends(require_permission("sales:read"))])
async def list_price_lists(
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    is_default: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List price lists."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        handler = ListPriceListsQueryHandler(price_list_repo)
        try:
            items = await handler.handle(
                ListPriceListsQuery(
                    tenant_id=tenant_id,
                    is_default=is_default,
                    is_active=True,
                    limit=limit,
                    offset=offset,
                )
            )
            total = len(items)
            return PriceListListResponse(items=items, total=total, limit=limit, offset=offset)
        except Exception as e:
            logger.exception(f"Error listing price lists: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="List retrieval failed")


@router.patch(
    "/price-lists/{price_list_id}",
    response_model=PriceListResponse,
    dependencies=[Depends(require_permission("sales:write"))],
)
async def update_price_list(
    price_list_id: UUID,
    body: PriceListUpdateRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Update price list header (name, validity, is_default, is_active)."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdatePriceListCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                UpdatePriceListCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    name=body.name,
                    valid_from=body.valid_from,
                    valid_to=body.valid_to,
                    is_default=body.is_default,
                    is_active=body.is_active,
                )
            )
            updated = await price_list_repo.get_by_id(price_list_id, tenant_id)
            return updated.to_dict() if updated else None
        except ValueError as e:
            err_msg = str(e)
            if "not found" in err_msg.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
            elif "already exists" in err_msg.lower():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
            else:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)
        except Exception as e:
            logger.exception(f"Error updating price list {price_list_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Update failed")


@router.post("/price-lists/{price_list_id}/lines", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales:write"))])
async def add_price_list_line(
    price_list_id: UUID,
    body: PriceListLineRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Add a pricing line to a price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = AddPriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                AddPriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    unit_price=body.unit_price,
                )
            )
            price_list = await price_list_repo.get_by_id(price_list_id, tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error adding price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line addition failed")


@router.patch("/price-lists/{price_list_id}/lines", response_model=PriceListResponse, dependencies=[Depends(require_permission("sales:write"))])
async def update_price_list_line(
    price_list_id: UUID,
    body: PriceListLineRequest,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update a pricing line."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdatePriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                UpdatePriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=body.product_id,
                    product_type=body.product_type,
                    new_price=body.unit_price,
                )
            )
            price_list = await price_list_repo.get_by_id(price_list_id, tenant_id)
            return price_list.to_dict() if price_list else None
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.exception(f"Error updating price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line update failed")


@router.delete("/price-lists/{price_list_id}/lines/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("sales:write"))])
async def remove_price_list_line(
    price_list_id: UUID,
    product_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Remove a pricing line from a price list."""
    container = get_container(request)
    async with container.session_factory() as session:
        price_list_repo = PriceListRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = RemovePriceListLineCommandHandler(price_list_repo, uow)
        try:
            await handler.handle(
                RemovePriceListLineCommand(
                    tenant_id=tenant_id,
                    price_list_id=price_list_id,
                    product_id=product_id,
                    product_type="PRODUCT",
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger.exception(f"Error removing price list line: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Line removal failed")
