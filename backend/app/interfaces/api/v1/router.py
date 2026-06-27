from __future__ import annotations

from fastapi import APIRouter, Depends
from backend.app.core.module_registry import module_registry
from backend.app.interfaces.api.v1.dependencies.auth import get_current_role

from backend.app.interfaces.api.v1.routes.auth import router as auth_router
from backend.app.interfaces.api.v1.routes.self_service_password_reset_router import router as password_reset_router
from backend.app.interfaces.api.v1.routes.tenants import router as tenants_router
from backend.app.interfaces.api.v1.routes.files import router as files_router
from backend.app.interfaces.api.v1.routes.inventory import router as inventory_router
from backend.app.interfaces.api.v1.routes.master_data import router as master_data_router
from backend.app.interfaces.api.v1.routes.batch_and_serial import router as batch_and_serial_router
from backend.app.interfaces.api.v1.routes.products import router as products_router
from backend.app.interfaces.api.v1.routes.boms import router as boms_router
from backend.app.interfaces.api.v1.workstations import router as workstations_router
from backend.app.interfaces.api.v1.operations import router as bom_operations_router
from backend.app.interfaces.api.v1.routes.operations import router as manufacturing_operations_router
from backend.app.interfaces.api.sales import router as sales_router
from backend.app.interfaces.api.v1.routes.work_orders import router as work_orders_router
from backend.app.interfaces.api.v1.routes.supply_chain import router as supply_chain_router
from backend.app.interfaces.api.v1.routes.inspection_templates import router as inspection_templates_router
from backend.app.interfaces.api.v1.routes.finance import router as finance_router
from backend.app.interfaces.api.v1.routes.deliveries import router as deliveries_router
from backend.app.interfaces.api.v1.routes.reports import router as reports_router
from backend.app.interfaces.api.v1.routes.notifications import router as notifications_router
from backend.app.interfaces.api.v1.routes.client_portal import router as client_portal_router
from backend.app.interfaces.api.v1.routes.mrp import router as mrp_router

from backend.app.interfaces.api.v1.routes.inventory_extended import router as inventory_extended_router
from backend.app.interfaces.api.v1.routes.rbac_admin import router as rbac_admin_router
from backend.app.interfaces.api.v1.routes.users import router as users_router
from backend.app.interfaces.api.v1.routes.dashboards import router as dashboards_router
from backend.app.interfaces.api.v1.routes.audit_logs import router as audit_logs_router
from backend.app.interfaces.api.v1.routes.documents import router as documents_router
from backend.app.interfaces.api.v1.routes.quality_control import router as quality_control_router
from backend.app.interfaces.api.v1.routes.storekeeper import router as storekeeper_router
from backend.app.interfaces.api.v1.routes.worker import router as worker_router
from backend.app.interfaces.api.v1.routes.workflow import router as workflow_router
from backend.app.interfaces.api.v1.routes.delivery_dashboard import router as delivery_dashboard_router
from backend.app.interfaces.api.v1.routes.analytics import router as analytics_router
from backend.app.interfaces.api.v1.routes.material_onboarding import router as material_onboarding_router
from backend.app.infrastructure.persistence.models import material_consumption_model as _material_consumption_model
from backend.app.infrastructure.persistence.models import pick_list_model as _pick_list_model

api_v1_router = APIRouter()

