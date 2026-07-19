from __future__ import annotations

import re
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/uploads"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Maps URL pattern → (entity_type, group_index_for_entity_id)
# Each tuple: (regex, entity_type, id_group_index or None)
_ENTITY_PATTERNS = [
    (re.compile(r"^/api/v\d+/suppliers/([0-9a-f-]{36})"), "supplier", 1),
    (re.compile(r"^/api/v\d+/suppliers"), "supplier", None),
    (re.compile(r"^/api/v\d+/purchase-orders/([0-9a-f-]{36})"), "purchase_order", 1),
    (re.compile(r"^/api/v\d+/purchase-orders"), "purchase_order", None),
    (re.compile(r"^/api/v\d+/supplier/purchase-orders/([0-9a-f-]{36})"), "purchase_order", 1),
    (re.compile(r"^/api/v\d+/grns/([0-9a-f-]{36})"), "goods_receipt_note", 1),
    (re.compile(r"^/api/v\d+/grns"), "goods_receipt_note", None),
    (re.compile(r"^/api/v\d+/material-requests/([0-9a-f-]{36})"), "material_request", 1),
    (re.compile(r"^/api/v\d+/material-requests"), "material_request", None),
    (re.compile(r"^/api/v\d+/rfq/([0-9a-f-]{36})"), "rfq", 1),
    (re.compile(r"^/api/v\d+/rfq"), "rfq", None),
    (re.compile(r"^/api/v\d+/supplier/rfq/([0-9a-f-]{36})"), "rfq", 1),
    (re.compile(r"^/api/v\d+/supplier/quotations/([0-9a-f-]{36})"), "supplier_quotation", 1),
    (re.compile(r"^/api/v\d+/supplier/quotations"), "supplier_quotation", None),
    (re.compile(r"^/api/v\d+/quotations/([0-9a-f-]{36})"), "supplier_quotation", 1),
    (re.compile(r"^/api/v\d+/work-orders/([0-9a-f-]{36})"), "work_order", 1),
    (re.compile(r"^/api/v\d+/work-orders"), "work_order", None),
    (re.compile(r"^/api/v\d+/sales/orders/([0-9a-f-]{36})"), "sales_order", 1),
    (re.compile(r"^/api/v\d+/sales/orders"), "sales_order", None),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/activate"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/copy"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/validate"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/operations"), "bom_operation", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})"), "bom", 1),
    (re.compile(r"^/api/v\d+/products/([0-9a-f-]{36})/boms"), "bom", None),
    (re.compile(r"^/api/v\d+/products/templates/([0-9a-f-]{36})/variants"), "item_variant", None),
    (re.compile(r"^/api/v\d+/products/templates/([0-9a-f-]{36})"), "item_template", 1),
    (re.compile(r"^/api/v\d+/products/variants/([0-9a-f-]{36})"), "item_variant", 1),
    (re.compile(r"^/api/v\d+/operations/([0-9a-f-]{36})"), "operation", 1),
    (re.compile(r"^/api/v\d+/operations"), "operation", None),
    (re.compile(r"^/api/v\d+/workstations/([0-9a-f-]{36})"), "workstation", 1),
    (re.compile(r"^/api/v\d+/workstations"), "workstation", None),
]

_ACTION_MAP = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "PATCH",
    "DELETE": "DELETE",
}

_ACTION_PATTERNS = [
    (re.compile(r"/purchase-orders/[0-9a-f-]{36}/send$"), "PO_SENT"),
    (re.compile(r"/purchase-orders/[0-9a-f-]{36}/acknowledge$"), "PO_ACKNOWLEDGED"),
    (re.compile(r"/supplier/purchase-orders/[0-9a-f-]{36}/acknowledge$"), "PO_ACKNOWLEDGED"),
    (re.compile(r"/purchase-orders/[0-9a-f-]{36}/receive$"), "PO_RECEIVED"),
    (re.compile(r"/grns/[0-9a-f-]{36}/receive-in-inventory$"), "GRN_RECEIVED"),
    (re.compile(r"/material-requests/run-mrp$"), "MRP_RUN"),
    (re.compile(r"/rfq/[0-9a-f-]{36}/send$"), "RFQ_SENT"),
    (re.compile(r"/rfq/[0-9a-f-]{36}/award$"), "RFQ_AWARDED"),
    (re.compile(r"/supplier/rfq/[0-9a-f-]{36}/quote$"), "QUOTE_SUBMITTED"),
]


def _resolve_entity(path: str) -> tuple[str | None, str | None]:
    """Returns (entity_type, entity_id) by matching path against known patterns."""
    for pattern, entity_type, id_group in _ENTITY_PATTERNS:
        m = pattern.search(path)
        if m:
            entity_id = m.group(id_group) if id_group and id_group <= len(m.groups()) else None
            return entity_type, entity_id
    return "api_request", None


def _resolve_action(method: str, path: str) -> str:
    for pattern, action in _ACTION_PATTERNS:
        if pattern.search(path):
            return action
    return _ACTION_MAP.get(method, method)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Post-response middleware — writes a structured audit record for every
    state-changing API call (POST/PUT/PATCH/DELETE).

    entity_type and entity_id are resolved from the URL path pattern.
    tenant_id, user_id, correlation_id are read from request.state (set by other middlewares).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path

        if (
            request.method in _WRITE_METHODS
            and not any(path.startswith(p) for p in _SKIP_PATHS)
        ):
            try:
                entity_type, entity_id = _resolve_entity(path)
                action = _resolve_action(request.method, path)

                # Attempt to get tenant_id/user_id from request state (set by TenantMiddleware/auth)
                tenant_id = getattr(request.state, "tenant_id", None)
                user_id = getattr(request.state, "user_id", None)
                correlation_id = getattr(request.state, "correlation_id", None)

                audit_service = request.app.state.container.audit_service
                await audit_service.log_action(
                    action=action,
                    entity_type=entity_type,
                    entity_id=uuid.UUID(entity_id) if entity_id else None,
                    extra={
                        "source": "http_write",
                        "path": path,
                        "method": request.method,
                        "status_code": response.status_code,
                    },
                )
            except Exception as exc:
                logger.error(
                    "AuditMiddleware failed to log",
                    extra={"error": str(exc)},
                )

        return response
