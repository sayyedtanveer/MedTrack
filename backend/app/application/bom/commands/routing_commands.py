import uuid
from typing import Optional
from pydantic import BaseModel

class AddWorkstationCommand(BaseModel):
    tenant_id: uuid.UUID
    code: str
    name: str
    capacity_hours_per_day: float = 8.0
    hourly_rate: float = 0.0

class AddOperationCommand(BaseModel):
    tenant_id: uuid.UUID
    name: str
    workstation_id: uuid.UUID
    setup_time: float = 0.0
    run_time: float = 0.0
    description: Optional[str] = None

class AttachOperationToBOMCommand(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
    operation_id: uuid.UUID
    sequence: int

class RemoveOperationFromBOMCommand(BaseModel):
    tenant_id: uuid.UUID
    bom_id: uuid.UUID
    bom_operation_id: uuid.UUID

class UpdateWorkstationCommand(BaseModel):
    workstation_id: uuid.UUID
    tenant_id: uuid.UUID
    code: Optional[str] = None
    name: Optional[str] = None
    capacity_hours_per_day: Optional[float] = None
    hourly_rate: Optional[float] = None
    is_active: Optional[bool] = None

class DeleteWorkstationCommand(BaseModel):
    workstation_id: uuid.UUID
    tenant_id: uuid.UUID

class UpdateOperationCommand(BaseModel):
    operation_id: uuid.UUID
    tenant_id: uuid.UUID
    name: Optional[str] = None
    workstation_id: Optional[uuid.UUID] = None
    setup_time: Optional[float] = None
    run_time: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class DeleteOperationCommand(BaseModel):
    operation_id: uuid.UUID
    tenant_id: uuid.UUID
