from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Set


class Permission(str, Enum):
    """Fine-grained permissions using the existing ERP permission registry."""

    ALL = "*"

    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_INVITE = "user:invite"
    RBAC_READ = "rbac:read"
    RBAC_WRITE = "rbac:write"
    ADMIN_READ = "admin:read"
    AUDIT_READ = "audit:read"

    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    INVENTORY_DELETE = "inventory:delete"

    SALES_READ = "sales:read"
    SALES_WRITE = "sales:write"
    SALES_DELETE = "sales:delete"
    SALES_VIEW_ORDERS = "sales:view_orders"
    SALES_CREATE_ORDER = "sales:create_order"
    SALES_APPROVE_ORDER = "sales:approve_order"

    MANUFACTURING_READ = "manufacturing:read"
    MANUFACTURING_WRITE = "manufacturing:write"

    PROCUREMENT_READ = "procurement:read"
    PROCUREMENT_WRITE = "procurement:write"

    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"
    INVOICE_CREATE = "invoice.create"
    INVOICE_VIEW = "invoice.view"
    INVOICE_APPROVE = "invoice.approve"
    PAYMENT_RECORD = "payment.record"
    SUPPLIER_INVOICE_CREATE = "supplier_invoice.create"
    SUPPLIER_INVOICE_VIEW = "supplier_invoice.view"
    SUPPLIER_PAYMENT_RECORD = "supplier_payment.record"
    LEDGER_VIEW = "ledger.view"
    FINANCE_SETTINGS_VIEW = "finance_settings.view"
    FINANCE_SETTINGS_WRITE = "finance_settings.write"
    REPORT_VIEW_FINANCIAL = "report.view_financial"

    QUALITY_READ = "quality:read"
    QUALITY_WRITE = "quality:write"

    REPORTS_READ = "reports:read"

    CLIENT_READ = "client:read"
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"
    STOREKEEPER_READ = "storekeeper:read"
    WORKER_READ = "worker:read"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"


