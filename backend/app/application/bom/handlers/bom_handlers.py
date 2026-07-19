import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from backend.app.application.bom.commands.bom_commands import (
    CreateBOMCommand,
    UpdateBOMCommand,
    CopyBOMCommand,
    ActivateBOMCommand,
    DeleteBOMCommand,
)
from backend.app.application.bom.queries.bom_queries import GetBOMQuery, ListBOMsQuery
from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.entities.bom_line import BOMLine
from backend.app.domain.bom.entities.bom_operation import BOMOperation
from backend.app.domain.inventory.entities.material import MaterialType
from backend.app.domain.bom.services.bom_validation_service import BOMValidationService
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
from backend.app.infrastructure.services.bom_providers import InfrastructureBOMProvider


from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class BOMHandlers:
    def __init__(self, bom_repo: BOMRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = bom_repo
        self._uow = uow

    def _ensure_unique_components(self, lines) -> None:
        seen: set[tuple[str, uuid.UUID]] = set()
        for line_input in lines:
            if line_input.material_id:
                key = ("material", line_input.material_id)
            elif line_input.template_id:
                key = ("template", line_input.template_id)
            else:
                key = ("variant", line_input.variant_id)
            if key in seen:
                raise ValueError(
                    f"Duplicate {key[0]} component in BOM. Edit the existing line quantity instead of adding it again."
                )
            seen.add(key)

    async def _validate_material_components(self, tenant_id: uuid.UUID, lines) -> None:
        material_ids = list({line.material_id for line in lines if line.material_id is not None})
        if not material_ids:
            return

        stmt = select(
            MaterialModel.id,
            MaterialModel.name,
            MaterialModel.material_type,
        ).where(
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
            MaterialModel.id.in_(material_ids),
        )
        result = await self._uow.session.execute(stmt)
        materials = {row.id: row for row in result}

        missing_ids = [str(material_id) for material_id in material_ids if material_id not in materials]
        if missing_ids:
            raise ValueError(
                "One or more selected raw materials do not exist for this tenant: "
                + ", ".join(missing_ids[:3])
            )

        invalid_materials = [
            row.name
            for row in materials.values()
            if str(row.material_type).strip().lower() != MaterialType.RAW.value
        ]
        if invalid_materials:
            raise ValueError(
                "Only raw materials can be added as BOM material lines. "
                "Use template or variant lines for sub-assemblies or finished goods: "
                + ", ".join(invalid_materials[:3])
            )

    # ── Commands ─────────────────────────────────────────────────────────────

    async def handle_create(self, cmd: CreateBOMCommand) -> BillOfMaterial:
        self._ensure_unique_components(cmd.lines)
        await self._validate_material_components(cmd.tenant_id, cmd.lines)
        # Build domain entity – constructor enforces that exactly one of template/variant is provided
        bom = BillOfMaterial(
            tenant_id=cmd.tenant_id,
            template_id=cmd.template_id,
            variant_id=cmd.variant_id,
            version=cmd.version,
            valid_from=cmd.valid_from,
            valid_to=cmd.valid_to,
            created_by=cmd.created_by,
            approved_by=cmd.approved_by,
            is_active=False,
        )
        for line_input in cmd.lines:
            bom.add_line(
                BOMLine(
                    tenant_id=cmd.tenant_id,
                    bom_id=bom.id,
                    material_id=line_input.material_id,
                    template_id=line_input.template_id,
                    variant_id=line_input.variant_id,
                    quantity=line_input.quantity,
                    scrap_percentage=line_input.scrap_percentage,
                    unit_id=line_input.unit_id,
                )
            )

        # Validate Circular Dependencies
        provider = InfrastructureBOMProvider(self._repo)
        validator = BOMValidationService(provider)
        await validator.validate_no_circular_dependencies(cmd.tenant_id, bom)

        await self._repo.save(bom)
        await self._uow.commit()
        return bom

    async def handle_update(self, cmd: UpdateBOMCommand) -> BillOfMaterial:
        bom = await self._repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        if bom.is_active:
            raise ValueError("Cannot update an active BOM. Deactivate it first or create a new version.")
        if cmd.valid_from is not None:
            bom.valid_from = cmd.valid_from
        if cmd.valid_to is not None:
            bom.valid_to = cmd.valid_to
        if cmd.approved_by is not None:
            bom.approved_by = cmd.approved_by
        if cmd.lines is not None:
            self._ensure_unique_components(cmd.lines)
            await self._validate_material_components(cmd.tenant_id, cmd.lines)
            bom.lines.clear()
            for line_input in cmd.lines:
                bom.add_line(
                    BOMLine(
                        tenant_id=cmd.tenant_id,
                        bom_id=bom.id,
                        material_id=line_input.material_id,
                        template_id=line_input.template_id,
                        variant_id=line_input.variant_id,
                        quantity=line_input.quantity,
                        scrap_percentage=line_input.scrap_percentage,
                        unit_id=line_input.unit_id,
                    )
                )
        bom._touch()

        # Validate Circular Dependencies
        provider = InfrastructureBOMProvider(self._repo)
        validator = BOMValidationService(provider)
        await validator.validate_no_circular_dependencies(cmd.tenant_id, bom)

        await self._repo.save(bom)
        await self._uow.commit()
        return bom

    async def handle_activate(self, cmd: ActivateBOMCommand) -> BillOfMaterial:
        bom = await self._repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        # Deactivate all other BOMs for this product first
        await self._repo.deactivate_all_for_product(
            tenant_id=cmd.tenant_id,
            template_id=bom.template_id,
            variant_id=bom.variant_id,
        )
        bom.activate()
        await self._repo.save(bom)
        await self._uow.commit()
        return bom

    async def handle_copy(self, cmd: CopyBOMCommand) -> BillOfMaterial:
        source = await self._repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not source:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        # Check if new version exists
        existing = await self._repo.get_by_version(
            tenant_id=cmd.tenant_id,
            version=cmd.new_version,
            template_id=source.template_id,
            variant_id=source.variant_id,
        )
        if existing:
            raise ValueError(f"BOM version '{cmd.new_version}' already exists for this product.")
        new_bom = BillOfMaterial(
            tenant_id=source.tenant_id,
            template_id=source.template_id,
            variant_id=source.variant_id,
            version=cmd.new_version,
            valid_from=source.valid_from,
            valid_to=source.valid_to,
            created_by=cmd.created_by,
            is_active=False,
        )
        for line in source.lines:
            new_bom.add_line(
                BOMLine(
                    tenant_id=source.tenant_id,
                    bom_id=new_bom.id,
                    material_id=line.material_id,
                    template_id=line.template_id,
                    variant_id=line.variant_id,
                    quantity=line.quantity,
                    scrap_percentage=line.scrap_percentage,
                    unit_id=line.unit_id,
                )
            )
        for operation in source.operations:
            new_bom.add_operation(
                BOMOperation(
                    tenant_id=source.tenant_id,
                    bom_id=new_bom.id,
                    operation_id=operation.operation_id,
                    sequence=operation.sequence,
                )
            )
        await self._repo.save(new_bom)
        await self._uow.commit()
        return new_bom

    async def handle_delete(self, cmd: DeleteBOMCommand) -> None:
        bom = await self._repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        if bom.is_active:
            raise ValueError("Cannot delete an active BOM.")
        bom.soft_delete()
        await self._repo.save(bom)
        await self._uow.commit()

    # ── Queries ─────────────────────────────────────────────────────────────

    async def handle_get(self, query: GetBOMQuery) -> BillOfMaterial:
        bom = await self._repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")
        return bom

    async def handle_list(self, query: ListBOMsQuery):
        return await self._repo.list_product_boms(
            tenant_id=query.tenant_id,
            template_id=query.template_id,
            variant_id=query.variant_id,
            page=query.page,
            page_size=query.page_size,
        )
