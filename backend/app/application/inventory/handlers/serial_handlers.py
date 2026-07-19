from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from backend.app.application.inventory.commands.inventory_commands import (
    AddSerialStockCommand,
    IssueSerialCommand,
    ReturnSerialCommand,
)
from backend.app.application.inventory.queries.inventory_queries import (
    GetSerialDetailsQuery,
    GetSerialsByMaterialQuery,
)
from backend.app.domain.inventory.entities.inventory_transaction import (
    InventoryTransaction,
    ReferenceType,
    TransactionType,
)
from backend.app.domain.inventory.entities.serial_number import SerialNumber, SerialStatus
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.serial_number_repository import SerialNumberRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.manufacturing.services.inventory_service import InventoryService


# ── Result DTOs ────────────────────────────────────────────────────────────────

@dataclass
class SerialResult:
    id: uuid.UUID
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    serial_number: str
    status: str
    current_location_id: Optional[uuid.UUID]
    reference_id: Optional[uuid.UUID]
    created_at: str


def _to_serial_result(s: SerialNumber) -> SerialResult:
    return SerialResult(
        id=s.id,
        tenant_id=s.tenant_id,
        material_id=s.material_id,
        serial_number=s.serial_number,
        status=s.status.value,
        current_location_id=s.current_location_id,
        reference_id=s.reference_id,
        created_at=s.created_at.isoformat(),
    )


# ── Add Serial Stock ───────────────────────────────────────────────────────────

class AddSerialStockHandler:
    """
    Registers a list of serial numbers for a serialised material.
    - Validates material.is_serialized.
    - Rejects any duplicate serial within the tenant.
    - Creates SerialNumber entities with status=IN_STOCK.
    - Increases Material.current_stock by the count of serials added.
    """

    def __init__(
        self,
        material_repo: MaterialRepository,
        serial_repo: SerialNumberRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._material_repo = material_repo
        self._serial_repo = serial_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: AddSerialStockCommand) -> List[SerialResult]:
        if not cmd.serial_numbers:
            raise ValueError("At least one serial number must be provided.")

        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        if not material.is_active:
            raise ValueError("Cannot add stock to an inactive material.")
        if not material.is_serialized:
            raise ValueError(
                f"Material '{material.code}' is not serialized. "
                "Set is_serialized=true before using serial stock operations."
            )

        # Check for duplicates within the batch before any writes
        duplicates = []
        for sn in cmd.serial_numbers:
            if await self._serial_repo.serial_exists(sn, cmd.tenant_id):
                duplicates.append(sn)
        if duplicates:
            raise ValueError(f"Serial numbers already exist in this tenant: {', '.join(duplicates)}")

        # Create serial entities
        serials: List[SerialNumber] = []
        for sn in cmd.serial_numbers:
            serial = SerialNumber(
                tenant_id=cmd.tenant_id,
                material_id=cmd.material_id,
                serial_number=sn,
                status=SerialStatus.IN_STOCK,
                current_location_id=cmd.location_id,
            )
            serials.append(serial)

        count = Decimal(str(len(serials)))
        await InventoryService(self._uow.session).add_stock(
            tenant_id=cmd.tenant_id,
            material_id=cmd.material_id,
            quantity=count,
            unit_id=None,
            created_by=cmd.created_by,
            to_location_id=cmd.location_id,
            remarks=cmd.remarks or f"Serial IN — {len(serials)} unit(s)",
        )

        for serial in serials:
            await self._serial_repo.save(serial)
        await self._uow.commit()
        return [_to_serial_result(s) for s in serials]


# ── Issue Serial ───────────────────────────────────────────────────────────────

class IssueSerialHandler:
    """
    Issues a serial (transitions IN_STOCK/RETURNED → ISSUED).
    Decrements Material.current_stock by 1.
    """

    def __init__(
        self,
        material_repo: MaterialRepository,
        serial_repo: SerialNumberRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._material_repo = material_repo
        self._serial_repo = serial_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: IssueSerialCommand) -> SerialResult:
        serial = await self._serial_repo.get_by_serial(cmd.serial_number, cmd.tenant_id)
        if not serial:
            raise ValueError(f"Serial number '{cmd.serial_number}' not found.")

        material = await self._material_repo.get_by_id(serial.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {serial.material_id} not found.")

        # Domain rule in SerialNumber entity
        serial.issue(reference_id=cmd.reference_id, location_id=cmd.location_id)
        await InventoryService(self._uow.session).remove_stock(
            tenant_id=cmd.tenant_id,
            material_id=serial.material_id,
            quantity=Decimal("1"),
            unit_id=None,
            created_by=cmd.created_by,
            from_location_id=cmd.location_id,
            reference_id=cmd.reference_id,
            remarks=cmd.remarks or f"Serial ISSUED — {cmd.serial_number}",
        )

        await self._serial_repo.save(serial)
        await self._uow.commit()
        return _to_serial_result(serial)


# ── Return Serial ──────────────────────────────────────────────────────────────

class ReturnSerialHandler:
    """
    Returns a serial (transitions ISSUED → RETURNED).
    Increments Material.current_stock by 1.
    """

    def __init__(
        self,
        material_repo: MaterialRepository,
        serial_repo: SerialNumberRepository,
        tx_repo: TransactionRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._material_repo = material_repo
        self._serial_repo = serial_repo
        self._tx_repo = tx_repo
        self._uow = uow

    async def handle(self, cmd: ReturnSerialCommand) -> SerialResult:
        serial = await self._serial_repo.get_by_serial(cmd.serial_number, cmd.tenant_id)
        if not serial:
            raise ValueError(f"Serial number '{cmd.serial_number}' not found.")

        material = await self._material_repo.get_by_id(serial.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {serial.material_id} not found.")

        # Domain rule in SerialNumber entity
        serial.return_item(location_id=cmd.location_id)
        await InventoryService(self._uow.session).add_stock(
            tenant_id=cmd.tenant_id,
            material_id=serial.material_id,
            quantity=Decimal("1"),
            unit_id=None,
            created_by=cmd.created_by,
            to_location_id=cmd.location_id,
            remarks=cmd.remarks or f"Serial RETURNED — {cmd.serial_number}",
        )

        await self._serial_repo.save(serial)
        await self._uow.commit()
        return _to_serial_result(serial)


# ── Serial Query Handler ───────────────────────────────────────────────────────

class SerialQueryHandler:
    def __init__(self, serial_repo: SerialNumberRepository) -> None:
        self._serial_repo = serial_repo

    async def get_serial_details(
        self, query: GetSerialDetailsQuery
    ) -> Optional[SerialResult]:
        serial = await self._serial_repo.get_by_serial(
            query.serial_number, query.tenant_id
        )
        return _to_serial_result(serial) if serial else None

    async def get_serials_by_material(
        self, query: GetSerialsByMaterialQuery
    ) -> List[SerialResult]:
        serials = await self._serial_repo.list_by_material(
            material_id=query.material_id,
            tenant_id=query.tenant_id,
            status=query.status,
        )
        return [_to_serial_result(s) for s in serials]
