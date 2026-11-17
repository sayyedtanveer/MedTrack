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
        cost_rollup = CostRollupService(
            provider, InfrastructureCostProvider(self._uow._session),
            InfrastructureTenantProvider(self._uow._session), component_resolver=provider,
        )
        service = BOMBrowserService(provider, details, cost_rollup=cost_rollup)
        
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
        service = CostRollupService(bom_provider, cost_provider, tenant_provider, component_resolver=bom_provider)
        
        return await service.calculate_standard_cost(query.tenant_id, bom, max_depth=query.max_depth)

    async def handle_cost_analysis(self, tenant_id: uuid.UUID, bom_id: uuid.UUID) -> Dict[str, Any]:
        """Analyze the existing rollup using its exact tree values."""
        from datetime import datetime, timezone
        from backend.app.domain.bom.services.component_resolution import BOMResolutionError
        from backend.app.infrastructure.persistence.models.tenant_model import TenantModel

        bom = await self._bom_repo.get_by_id(bom_id, tenant_id)
        if bom is None:
            raise LookupError("BOM not found")
        session = self._uow._session
        provider = InfrastructureBOMProvider(self._bom_repo)
        result = await CostRollupService(
            provider, InfrastructureCostProvider(session), InfrastructureTenantProvider(session),
        ).calculate_standard_cost(tenant_id, bom, exact_tree=True, tree_row_limit=5000)
        tree = result["tree"]
        target = {}
        try:
            target = await self._bom_repo.get_component_info(
                tenant_id, template_id=bom.template_id, variant_id=bom.variant_id, allow_inactive=True,
            )
        except BOMResolutionError as exc:
            result["missing_costs"].append({
                "component_type": "bom", "component_id": str(bom.id), "reason": exc.reason, "message": str(exc),
            })
        if not target.get("unit_name") and not any(
            issue["component_id"] == str(bom.id) for issue in result["missing_costs"]
        ):
            result["missing_costs"].append({
                "component_type": "bom", "component_id": str(bom.id),
                "reason": "OUTPUT_UOM_MISSING", "message": "The selected BOM has no active output UOM.",
            })
        complete = not result["missing_costs"]
        direct = Decimal("0")
        nested = Decimal("0")
        flat = dict(material=Decimal("0"), operations=Decimal("0"), outside_processing=Decimal("0"))
        if complete:
            for node in tree["children"]:
                if node["cost_basis"] == "CHILD_BOM":
                    nested += node["cost"]
                else:
                    direct += node["cost"]

            def collect(node: Dict[str, Any]) -> None:
                if node.get("cost_basis") == "STANDARD_COST":
                    flat["material"] += node["cost"]
                    return
                flat["operations"] += node.get("operation_cost", Decimal("0"))
                flat["outside_processing"] += node.get("making_cost", Decimal("0"))
                for child in node["children"]:
                    collect(child)

            collect(tree)
            if (sum(flat.values()) != result["total_cost"]
                or direct + nested + result["operation_cost"] + result["making_cost"] != result["total_cost"]):
                raise ArithmeticError("BOM analysis categories do not reconcile")

        operation_ids = set()

        def gather_operations(node: Dict[str, Any]) -> None:
            operation_ids.update(uuid.UUID(op["operation_id"]) for op in node.get("operations", []))
            for child in node["children"]:
                gather_operations(child)

        gather_operations(tree)
        if operation_ids:
            operations = (await session.execute(select(
                OperationModel.id, OperationModel.operation_code, OperationModel.name,
            ).where(
                OperationModel.tenant_id == tenant_id, OperationModel.is_deleted.is_(False),
                OperationModel.id.in_(operation_ids),
            ))).all()
            operation_names = {str(op.id): (op.operation_code, op.name) for op in operations}

            def attach_operation_names(node: Dict[str, Any]) -> None:
                for op in node.get("operations", []):
                    op["code"], op["name"] = operation_names.get(op["operation_id"], (None, "Operation"))
                for child in node["children"]:
                    attach_operation_names(child)

            attach_operation_names(tree)

        company = (await session.execute(select(TenantModel.name).where(
            TenantModel.id == tenant_id, TenantModel.is_deleted.is_(False),
        ))).scalar_one_or_none()
        template_id = bom.template_id
        if bom.variant_id:
            template_id = (await session.execute(select(ItemVariantModel.template_id).where(
                ItemVariantModel.id == bom.variant_id, ItemVariantModel.tenant_id == tenant_id,
                ItemVariantModel.is_deleted.is_(False),
            ))).scalar_one_or_none()
        product = None
        if template_id:
            row = (await session.execute(select(ItemTemplateModel.code, ItemTemplateModel.name).where(
                ItemTemplateModel.id == template_id, ItemTemplateModel.tenant_id == tenant_id,
                ItemTemplateModel.is_deleted.is_(False),
            ))).first()
            if row:
                product = {"code": row.code, "name": row.name}
        return {
            "bom_id": str(bom.id), "version": bom.version, "is_active": bom.is_active,
            "company": company, "product": product, "target_code": target.get("code"),
            "target_name": target.get("name"), "variant_id": str(bom.variant_id) if bom.variant_id else None,
            "output_quantity": 1, "output_uom": target.get("unit_name"),
            "generated_at": datetime.now(timezone.utc),
            "currency_code": result["currency_code"], "currency_symbol": result["currency_symbol"],
            "is_complete": complete, "missing_costs": result["missing_costs"],
            "total_cost": result["total_cost"] if complete else None,
            "direct_material_cost": direct if complete else None,
            "nested_cost": nested if complete else None,
            "own_operation_cost": result["operation_cost"], "own_outside_processing_cost": result["making_cost"],
            "composition": flat if complete else None, "tree": tree,
        }

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
