from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.application.setup.setup_status_service import CompanySetupStatusService
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container

router = APIRouter(prefix="/company/setup-status", tags=["Company Setup"])


@router.get("", summary="Get company setup readiness status")
async def get_company_setup_status(
    request: Request,
    tenant_id = Depends(get_current_tenant_id),
):
    container = get_container(request)

    async with container.session_factory() as session:
        from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
        from backend.app.infrastructure.persistence.models.user_model import UserModel
        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
        from backend.app.infrastructure.persistence.models.sales_models import ClientModel
        from backend.app.infrastructure.persistence.models.material_model import MaterialModel
        from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
        from backend.app.infrastructure.persistence.models.bom_model import BOMModel
        from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
        from sqlalchemy import select

        tenant_result = await session.execute(select(TenantModel).where(TenantModel.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()

        company = bool(tenant and tenant.name and tenant.gst_number)

        supplier_result = await session.execute(
            select(SupplierModel.id).where(
                SupplierModel.tenant_id == tenant_id,
                SupplierModel.is_deleted.is_(False),
                SupplierModel.is_active.is_(True),
            )
        )
        supplier_count = len(supplier_result.scalars().all())

        customer_result = await session.execute(
            select(ClientModel.id).where(
                ClientModel.tenant_id == tenant_id,
                ClientModel.is_deleted.is_(False),
                ClientModel.is_active.is_(True),
            )
        )
        customer_count = len(customer_result.scalars().all())

        material_result = await session.execute(
            select(MaterialModel.id).where(
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
                MaterialModel.is_active.is_(True),
                MaterialModel.category_id.is_not(None),
                MaterialModel.base_unit_id.is_not(None),
                MaterialModel.item_code.is_not(None),
            )
        )
        material_count = len(material_result.scalars().all())

        product_result = await session.execute(
            select(ItemTemplateModel.id).where(
                ItemTemplateModel.tenant_id == tenant_id,
                ItemTemplateModel.is_deleted.is_(False),
                ItemTemplateModel.is_active.is_(True),
            )
        )
        product_count = len(product_result.scalars().all())

        bom_result = await session.execute(
            select(BOMModel.id).where(
                BOMModel.tenant_id == tenant_id,
                BOMModel.is_deleted.is_(False),
                BOMModel.is_active.is_(True),
            )
        )
        bom_count = len(bom_result.scalars().all())

        opening_stock_result = await session.execute(
            select(InventoryTransactionModel.id).where(
                InventoryTransactionModel.tenant_id == tenant_id,
                InventoryTransactionModel.is_deleted.is_(False),
            )
        )
        opening_stock_count = len(opening_stock_result.scalars().all())

        from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
        unit_result = await session.execute(
            select(UnitOfMeasureModel.id).where(
                UnitOfMeasureModel.tenant_id == tenant_id,
                UnitOfMeasureModel.is_deleted.is_(False),
                UnitOfMeasureModel.is_active.is_(True),
            )
        )
        unit_count = len(unit_result.scalars().all())

        from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
        category_result = await session.execute(
            select(MaterialCategoryModel.id).where(
                MaterialCategoryModel.tenant_id == tenant_id,
                MaterialCategoryModel.is_deleted.is_(False),
                MaterialCategoryModel.is_active.is_(True),
            )
        )
        category_count = len(category_result.scalars().all())

        from backend.app.infrastructure.persistence.models.location_model import LocationModel
        location_result = await session.execute(
            select(LocationModel.id).where(
                LocationModel.tenant_id == tenant_id,
                LocationModel.is_deleted.is_(False),
                LocationModel.is_active.is_(True),
            )
        )
        location_count = len(location_result.scalars().all())

        from backend.app.infrastructure.persistence.models.operation_model import OperationModel
        operation_result = await session.execute(
            select(OperationModel.id).where(
                OperationModel.tenant_id == tenant_id,
                OperationModel.is_deleted.is_(False),
                OperationModel.is_active.is_(True),
            )
        )
        operation_count = len(operation_result.scalars().all())

        from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel
        workstation_result = await session.execute(
            select(WorkstationModel.id).where(
                WorkstationModel.tenant_id == tenant_id,
                WorkstationModel.is_deleted.is_(False),
                WorkstationModel.is_active.is_(True),
            )
        )
        workstation_count = len(workstation_result.scalars().all())

        non_admin_user_result = await session.execute(
            select(UserModel.id).where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
                UserModel.is_active.is_(True),
                UserModel.role.notin_(["ADMIN", "TENANT_ADMIN"]),
            )
        )
        non_admin_user_count = len(non_admin_user_result.scalars().all())

    step_status = {
        "company": company,
        "numberSeries": True,
        "supplier": supplier_count > 0,
        "customer": customer_count > 0,
        "material": material_count > 0,
        "product": product_count > 0,
        "bom": bom_count > 0,
        "openingStock": opening_stock_count > 0,
        "units": unit_count > 0,
        "categories": category_count > 0,
        "locations": location_count > 0,
        "operations": operation_count > 0,
        "workstations": workstation_count > 0,
        "users": non_admin_user_count > 0,
    }

    return CompanySetupStatusService.build_status_response(step_status)
