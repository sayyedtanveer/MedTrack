import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.services.bom_browser_service import BOMProvider, ComponentDetailProvider
from backend.app.domain.bom.services.cost_rollup_service import CostProvider
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.services.component_resolution import ComponentResolution, BOMResolutionError
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.workstation_model import WorkstationModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.procurement_pricing_models import (
    StandardCostRevisionModel,
)
from backend.app.domain.bom.services.cost_rollup_service import TenantProvider


class InfrastructureBOMProvider(BOMProvider):
    def __init__(self, bom_repo):
        self._bom_repo = bom_repo

    async def get_active_bom(self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None) -> Optional[BillOfMaterial]:
        return await self._bom_repo.get_active_bom(tenant_id, template_id, variant_id)
    
    async def get_bom_for_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Optional[BillOfMaterial]:
        """Get active BOM for a semi-finished material via variant-material relationship"""
        return await self._bom_repo.get_bom_for_material(tenant_id, material_id)

    async def resolve_component(self, tenant_id: uuid.UUID, line: BOMLine) -> ComponentResolution:
        info: Dict[str, Any] = {}
        verified_child: Optional[BillOfMaterial] = None
        try:
            if line.tenant_id != tenant_id:
                raise BOMResolutionError("TENANT_MISMATCH", "Component line belongs to a different tenant")
            info = await self._bom_repo.get_component_info(
                tenant_id, material_id=line.material_id, variant_id=line.variant_id, template_id=line.template_id,
            )
            if line.material_id:
                child = (await self.get_bom_for_material(tenant_id, line.material_id)
                         if info.get("material_type") == "semi_finished" else None)
            else:
                try:
                    child = await self.get_active_bom(tenant_id, line.template_id, line.variant_id)
                except ValueError as exc:
                    raise BOMResolutionError("BOM_AMBIGUOUS", str(exc)) from exc
                if child is None:
                    raise BOMResolutionError("BOM_MISSING", "No active, nondeleted child BOM exists for this component")
            if child is not None:
                if child.tenant_id != tenant_id or child.is_deleted or not child.is_active:
                    raise BOMResolutionError("BOM_INVALID", "Linked child BOM is inactive, deleted or outside this tenant")
                output = await self._bom_repo.get_component_info(
                    tenant_id, variant_id=child.variant_id, template_id=child.template_id,
                )
                verified_child = child
                # BOM costs are per ONE target output base unit. No yield/batch
                # quantity exists in this model; never invent a unit conversion.
                if not line.unit_id or not output.get("base_unit_id") or not info.get("base_unit_id"):
                    raise BOMResolutionError("OUTPUT_UOM_MISSING", "Child output and component quantity require configured UOMs")
                if line.unit_id != output["base_unit_id"] or info["base_unit_id"] != output["base_unit_id"]:
                    raise BOMResolutionError("UOM_INCOMPATIBLE", "Child output UOM differs from the component UOM; no conversion is applied")
            if line.unit_id and info.get("base_unit_id") and line.unit_id != info["base_unit_id"]:
                raise BOMResolutionError("UOM_INCOMPATIBLE", "Component quantity UOM differs from its configured base UOM; no conversion is applied")
            return ComponentResolution(child_bom=child, details=info)
        except BOMResolutionError as exc:
            # A valid child remains browseable when its costing UOM cannot be resolved.
            return ComponentResolution(child_bom=verified_child, details=info, reason=exc.reason, message=str(exc))

class InfrastructureTenantProvider(TenantProvider):
    def __init__(self, session):
        self._session = session
        
    async def get_tenant_currency(self, tenant_id: uuid.UUID) -> tuple[Optional[str], Optional[str]]:
        stmt = select(TenantModel.currency_code, TenantModel.currency_symbol).where(
            TenantModel.id == tenant_id, TenantModel.is_deleted.is_(False),
        )
        res = (await self._session.execute(stmt)).first()
        if res:
            return res.currency_code, res.currency_symbol
        return None, None

