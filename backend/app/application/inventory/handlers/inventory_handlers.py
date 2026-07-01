from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.app.application.inventory.commands.inventory_commands import (
    MISSING,
    CreateMaterialCommand,
    UpdateMaterialCommand,
    AddStockCommand,
    RemoveStockCommand,
    AdjustStockCommand,
)
from backend.app.domain.inventory.entities.material import Material
from backend.app.domain.inventory.entities.inventory_transaction import (
    InventoryTransaction,
    TransactionType,
    ReferenceType,
)
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.persistence.models.inventory_management_models import StockLedgerModel
from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.application.inventory.services.low_stock_checker import LowStockChecker
from backend.app.application.manufacturing.services.inventory_service import InventoryService
from datetime import datetime
from datetime import timezone

logger = logging.getLogger(__name__)


@dataclass
class MaterialResult:
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    item_code: str
    item_type: str
    name: str
    material_type: str
    description: Optional[str]
    category_id: Optional[uuid.UUID]
    base_unit_id: Optional[uuid.UUID]
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    reorder_level: Optional[Decimal]
    location_id: Optional[uuid.UUID]
    is_batch_tracked: bool
    is_serialized: bool
    code_locked: bool
    inspection_required: bool
    inspection_template_id: Optional[uuid.UUID]
    is_active: bool
    is_low_stock: bool

def _to_result(m: Material) -> MaterialResult:
    return MaterialResult(
        id=m.id,
        tenant_id=m.tenant_id,
        code=m.code,
        item_code=m.item_code,
        item_type=m.item_type,
        name=m.name,
        material_type=m.material_type.value if hasattr(m.material_type, 'value') else m.material_type,
        description=m.description,
        category_id=m.category_id,
        base_unit_id=m.base_unit_id,
        current_stock=m.current_stock,
        reserved_stock=m.reserved_stock,
        available_stock=m.get_available_stock(),
        reorder_level=m.reorder_level,
        location_id=m.location_id,
        is_batch_tracked=m.is_batch_tracked,
        is_serialized=m.is_serialized,
        code_locked=m.code_locked,
        inspection_required=m.inspection_required,
        inspection_template_id=m.inspection_template_id,
        is_active=m.is_active,
        is_low_stock=m.is_low_stock(),
    )