api_v1_router.include_router(rbac_admin_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(audit_logs_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(password_reset_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(inventory_extended_router)
api_v1_router.include_router(master_data_router)
api_v1_router.include_router(batch_and_serial_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(boms_router)
api_v1_router.include_router(workstations_router)
api_v1_router.include_router(bom_operations_router)
api_v1_router.include_router(manufacturing_operations_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(work_orders_router)
api_v1_router.include_router(supply_chain_router)
api_v1_router.include_router(dashboards_router)
api_v1_router.include_router(inspection_templates_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(deliveries_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(client_portal_router)
api_v1_router.include_router(mrp_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(quality_control_router)
api_v1_router.include_router(storekeeper_router)
api_v1_router.include_router(worker_router)
api_v1_router.include_router(workflow_router)
api_v1_router.include_router(delivery_dashboard_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(material_onboarding_router)


# --- Dynamic Module Registration ---
module_registry.register(
    id="auth",
    name="IAM & Users",
    route="/users",
    dependencies=[],
    roles=["ADMIN"],
    status="active",
    icon="Users"
)

module_registry.register(
    id="inventory",
    name="Inventory",
    route="/inventory",
    dependencies=[],
    roles=["ADMIN", "MANAGER", "OPERATOR", "VIEWER"],
    status="active",
    icon="Package"
)

module_registry.register(
    id="products",
    name="Product Master",
    route="/products",
    dependencies=["inventory"],
    roles=["ADMIN", "MANAGER"],
    status="active",
    icon="PackageSearch"
)

module_registry.register(
    id="bom",
    name="Bill of Materials",
    route="/bom",
    dependencies=["products", "inventory"],
    roles=["ADMIN", "MANAGER", "OPERATOR"],
    status="active",
    icon="Layers"
)

module_registry.register(
    id="manufacturing",
    name="Manufacturing Ops",
    route="/manufacturing",
    dependencies=["bom"],
    roles=["ADMIN", "MANAGER"],
    status="active",
    icon="Factory"
)

module_registry.register(
    id="sales",
    name="Sales & Orders",
    route="/sales",
    dependencies=["inventory", "products"],
    roles=["ADMIN", "MANAGER", "OPERATOR", "VIEWER"],
    status="active",
    icon="ShoppingCart"
)

module_registry.register(
    id="work-orders",
    name="Work Orders",
    route="/work-orders",
    dependencies=["bom", "inventory"],
    roles=["ADMIN", "MANAGER", "OPERATOR"],
    status="active",
    icon="ClipboardList"
)

module_registry.register(
    id="shop-floor",
    name="Shop Floor",
    route="/shop-floor",
    dependencies=["work-orders"],
    roles=["ADMIN", "MANAGER", "OPERATOR"],
    status="active",
    icon="Factory"
)

module_registry.register(
    id="procurement",
    name="Procurement & Quality",
    route="/procurement",
    dependencies=["inventory"],
    roles=["ADMIN", "MANAGER", "OPERATOR"],
    status="active",
    icon="Truck"
)

module_registry.register(
    id="finance",
    name="Finance & Accounting",
    route="/finance",
    dependencies=["sales", "procurement"],
    roles=["ADMIN", "ACCOUNTANT", "MANAGER"],
    status="active",
    icon="DollarSign"
)

module_registry.register(
    id="deliveries",
    name="Deliveries",
    route="/sales/deliveries",
    dependencies=["sales", "inventory"],
    roles=["ADMIN", "MANAGER", "SALES", "STOREKEEPER"],
    status="active",
    icon="Truck"
)

module_registry.register(
    id="reports",
    name="Reports & Analytics",
    route="/reports",
    dependencies=[],
    roles=["ADMIN", "MANAGER", "ACCOUNTANT", "SALES", "QC", "OPERATOR"],
    status="active",
    icon="BarChart2"
)

module_registry.register(
    id="audit-logs",
    name="Activity Log",
    route="/activity-log",
    dependencies=[],
    roles=["ADMIN", "TENANT_ADMIN"],
    status="active",
    icon="History"
)

module_registry.register(
    id="mrp",
    name="Capacity & MRP",
    route="/mrp",
    dependencies=["work-orders", "inventory"],
    roles=["ADMIN", "TENANT_ADMIN", "MANAGER", "PLANNER", "STOREKEEPER", "OPERATOR"],
    status="active",
    icon="BarChart3"
)

# --- System API Map ---
@api_v1_router.get("/system-map", tags=["System"])
async def get_system_map(current_role: str = Depends(get_current_role)):
    """Returns the dynamic system floor plan tailored to the user's role."""
    return module_registry.get_system_map(user_role=current_role)