class InfrastructureCostProvider(CostProvider):
    def __init__(self, session):
        self._session = session

    async def get_material_cost(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Optional[Decimal]:
        approved_revision_stmt = select(StandardCostRevisionModel.id).where(
            StandardCostRevisionModel.tenant_id == tenant_id,
            StandardCostRevisionModel.material_id == material_id,
            StandardCostRevisionModel.status == "APPROVED",
            StandardCostRevisionModel.is_deleted.is_(False),
        ).limit(1)
        approved_revision_id = (
            await self._session.execute(approved_revision_stmt)
        ).scalar_one_or_none()
        if approved_revision_id is None:
            return None

        stmt = select(MaterialModel.current_cost).where(
            MaterialModel.id == material_id,
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        cost = (await self._session.execute(stmt)).scalar_one_or_none()
        return Decimal(str(cost)) if cost is not None else None

    async def get_operation_cost(self, tenant_id: uuid.UUID, operation_id: uuid.UUID) -> Optional[Decimal]:
        stmt = select(
            OperationModel.setup_time, OperationModel.run_time, WorkstationModel.hourly_rate,
        ).join(WorkstationModel, OperationModel.workstation_id == WorkstationModel.id).where(
            OperationModel.id == operation_id,
            OperationModel.tenant_id == tenant_id,
            OperationModel.is_deleted.is_(False),
            OperationModel.is_active.is_(True),
            WorkstationModel.tenant_id == tenant_id,
            WorkstationModel.is_deleted.is_(False),
            WorkstationModel.is_active.is_(True),
        )
        operation = (await self._session.execute(stmt)).first()
        if operation is None:
            return None
        
        # Cost = (setup + run_time) * rate
        # times are in minutes, rate is per hour. Convert times to hours.
        total_minutes = Decimal(str(operation.setup_time)) + Decimal(str(operation.run_time))
        hours = total_minutes / Decimal('60.0')
        rate = Decimal(str(operation.hourly_rate))
        return hours * rate

class InfrastructureComponentDetailProvider(ComponentDetailProvider):
    def __init__(self, session):
        self._session = session
        
    async def get_component_details(self, tenant_id: uuid.UUID, is_material: bool, component_id: uuid.UUID) -> Dict[str, Any]:
        if is_material:
            stmt = select(
                MaterialModel.name, 
                MaterialModel.code, 
                MaterialModel.material_type,
                MaterialModel.current_cost,
                UnitOfMeasureModel.name.label("unit_name")
            ).outerjoin(
                UnitOfMeasureModel, MaterialModel.base_unit_id == UnitOfMeasureModel.id
            ).where(
                MaterialModel.id == component_id,
                MaterialModel.tenant_id == tenant_id
            )
            res = (await self._session.execute(stmt)).first()
            if res:
                # Check for an APPROVED StandardCostRevision — the BOM cost provider
                # gate requires one before recognising current_cost.  If none exists,
                # return 0 so the tree display matches the cost rollup (which would
                # treat this material as "missing cost").
                approved_stmt = select(StandardCostRevisionModel.id).where(
                    StandardCostRevisionModel.tenant_id == tenant_id,
                    StandardCostRevisionModel.material_id == component_id,
                    StandardCostRevisionModel.status == "APPROVED",
                    StandardCostRevisionModel.is_deleted.is_(False),
                ).limit(1)
                has_approved = (await self._session.execute(approved_stmt)).scalar_one_or_none() is not None
                return {
                    "name": res.name, 
                    "code": res.code, 
                    "unit_name": res.unit_name or "pcs",
                    "material_type": res.material_type,
                    "current_cost": float(res.current_cost) if (has_approved and res.current_cost) else 0.0,
                }
            return {"name": "Unknown", "code": "???", "unit_name": "pcs", "material_type": None}
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
