import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.services.bom_browser_service import BOMBrowserService, BOMProvider, ComponentDetailProvider
from backend.app.domain.bom.services.cost_rollup_service import CostRollupService, CostProvider
from backend.app.application.bom.queries.bom_advanced_queries import GetBOMTreeQuery, GetBOMCostQuery
from backend.app.infrastructure.services.bom_providers import (
    InfrastructureBOMProvider,
    InfrastructureCostProvider,
    InfrastructureComponentDetailProvider,
    InfrastructureTenantProvider
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.bom.queries.bom_advanced_queries import GetBOMTreeQuery, GetBOMCostQuery, ValidateBOMQuery
from backend.app.domain.bom.services.bom_validation_service import BOMValidationService

from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.operation_model import OperationModel


class BOMAdvancedHandlers:
    def __init__(self, uow: SQLAlchemyUnitOfWork, bom_repo):
        self._uow = uow
        self._bom_repo = bom_repo

    async def handle_get_tree(self, query: GetBOMTreeQuery) -> Dict[str, Any]:
        bom = await self._bom_repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")

        provider = InfrastructureBOMProvider(self._bom_repo)
        details = InfrastructureComponentDetailProvider(self._uow._session)
        service = BOMBrowserService(provider, details)
        
        tree = await service.build_tree(query.tenant_id, bom, max_depth=query.max_depth)
        
        # If parent_id is requested, find it in the tree and return it as root
        if query.parent_id and str(query.parent_id) != str(query.bom_id):
            return service.find_node_in_tree(tree, str(query.parent_id)) or {}
            
        return tree

    async def handle_get_cost(self, query: GetBOMCostQuery) -> Dict[str, Any]:
        bom = await self._bom_repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")

        bom_provider = InfrastructureBOMProvider(self._bom_repo)
        cost_provider = InfrastructureCostProvider(self._uow._session)
        tenant_provider = InfrastructureTenantProvider(self._uow._session)
        service = CostRollupService(bom_provider, cost_provider, tenant_provider)
        
        return await service.calculate_standard_cost(query.tenant_id, bom, max_depth=query.max_depth)

    async def handle_validate(self, query: ValidateBOMQuery) -> Dict[str, Any]:
        bom = await self._bom_repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")

        result = {
            "missing_components": [],
            "inactive_items": [],
            "invalid_operations": [],
            "missing_units": [],
            "invalid_quantities": [],
            "circular_dependency": False
        }

        # 1. Circular dependency
        provider = InfrastructureBOMProvider(self._bom_repo)
        val_service = BOMValidationService(provider)
        try:
            await val_service.validate_no_circular_dependencies(query.tenant_id, bom)
        except ValueError as e:
            result["circular_dependency"] = str(e)

        session = self._uow._session

        # 2. Lines Validation
        for line in bom.lines:
            target_id = line.template_id or line.variant_id or line.material_id
            
            if float(line.quantity) <= 0:
                result["invalid_quantities"].append({"line_id": str(line.id), "component_id": str(target_id), "quantity": float(line.quantity)})
            
            if not line.unit_id:
                result["missing_units"].append({"line_id": str(line.id), "component_id": str(target_id)})

            # Check component existence/active
            if line.material_id:
                stmt = select(MaterialModel.is_deleted, MaterialModel.is_active).where(MaterialModel.id == line.material_id, MaterialModel.tenant_id == query.tenant_id)
            elif line.variant_id:
                stmt = select(ItemVariantModel.is_deleted, ItemVariantModel.is_active).where(ItemVariantModel.id == line.variant_id, ItemVariantModel.tenant_id == query.tenant_id)
            elif line.template_id:
                stmt = select(ItemTemplateModel.is_deleted, ItemTemplateModel.is_active).where(ItemTemplateModel.id == line.template_id, ItemTemplateModel.tenant_id == query.tenant_id)
            else:
                continue
                
            row = (await session.execute(stmt)).first()
            if not row or row.is_deleted:
                result["missing_components"].append(str(target_id))
            elif not row.is_active:
                result["inactive_items"].append(str(target_id))

        # 3. Operations Validation
        for op in bom.operations:
            stmt = select(OperationModel.is_deleted, OperationModel.is_active).where(OperationModel.id == op.operation_id, OperationModel.tenant_id == query.tenant_id)
            row = (await session.execute(stmt)).first()
            if not row or row.is_deleted or not row.is_active:
                result["invalid_operations"].append(str(op.operation_id))

        return result