# ── Create Material ────────────────────────────────────────────────────────
class CreateMaterialHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        uow: SQLAlchemyUnitOfWork,
        item_code_service: ItemCodeService | None = None,
    ):
        self._repo = material_repo
        self._uow = uow
        self._item_code_service = item_code_service

    async def handle(self, cmd: CreateMaterialCommand) -> MaterialResult:
        normalized_name = Material.normalize_name(cmd.name)
        normalized_type = Material.coerce_material_type(cmd.material_type)
        Material.validate_name_for_type(normalized_name, normalized_type)

        # Backward-compat for existing flows/tests: if category_id is omitted,
        # default to tenant-scoped "Uncategorized".
        if cmd.category_id is None:
            from sqlalchemy import select
            from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel

            uncategorized = await self._uow.session.scalar(
                select(MaterialCategoryModel.id).where(
                    MaterialCategoryModel.tenant_id == cmd.tenant_id,
                    MaterialCategoryModel.is_deleted.is_(False),
                    MaterialCategoryModel.name == "Uncategorized",
                )
            )
            if uncategorized is None:
                # Ensure backward-compat for tests/older flows where category_id is omitted.
                # Create a tenant-scoped "Uncategorized" category if it doesn't exist.
                now = datetime.now(timezone.utc)
                category = MaterialCategoryModel(
                    id=uuid.uuid4(),
                    tenant_id=cmd.tenant_id,
                    name="Uncategorized",
                    code_prefix="GEN",
                    description=None,
                    is_active=True,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
                self._uow.session.add(category)
                await self._uow.session.flush()
                uncategorized = category.id

            cmd = CreateMaterialCommand(
                tenant_id=cmd.tenant_id,
                created_by=cmd.created_by,
                code=cmd.code,
                name=cmd.name,
                material_type=cmd.material_type,
                description=cmd.description,
                category_id=uncategorized,
                base_unit_id=cmd.base_unit_id,
                reorder_level=cmd.reorder_level,
                location_id=cmd.location_id,
                is_batch_tracked=cmd.is_batch_tracked,
                is_serialized=cmd.is_serialized,
                opening_stock=cmd.opening_stock,
            )

        # at this point category_id must be non-null
        category_id = cmd.category_id
        if category_id is None:
            raise ValueError("Category is required for item code generation.")

        if self._item_code_service is not None:
            if cmd.code:
                normalized_code = await self._item_code_service.validate_manual_code(
                    tenant_id=cmd.tenant_id,
                    code=cmd.code,
                    target="material",
                )
            else:
                # Check if a Number Series config already exists for this tenant.
                # If so, use the new generate_for_entity() method with entity_name.
                # If not, fall back to legacy generate() for backward compatibility (Req 14.2).
                existing_config = await self._item_code_service._try_load_config(
                    tenant_id=cmd.tenant_id,
                    entity_type="material",
                )
                if existing_config is not None:
                    normalized_code = await self._item_code_service.generate_for_entity(
                        tenant_id=cmd.tenant_id,
                        entity_type="material",
                        sub_type=normalized_type.value,
                        entity_name=normalized_name,
                        user_id=cmd.created_by,
                    )
                else:
                    normalized_code = await self._item_code_service.generate(
                        tenant_id=cmd.tenant_id,
                        item_type=normalized_type.value,
                        category_id=category_id,
                        target="material",
                    )
        else:
            normalized_code = Material.normalize_code(cmd.code or "")

        if await self._repo.code_exists(normalized_code, cmd.tenant_id):
            raise ValueError(f"Material with code '{normalized_code}' already exists in this tenant.")
        if await self._repo.name_exists(normalized_name, cmd.tenant_id, material_type=normalized_type):
            raise ValueError(
                f"{normalized_type.value.title()} material name '{normalized_name}' already exists in this tenant."
            )

        # code_locked=True ensures code immutability after assignment (Req 9.1)
        material = Material(
            tenant_id=cmd.tenant_id,
            code=normalized_code,
            name=normalized_name,
            material_type=normalized_type,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            reorder_level=cmd.reorder_level,
            location_id=cmd.location_id,
            is_batch_tracked=cmd.is_batch_tracked,
            is_serialized=cmd.is_serialized,
            code_locked=True,
        )
        await self._repo.save(material)

        # Opening stock: if provided and > 0, increase stock and record transaction atomically
        opening_stock = cmd.opening_stock
        if opening_stock is not None and opening_stock > Decimal("0"):
            material.increase_stock(opening_stock)
            await self._repo.save(material)

            tx = InventoryTransaction(
                tenant_id=cmd.tenant_id,
                material_id=material.id,
                transaction_type=TransactionType.IN,
                quantity=opening_stock,
                reference_type=ReferenceType.OPENING_BALANCE,
                remarks="Opening balance",
                created_by=cmd.created_by,
            )
            tx_repo = TransactionRepository(self._uow.session)
            await tx_repo.save(tx)

        await self._uow.commit()
        return _to_result(material)


# ── Update Material ────────────────────────────────────────────────────────
class UpdateMaterialHandler:
    def __init__(self, material_repo: MaterialRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = material_repo
        self._uow = uow

    async def handle(self, cmd: UpdateMaterialCommand) -> MaterialResult:
        material = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.id} not found.")

        # ── Code immutability enforcement ──────────────────────────────────
        # If the request includes a code value that differs from the current one,
        # and code_locked is True, reject with an immutability error.
        if cmd.code is not MISSING and cmd.code is not None:
            requested_code = cmd.code.strip()
            if requested_code and requested_code != material.code:
                if material.code_locked:
                    raise ValueError("Item code is immutable")
        # If code is omitted (MISSING) or None, retain existing code unchanged.

        next_name = Material.normalize_name(cmd.name) if cmd.name is not None else material.name
        next_type = (
            Material.coerce_material_type(cmd.material_type)
            if cmd.material_type is not None
            else material.material_type
        )
        Material.validate_name_for_type(next_name, next_type)

        if (
            cmd.name is not None
            or cmd.material_type is not None
        ) and await self._repo.name_exists(
            next_name,
            cmd.tenant_id,
            material_type=next_type,
            exclude_id=material.id,
        ):
            raise ValueError(
                f"{next_type.value.title()} material name '{next_name}' already exists in this tenant."
            )

        material.update(
            name=next_name if cmd.name is not None else None,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            material_type=next_type if cmd.material_type is not None else None,
            reorder_level=cmd.reorder_level,
            location_id=cmd.location_id,
            is_batch_tracked=cmd.is_batch_tracked,
            is_serialized=cmd.is_serialized,
            is_active=cmd.is_active,
        )
        if cmd.inspection_required is not MISSING:
            material.inspection_required = cmd.inspection_required
        if cmd.inspection_template_id is not MISSING:
            material.inspection_template_id = cmd.inspection_template_id
        await self._repo.save(material)
        await self._uow.commit()
        return _to_result(material)


# ── Add Stock ──────────────────────────────────────────────────────────────
class AddStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AddStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot add stock to an inactive material.")

        # Capture stock level before mutation for low-stock threshold check
        previous_stock = material.current_stock

        await InventoryService(self._uow.session).add_stock(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            to_location_id=cmd.to_location_id,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks,
            created_by=cmd.created_by,
        )
        await self._uow.commit()
        updated = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not updated:
            raise ValueError(f"Material {cmd.material_id} not found.")

        # Check for low-stock threshold crossing and notify if needed.
        # Notification failure must not affect the stock mutation.
        try:
            checker = LowStockChecker(self._uow.session)
            notification_id = await checker.check_and_notify(
                tenant_id=cmd.tenant_id,
                material=updated,
                previous_stock=previous_stock,
                actor_user_id=cmd.created_by,
            )
            if notification_id is not None:
                await self._uow.commit()
        except Exception:
            logger.exception(
                "Low stock check failed after AddStock for material %s. "
                "Stock mutation succeeded.",
                cmd.material_id,
            )

        return _to_result(updated)


# ── Remove Stock ───────────────────────────────────────────────────────────
class RemoveStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: RemoveStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot remove stock from an inactive material.")

        # Capture stock level before mutation for low-stock threshold check
        previous_stock = material.current_stock

        await InventoryService(self._uow.session).remove_stock(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            from_location_id=cmd.from_location_id,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks,
            created_by=cmd.created_by,
        )
        await self._uow.commit()
        updated = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not updated:
            raise ValueError(f"Material {cmd.material_id} not found.")

        # Check for low-stock threshold crossing and notify if needed.
        # Notification failure must not affect the stock mutation.
        try:
            checker = LowStockChecker(self._uow.session)
            notification_id = await checker.check_and_notify(
                tenant_id=cmd.tenant_id,
                material=updated,
                previous_stock=previous_stock,
                actor_user_id=cmd.created_by,
            )
            if notification_id is not None:
                await self._uow.commit()
        except Exception:
            logger.exception(
                "Low stock check failed after RemoveStock for material %s. "
                "Stock mutation succeeded.",
                cmd.material_id,
            )

        return _to_result(updated)


# ── Adjust Stock ───────────────────────────────────────────────────────────
class AdjustStockHandler:
    def __init__(
        self,
        material_repo: MaterialRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AdjustStockCommand) -> MaterialResult:
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot adjust stock for an inactive material.")

        # Capture stock level before mutation for low-stock threshold check
        previous_stock = material.current_stock

        await InventoryService(self._uow.session).adjust_stock(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            new_quantity=cmd.new_quantity,
            unit_id=cmd.unit_id,
            location_id=cmd.location_id,
            remarks=cmd.remarks or f"Adjusted to {cmd.new_quantity}",
            created_by=cmd.created_by,
        )
        await self._uow.commit()
        updated = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not updated:
            raise ValueError(f"Material {cmd.material_id} not found.")

        # Check for low-stock threshold crossing and notify if needed.
        # Notification failure must not affect the stock mutation.
        try:
            checker = LowStockChecker(self._uow.session)
            notification_id = await checker.check_and_notify(
                tenant_id=cmd.tenant_id,
                material=updated,
                previous_stock=previous_stock,
                actor_user_id=cmd.created_by,
            )
            if notification_id is not None:
                await self._uow.commit()
        except Exception:
            logger.exception(
                "Low stock check failed after AdjustStock for material %s. "
                "Stock mutation succeeded.",
                cmd.material_id,
            )

        return _to_result(updated)
