import uuid
from typing import Any, List, Optional, Tuple, Type

from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload, joinedload

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.entities.bom_operation import BOMOperation
from backend.app.domain.bom.services.component_resolution import BOMResolutionError
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.models.bom_model import BOMModel, BOMLineModel
from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.repositories.base_repository import BaseRepository


class BOMRepository(BaseRepository[BillOfMaterial, BOMModel]):

    def _model_class(self) -> Type[BOMModel]:
        return BOMModel

    def _to_entity(self, model: BOMModel) -> BillOfMaterial:
        bom = BillOfMaterial(
            id=model.id,
            tenant_id=model.tenant_id,
            template_id=model.template_id,
            variant_id=model.variant_id,
            version=model.version,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            created_by=model.created_by,
            approved_by=model.approved_by,
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            operations_count=model.operations_count,
            making_charge=model.making_charge,
            making_charge_basis=model.making_charge_basis,
            lines=[],
            operations=[],
        )
        if hasattr(model, "lines") and model.lines is not None:
            for line_model in model.lines:
                if line_model.is_deleted:
                    continue
                bom.add_line(
                    BOMLine(
                        id=line_model.id,
                        tenant_id=line_model.tenant_id,
                        bom_id=line_model.bom_id,
                        material_id=line_model.material_id,
                        template_id=line_model.template_id,
                        variant_id=line_model.variant_id,
                        quantity=line_model.quantity, # type: ignore
                        scrap_percentage=line_model.scrap_percentage, # type: ignore
                        unit_id=line_model.unit_id,
                    )
                )
        if hasattr(model, "operations") and model.operations is not None:
            for operation_model in model.operations:
                if operation_model.is_deleted:
                    continue
                bom.add_operation(
                    BOMOperation(
                        id=operation_model.id,
                        tenant_id=operation_model.tenant_id,
                        bom_id=operation_model.bom_id,
                        operation_id=operation_model.operation_id,
                        sequence=operation_model.sequence,
                    )
                )
        return bom

    def _to_model(self, entity: BillOfMaterial) -> BOMModel:
        model = BOMModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            template_id=entity.template_id,
            variant_id=entity.variant_id,
            version=entity.version,
            is_active=entity.is_active,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            created_by=entity.created_by,
            approved_by=entity.approved_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            making_charge=float(entity.making_charge) if entity.making_charge is not None else None,
            making_charge_basis=entity.making_charge_basis,
        )
        model.lines = [
            BOMLineModel(
                id=line.id,
                tenant_id=line.tenant_id,
                bom_id=entity.id,  # Link to parent
                material_id=line.material_id,
                template_id=line.template_id,
                variant_id=line.variant_id,
                quantity=line.quantity, # type: ignore
                scrap_percentage=line.scrap_percentage, # type: ignore
                unit_id=line.unit_id,
            )
            for line in entity.lines
        ]
        model.operations = [
            BOMOperationModel(
                id=operation.id,
                tenant_id=operation.tenant_id,
                bom_id=entity.id,
                operation_id=operation.operation_id,
                sequence=operation.sequence,
                is_deleted=operation.is_deleted,
            )
            for operation in entity.operations
        ]
        return model

    # ── Override base get_by_id to eager load lines ───────────────────────────
    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[BillOfMaterial]:
        stmt = (
            select(BOMModel)
            .options(selectinload(BOMModel.lines), selectinload(BOMModel.operations))
            .where(
                BOMModel.id == id,
                BOMModel.tenant_id == tenant_id,
                BOMModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    # ── Custom Query Methods ──────────────────────────────────────────────────
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        """Gets the currently active BOM for a given product.

        Raises ValueError if multiple active BOMs are found — that indicates
        a data-integrity problem (concurrent activation race condition) that must
        be repaired manually rather than silently resolved.
        """
        from sqlalchemy.exc import MultipleResultsFound

        stmt = select(BOMModel).options(selectinload(BOMModel.lines), selectinload(BOMModel.operations)).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_active.is_(True),
            BOMModel.is_deleted.is_(False),
        )
        if template_id:
            stmt = stmt.where(BOMModel.template_id == template_id)
        if variant_id:
            stmt = stmt.where(BOMModel.variant_id == variant_id)

        result = await self._session.execute(stmt)
        try:
            model = result.scalar_one_or_none()
        except MultipleResultsFound:
            target_label = f"variant {variant_id}" if variant_id else f"template {template_id}"
            raise ValueError(
                f"Data integrity error: multiple active BOMs found for {target_label} "
                f"(tenant {tenant_id}). "
                "Only one BOM version may be active at a time. "
                "Deactivate all but one before proceeding."
            )
        return self._to_entity(model) if model else None

    async def get_by_version(
        self, tenant_id: uuid.UUID, version: str, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        """Gets a specific semantic version of a BOM for a given product."""
        stmt = select(BOMModel).options(selectinload(BOMModel.lines), selectinload(BOMModel.operations)).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.version == version,
            BOMModel.is_deleted.is_(False),
        )
        if template_id:
            stmt = stmt.where(BOMModel.template_id == template_id)
        if variant_id:
            stmt = stmt.where(BOMModel.variant_id == variant_id)
            
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def deactivate_all_for_product(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> None:
        """Sets all BOMs for a specific product to inactive, usually called before activating a new one."""
        stmt = update(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
        ).values(is_active=False)
        
        if template_id:
            stmt = stmt.where(BOMModel.template_id == template_id)
        if variant_id:
            stmt = stmt.where(BOMModel.variant_id == variant_id)
            
        await self._session.execute(stmt)

    async def list_product_boms(
        self,
        tenant_id: uuid.UUID,
        template_id: Optional[uuid.UUID] = None,
        variant_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[BillOfMaterial], int]:
        """List all BOMs for a given product (versions history)"""
        base_stmt = select(BOMModel).where(
            BOMModel.tenant_id == tenant_id,
            BOMModel.is_deleted.is_(False),
        )
        
        if template_id:
            base_stmt = base_stmt.where(BOMModel.template_id == template_id)
        if variant_id:
            base_stmt = base_stmt.where(BOMModel.variant_id == variant_id)

        # Count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Paginate
        paged = (
            base_stmt
            .options(selectinload(BOMModel.lines))
            .options(selectinload(BOMModel.operations))
            .order_by(BOMModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(paged)).scalars().all()
        return [self._to_entity(r) for r in rows], total

    async def get_component_info(
        self, tenant_id: uuid.UUID, *, material_id: Optional[uuid.UUID] = None,
        variant_id: Optional[uuid.UUID] = None, template_id: Optional[uuid.UUID] = None,
        allow_inactive: bool = False,
    ) -> dict[str, Any]:
        """Read exact component identity and configured base UOM, never a name/SKU match."""
        model_type = MaterialModel if material_id else ItemVariantModel if variant_id else ItemTemplateModel
        component_id = material_id or variant_id or template_id
        model = (await self._session.execute(select(model_type).where(
            model_type.id == component_id, model_type.tenant_id == tenant_id,
            model_type.is_deleted.is_(False),
            *(() if allow_inactive else (model_type.is_active.is_(True),)),
        ))).scalar_one_or_none()
        if model is None:
            raise BOMResolutionError("COMPONENT_INVALID", "Component is missing, inactive, deleted or outside this tenant")
        if variant_id:
            template = (await self._session.execute(select(ItemTemplateModel.id).where(
                ItemTemplateModel.id == model.template_id, ItemTemplateModel.tenant_id == tenant_id,
                ItemTemplateModel.is_deleted.is_(False),
                *(() if allow_inactive else (ItemTemplateModel.is_active.is_(True),)),
            ))).scalar_one_or_none()
            if template is None:
                raise BOMResolutionError("TARGET_INVALID", "The variant's template is missing, inactive or deleted")
        unit = (await self._session.execute(select(UnitOfMeasureModel).where(
            UnitOfMeasureModel.id == model.base_unit_id, UnitOfMeasureModel.tenant_id == tenant_id,
            UnitOfMeasureModel.is_deleted.is_(False), UnitOfMeasureModel.is_active.is_(True),
        ))).scalar_one_or_none() if model.base_unit_id else None
        return {"name": model.name, "code": model.code,
                "material_type": model.material_type if material_id else None,
                "base_unit_id": unit.id if unit else None,
                "unit_name": unit.code if unit else None}

    async def get_bom_for_material(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Optional[BillOfMaterial]:
        """Resolve explicit SF material → variant → active BOM, failing closed on broken mappings.

        None means no manufacturing mapping at all. A mapping that exists but
        cannot yield one valid active BOM is a costing error, not a purchased leaf.
        """
        info = await self.get_component_info(tenant_id, material_id=material_id)
        if info["material_type"] != "semi_finished":
            return None
        mappings = (await self._session.execute(select(ItemVariantModel).where(
            ItemVariantModel.material_id == material_id, ItemVariantModel.tenant_id == tenant_id,
        ))).scalars().all()
        if not mappings:
            return None
        valid = [variant for variant in mappings if variant.is_active and not variant.is_deleted]
        if not valid:
            raise BOMResolutionError("MAPPING_INVALID", "Manufacturing mapping exists but its variant is inactive or deleted")
        if len(valid) != 1:
            raise BOMResolutionError("MAPPING_AMBIGUOUS", "Multiple active variants map to this semi-finished material")
        variant = valid[0]
        await self.get_component_info(tenant_id, variant_id=variant.id)
        try:
            child = await self.get_active_bom(tenant_id, variant_id=variant.id)
        except ValueError as exc:
            raise BOMResolutionError("BOM_AMBIGUOUS", str(exc)) from exc
        if child is None:
            raise BOMResolutionError("BOM_MISSING", "Manufacturing mapping exists but no active, nondeleted child BOM exists")
        return child
