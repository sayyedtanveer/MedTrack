from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.client_portal.service import ClientPortalService
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
    get_current_user_payload,
)
from backend.app.interfaces.api.v1.dependencies.client_portal import require_client_id, require_client_role
from backend.app.interfaces.api.v1.schemas.client_portal import (
    ClientAddressCreateRequest,
    ClientAddressUpdateRequest,
    ClientForgotPasswordRequest,
    ClientLoginRequest,
    ClientLoginResponse,
    ClientOrderCreateRequest,
    ClientProfileUpdateRequest,
    ClientRefreshResponse,
    ClientReorderRequest,
    ClientResetPasswordRequest,
    ClientSupportRequest,
    ClientNotificationSettingsUpdateRequest,
)

router = APIRouter(prefix="/client", tags=["Client Portal"])


def _get_container(request: Request):
    return request.app.state.container


async def _get_db_session(request: Request):
    factory = request.app.state.container.session_factory
    async with factory() as session:
        yield session


def _service(request: Request, session: AsyncSession) -> ClientPortalService:
    container = _get_container(request)
    return ClientPortalService(
        session=session,
        password_hasher=container.password_hasher,
        jwt_handler=container.jwt_handler,
        email_service=container.email_service,
        connection_manager=getattr(container, "connection_manager", None),
        environment=getattr(container, "environment", "development"),
    )


@router.post("/auth/login", response_model=ClientLoginResponse)
async def client_login(
    body: ClientLoginRequest,
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).login_client(body.email, body.password, body.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/auth/logout")
async def client_logout(
    payload: dict = Depends(require_client_role),
):
    return {"status": "logged_out"}


@router.post("/auth/refresh", response_model=ClientRefreshResponse)
async def client_refresh(
    request: Request,
    payload: dict = Depends(require_client_role),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).refresh_client_session(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/auth/forgot-password")
async def client_forgot_password(
    body: ClientForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).request_password_reset(body.email, body.tenant_id)


@router.post("/auth/reset-password")
async def client_reset_password(
    body: ClientResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).reset_password(body.token, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/dashboard")
async def client_dashboard(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_dashboard(tenant_id, client_id, user_id)


@router.get("/catalog")
async def client_catalog(
    request: Request,
    search: str | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).list_catalog(tenant_id, client_id, search)


@router.get("/orders")
async def client_orders(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).list_orders(tenant_id, client_id, page, page_size, status_filter, search)


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def client_order_create(
    body: ClientOrderCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        lines = [line.model_dump() for line in body.lines]
        return await _service(request, session).create_order(
            tenant_id=tenant_id,
            client_id=client_id,
            user_id=user_id,
            lines_input=lines,
            delivery_date=body.delivery_date,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/orders/{order_id}")
async def client_order_detail(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).get_order(tenant_id, client_id, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/orders/{order_id}/tracking")
async def client_order_tracking(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).get_order_tracking(tenant_id, client_id, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/orders/reorder", status_code=status.HTTP_201_CREATED)
async def client_reorder(
    body: ClientReorderRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        lines = [line.model_dump() for line in body.lines] if body.lines else None
        return await _service(request, session).create_reorder(tenant_id, client_id, body.order_id, lines, body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/orders/{order_id}/cancel-request")
async def client_cancel_request(
    order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).request_order_cancellation(tenant_id, client_id, user_id, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/invoices")
async def client_invoices(
    request: Request,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).list_invoices(tenant_id, client_id, page, page_size, status_filter)


@router.get("/invoices/{invoice_id}")
async def client_invoice_detail(
    invoice_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).get_invoice(tenant_id, client_id, invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/invoices/{invoice_id}/pdf")
async def client_invoice_pdf(
    invoice_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        invoice_number, pdf_bytes = await _service(request, session).build_invoice_pdf(tenant_id, client_id, invoice_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{invoice_number}.pdf"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/credit")
async def client_credit(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_credit(tenant_id, client_id)


@router.get("/profile")
async def client_profile(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_profile(tenant_id, client_id, user_id)


@router.put("/profile")
async def client_profile_update(
    body: ClientProfileUpdateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).update_profile(tenant_id, client_id, user_id, body.model_dump(exclude_none=True))


@router.get("/addresses")
async def client_addresses(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).list_addresses(tenant_id, client_id)


@router.post("/addresses", status_code=status.HTTP_201_CREATED)
async def client_address_create(
    body: ClientAddressCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).create_address(tenant_id, client_id, body.model_dump())


@router.put("/addresses/{address_id}")
async def client_address_update(
    address_id: uuid.UUID,
    body: ClientAddressUpdateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).update_address(
            tenant_id,
            client_id,
            address_id,
            body.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/addresses/{address_id}")
async def client_address_delete(
    address_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).delete_address(tenant_id, client_id, address_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/notifications")
async def client_notifications(
    request: Request,
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_notifications(tenant_id, client_id, user_id, unread_only, page, page_size)


@router.put("/notifications/{notification_id}/read")
async def client_notification_read(
    notification_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        return await _service(request, session).mark_notification_read(tenant_id, user_id, notification_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/notifications/settings")
async def client_notification_settings(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_notification_settings(tenant_id, client_id, user_id)


@router.put("/notifications/settings")
async def client_notification_settings_update(
    body: ClientNotificationSettingsUpdateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).update_notification_settings(
        tenant_id,
        client_id,
        user_id,
        body.model_dump(exclude_none=True),
    )


@router.get("/support/faq")
async def client_support_faq(
    request: Request,
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).get_support_faq()


@router.post("/support/contact", status_code=status.HTTP_201_CREATED)
async def client_support_contact(
    body: ClientSupportRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    client_id: uuid.UUID = Depends(require_client_id),
    session: AsyncSession = Depends(_get_db_session),
):
    return await _service(request, session).submit_support_request(tenant_id, client_id, user_id, body.subject, body.message)
