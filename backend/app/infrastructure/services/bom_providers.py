import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.services.bom_browser_service import BOMProvider, ComponentDetailProvider
from backend.app.domain.bom.services.cost_rollup_service import CostProvider
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.domain.bom.services.cost_rollup_service import TenantProvider


class InfrastructureBOMProvider(BOMProvider):
    def __init__(self, bom_repo):
        self._bom_repo = bom_repo

    async def get_active_bom(self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None) -> Optional[BillOfMaterial]:
        return await self._bom_repo.get_active_bom(tenant_id, template_id, variant_id)

class InfrastructureTenantProvider(TenantProvider):
    def __init__(self, session):
        self._session = session
        
    async def get_tenant_currency(self, tenant_id: uuid.UUID) -> tuple[Optional[str], Optional[str]]:
        stmt = select(TenantModel.currency_code, TenantModel.currency_symbol).where(TenantModel.id == tenant_id)
        res = (await self._session.execute(stmt)).first()
        if res:
            return res.currency_code, res.currency_symbol
        return None, None

class InfrastructureCostProvider(CostProvider):
    def __init__(self, session):
        self._session = session

    async def get_material_cost(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        stmt = select(MaterialModel.current_cost).where(
            MaterialModel.id == material_id,
            MaterialModel.tenant_id == tenant_id
        )
        cost = (await self._session.execute(stmt)).scalar_one_or_none()
        return Decimal(str(cost)) if cost else Decimal('0.0')

    async def get_operation_cost(self, tenant_id: uuid.UUID, operation_id: uuid.UUID) -> Decimal:
        stmt = select(OperationModel).options(selectinload(OperationModel.workstation)).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id
        )
        op_model = (await self._session.execute(stmt)).scalar_one_or_none()
        if not op_model:
            return Decimal('0.0')
        
        # Cost = (setup + run_time) * rate
        # times are in minutes, rate is per hour. Convert times to hours.
        total_minutes = Decimal(str(op_model.setup_time)) + Decimal(str(op_model.run_time))
        hours = total_minutes / Decimal('60.0')
        rate = Decimal(str(op_model.workstation.hourly_rate))
        return hours * rate

class InfrastructureComponentDetailProvider(ComponentDetailProvider):
    def __init__(self, session):
        self._session = session
        
    async def get_component_details(self, tenant_id: uuid.UUID, is_material: bool, component_id: uuid.UUID) -> Dict[str, Any]:
        if is_material:
            stmt = select(MaterialModel.name, MaterialModel.code, UnitOfMeasureModel.name.label("unit_name")).outerjoin(
                UnitOfMeasureModel, MaterialModel.base_unit_id == UnitOfMeasureModel.id
            ).where(
                MaterialModel.id == component_id,
                MaterialModel.tenant_id == tenant_id
            )
        else:
            # Try Variant first, then Template.
            stmt = select(ItemVariantModel.name, ItemVariantModel.code, UnitOfMeasureModel.name.label("unit_name")).outerjoin(
                UnitOfMeasureModel, ItemVariantModel.base_unit_id == UnitOfMeasureModel.id
            ).where(
                ItemVariantModel.id == component_id,
                ItemVariantModel.tenant_id == tenant_id
            )
            res = (await self._session.execute(stmt)).first()
            if not res:
                stmt = select(ItemTemplateModel.name, ItemTemplateModel.code, UnitOfMeasureModel.name.label("unit_name")).outerjoin(
                    UnitOfMeasureModel, ItemTemplateModel.base_unit_id == UnitOfMeasureModel.id
                ).where(
                    ItemTemplateModel.id == component_id,
                    ItemTemplateModel.tenant_id == tenant_id
                )
                res = (await self._session.execute(stmt)).first()
            if res:
                return {"name": res.name, "code": res.code, "unit_name": res.unit_name or "pcs"}
            return {"name": "Unknown", "code": "???", "unit_name": "pcs"}

        res = (await self._session.execute(stmt)).first()
        if res:
            return {"name": res.name, "code": res.code, "unit_name": res.unit_name or "pcs"}
        return {"name": "Unknown", "code": "???", "unit_name": "pcs"}
