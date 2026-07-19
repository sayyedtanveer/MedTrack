import uuid
from typing import List

from backend.app.domain.bom.entities.workstation import Workstation
from backend.app.domain.bom.entities.operation import Operation
from backend.app.domain.bom.entities.bom_operation import BOMOperation
from backend.app.application.bom.commands.routing_commands import (
    AddWorkstationCommand,
    AddOperationCommand,
    AttachOperationToBOMCommand,
    RemoveOperationFromBOMCommand,
    UpdateWorkstationCommand,
    DeleteWorkstationCommand,
    UpdateOperationCommand,
    DeleteOperationCommand,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class RoutingHandlers:
    def __init__(self, uow: SQLAlchemyUnitOfWork, bom_repo, workstation_repo, operation_repo):
        self._uow = uow
        self._bom_repo = bom_repo
        self._workstation_repo = workstation_repo
        self._operation_repo = operation_repo

    async def handle_add_workstation(self, cmd: AddWorkstationCommand) -> uuid.UUID:
        workstation = Workstation(
            tenant_id=cmd.tenant_id,
            code=cmd.code,
            name=cmd.name,
            capacity_hours_per_day=cmd.capacity_hours_per_day,
            hourly_rate=cmd.hourly_rate
        )
        self._workstation_repo.save(workstation)
        await self._uow.commit()
        return workstation.id

    async def handle_add_operation(self, cmd: AddOperationCommand) -> uuid.UUID:
        workstation = await self._workstation_repo.get_by_id(cmd.workstation_id, cmd.tenant_id)
        if not workstation:
            raise ValueError(f"Workstation {cmd.workstation_id} not found.")

        operation = Operation(
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            workstation_id=cmd.workstation_id,
            setup_time=cmd.setup_time,
            run_time=cmd.run_time,
            description=cmd.description
        )
        self._operation_repo.save(operation)
        await self._uow.commit()
        return operation.id

    async def handle_attach_operation(self, cmd: AttachOperationToBOMCommand) -> uuid.UUID:
        bom = await self._bom_repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        if bom.is_active:
            raise ValueError("Cannot attach operation to an active BOM. Create a new BOM version to change routing.")

        operation = await self._operation_repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation {cmd.operation_id} not found.")

        # Check if sequence is unique
        if any(op.sequence == cmd.sequence for op in bom.operations):
            raise ValueError(f"An operation with sequence {cmd.sequence} already exists on this BOM.")

        bom_op = BOMOperation(
            tenant_id=cmd.tenant_id,
            bom_id=cmd.bom_id,
            operation_id=cmd.operation_id,
            sequence=cmd.sequence
        )
        bom.add_operation(bom_op)

        await self._bom_repo.save(bom)
        await self._uow.commit()

        return bom_op.id

    async def handle_remove_operation_from_bom(self, cmd: RemoveOperationFromBOMCommand) -> None:
        bom = await self._bom_repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        if bom.is_active:
            raise ValueError("Cannot remove operation from an active BOM. Create a new BOM version to change routing.")

        before = len(bom.operations)
        bom.operations = [op for op in bom.operations if op.id != cmd.bom_operation_id]
        if len(bom.operations) == before:
            raise ValueError(f"BOM operation {cmd.bom_operation_id} not found.")

        await self._bom_repo.save(bom)
        await self._uow.commit()

    async def handle_update_workstation(self, cmd: UpdateWorkstationCommand) -> Workstation:
        workstation = await self._workstation_repo.get_by_id(cmd.workstation_id, cmd.tenant_id)
        if not workstation:
            raise ValueError(f"Workstation {cmd.workstation_id} not found.")

        workstation.update(
            code=cmd.code,
            name=cmd.name,
            capacity_hours_per_day=cmd.capacity_hours_per_day,
            hourly_rate=cmd.hourly_rate,
            is_active=cmd.is_active
        )
        self._workstation_repo.save(workstation)
        await self._uow.commit()
        return workstation

    async def handle_delete_workstation(self, cmd: DeleteWorkstationCommand) -> None:
        workstation = await self._workstation_repo.get_by_id(cmd.workstation_id, cmd.tenant_id)
        if not workstation:
            raise ValueError(f"Workstation {cmd.workstation_id} not found.")

        workstation.soft_delete()
        self._workstation_repo.save(workstation)
        await self._uow.commit()

    async def handle_update_operation(self, cmd: UpdateOperationCommand) -> Operation:
        operation = await self._operation_repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation {cmd.operation_id} not found.")

        if cmd.workstation_id:
            workstation = await self._workstation_repo.get_by_id(cmd.workstation_id, cmd.tenant_id)
            if not workstation:
                raise ValueError(f"Workstation {cmd.workstation_id} not found.")

        operation.update(
            name=cmd.name,
            workstation_id=cmd.workstation_id,
            setup_time=cmd.setup_time,
            run_time=cmd.run_time,
            description=cmd.description,
            is_active=cmd.is_active
        )
        self._operation_repo.save(operation)
        await self._uow.commit()
        return operation

    async def handle_delete_operation(self, cmd: DeleteOperationCommand) -> None:
        operation = await self._operation_repo.get_by_id(cmd.operation_id, cmd.tenant_id)
        if not operation:
            raise ValueError(f"Operation {cmd.operation_id} not found.")

        operation.soft_delete()
        self._operation_repo.save(operation)
        await self._uow.commit()