_mfg_inv_quality = frozenset({
    Permission.INVENTORY_READ,
    Permission.INVENTORY_WRITE,
    Permission.MANUFACTURING_READ,
    Permission.MANUFACTURING_WRITE,
    Permission.QUALITY_READ,
    Permission.QUALITY_WRITE,
})


ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": frozenset({Permission.ALL}),
    "tenant_admin": frozenset({Permission.ALL}),
    "manager": frozenset({
        Permission.ADMIN_READ,
        Permission.RBAC_READ,
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_WRITE,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.SALES_APPROVE_ORDER,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.FINANCE_READ,
        Permission.INVOICE_CREATE,
        Permission.INVOICE_VIEW,
        Permission.INVOICE_APPROVE,
        Permission.PAYMENT_RECORD,
        Permission.SUPPLIER_INVOICE_VIEW,
        Permission.SUPPLIER_PAYMENT_RECORD,
        Permission.LEDGER_VIEW,
        Permission.FINANCE_SETTINGS_VIEW,
        Permission.REPORT_VIEW_FINANCIAL,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
        Permission.REPORTS_READ,
        Permission.STOREKEEPER_READ,
        Permission.WORKER_READ,
    }),
    "operator": frozenset(
        _mfg_inv_quality
        | {
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_WRITE,
            Permission.STOREKEEPER_READ,
        }
    ),
    "storekeeper": frozenset(
        _mfg_inv_quality
        | {
            Permission.PROCUREMENT_READ,
            Permission.PROCUREMENT_WRITE,
            Permission.STOREKEEPER_READ,
        }
    ),
    "planner": frozenset({
        Permission.INVENTORY_READ,
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.QUALITY_READ,
        Permission.REPORTS_READ,
        Permission.STOREKEEPER_READ,
    }),
    "qc": frozenset({
        Permission.INVENTORY_READ,
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
        Permission.PROCUREMENT_READ,
    }),
    "sales": frozenset({
        Permission.INVENTORY_READ,
        Permission.SALES_READ,
        Permission.SALES_WRITE,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.INVOICE_CREATE,
        Permission.INVOICE_VIEW,
        Permission.MANUFACTURING_READ,
        Permission.REPORTS_READ,
    }),
    "accountant": frozenset({
        Permission.FINANCE_READ,
        Permission.FINANCE_WRITE,
        Permission.INVOICE_CREATE,
        Permission.INVOICE_VIEW,
        Permission.INVOICE_APPROVE,
        Permission.PAYMENT_RECORD,
        Permission.SUPPLIER_INVOICE_CREATE,
        Permission.SUPPLIER_INVOICE_VIEW,
        Permission.SUPPLIER_PAYMENT_RECORD,
        Permission.LEDGER_VIEW,
        Permission.FINANCE_SETTINGS_VIEW,
        Permission.FINANCE_SETTINGS_WRITE,
        Permission.REPORT_VIEW_FINANCIAL,
        Permission.REPORTS_READ,
    }),
    "worker": frozenset({
        Permission.MANUFACTURING_READ,
        Permission.MANUFACTURING_WRITE,
        Permission.INVENTORY_READ,
        Permission.WORKER_READ,
    }),
    "client": frozenset({
        Permission.SALES_READ,
        Permission.SALES_VIEW_ORDERS,
        Permission.SALES_CREATE_ORDER,
        Permission.INVENTORY_READ,
        Permission.CLIENT_READ,
        Permission.INVOICE_VIEW,
    }),
    "supplier": frozenset({
        Permission.PROCUREMENT_READ,
        Permission.PROCUREMENT_WRITE,
        Permission.SUPPLIER_READ,
        Permission.SUPPLIER_WRITE,
        Permission.SUPPLIER_INVOICE_CREATE,
        Permission.SUPPLIER_INVOICE_VIEW,
    }),
    "viewer": frozenset({
        Permission.INVENTORY_READ,
        Permission.SALES_READ,
        Permission.MANUFACTURING_READ,
        Permission.PROCUREMENT_READ,
        Permission.FINANCE_READ,
        Permission.QUALITY_READ,
        Permission.REPORTS_READ,
    }),
}


PERMISSION_FALLBACKS: Dict[str, FrozenSet[str]] = {
    Permission.INVOICE_CREATE.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.INVOICE_VIEW.value: frozenset({Permission.FINANCE_READ.value}),
    Permission.INVOICE_APPROVE.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.PAYMENT_RECORD.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.SUPPLIER_INVOICE_CREATE.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.SUPPLIER_INVOICE_VIEW.value: frozenset({Permission.FINANCE_READ.value}),
    Permission.SUPPLIER_PAYMENT_RECORD.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.LEDGER_VIEW.value: frozenset({Permission.FINANCE_READ.value}),
    Permission.FINANCE_SETTINGS_VIEW.value: frozenset({Permission.FINANCE_READ.value}),
    Permission.FINANCE_SETTINGS_WRITE.value: frozenset({Permission.FINANCE_WRITE.value}),
    Permission.REPORT_VIEW_FINANCIAL.value: frozenset({
        Permission.REPORTS_READ.value,
        Permission.FINANCE_READ.value,
    }),
}


def permission_aliases(permission: str) -> Set[str]:
    """Return the requested permission plus any backward-compatible fallbacks."""
    requested = str(permission or "").strip()
    aliases = {requested}
    aliases.update(PERMISSION_FALLBACKS.get(requested, frozenset()))
    return aliases


def permission_grants(granted_permission: str, requested_permission: str) -> bool:
    granted = str(granted_permission or "").strip()
    if granted == Permission.ALL.value:
        return True
    return granted in permission_aliases(requested_permission)


def has_permission(role: str, permission: str) -> bool:
    """Return True if the given role grants the requested permission."""
    perms = {
        granted.value if isinstance(granted, Permission) else str(granted)
        for granted in ROLE_PERMISSIONS.get(role.lower(), frozenset())
    }
    return any(permission_grants(granted, permission) for granted in perms)
