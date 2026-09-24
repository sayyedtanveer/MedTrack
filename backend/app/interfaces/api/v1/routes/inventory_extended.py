from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from decimal import Decimal

from backend.app.infrastructure.persistence.models.inventory_management_models import (
    StockReservationModel,
    WarehouseZoneModel,
    StockLedgerModel,
)
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.application.inventory.handlers.storekeeper_handler import StorekeeperHandler
from backend.app.application.inventory.commands.storekeeper_commands import (
    IssueMaterialCommand,
    PartialIssueCommand,
    RejectIssueCommand,
    ReturnMaterialCommand,
)
from backend.app.application.inventory.services.inventory_traceability_service import InventoryTraceabilityService
from backend.app.application.manufacturing.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Extended"])

# ── Schemas ─────────────────────────────────────────────────────────────

class WarehouseZoneCreate(BaseModel):
    warehouse_location_id: uuid.UUID
    zone_name: str
    zone_type: str
    capacity: Optional[float] = None

class WarehouseZoneResponse(WarehouseZoneCreate):
    id: uuid.UUID
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class StockReservationCreate(BaseModel):
    material_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

class StockReservationResponse(StockReservationCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StockLedgerResponse(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    location_id: Optional[uuid.UUID]
    transaction_date: datetime
    transaction_type: str
    quantity_change: float
    running_balance: float
    reference_type: Optional[str]
    reference_id: Optional[uuid.UUID]
    model_config = ConfigDict(from_attributes=True)

class RealtimeStockResponse(BaseModel):
    material_id: uuid.UUID
    material_code: str
    material_name: str
    current_stock: float
    reserved_stock: float
    available_stock: float
    model_config = ConfigDict(from_attributes=True)

# ── Warehouse Zones ─────────────────────────────────────────────────────────

@router.post("/zones", response_model=WarehouseZoneResponse, dependencies=[Depends(require_permission("inventory:write"))])
async def create_warehouse_zone(
    body: WarehouseZoneCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        # verify the location is a warehouse
        loc = await session.get(LocationModel, body.warehouse_location_id)
        if not loc or loc.tenant_id != tenant_id or loc.type != "warehouse":
            raise HTTPException(status_code=400, detail="Invalid warehouse location")

        zone = WarehouseZoneModel(
            tenant_id=tenant_id,
            warehouse_location_id=body.warehouse_location_id,
            zone_name=body.zone_name,
            zone_type=body.zone_type,
            capacity=body.capacity
        )
        session.add(zone)
        await session.commit()
        await session.refresh(zone)
        return WarehouseZoneResponse.model_validate(zone)

@router.get("/zones", response_model=List[WarehouseZoneResponse])
async def list_warehouse_zones(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    warehouse_id: Optional[uuid.UUID] = Query(None)
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WarehouseZoneModel).where(WarehouseZoneModel.tenant_id == tenant_id)
        if warehouse_id:
            stmt = stmt.where(WarehouseZoneModel.warehouse_location_id == warehouse_id)
        
        result = await session.execute(stmt)
        zones = result.scalars().all()
        return [WarehouseZoneResponse.model_validate(z) for z in zones]

# ── Reservations ────────────────────────────────────────────────────────────

@router.post("/reservations", response_model=StockReservationResponse, dependencies=[Depends(require_permission("inventory:write"))])
async def reserve_stock(
    body: StockReservationCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    created_by: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        try:
            await InventoryService(session).reserve_reference_stock(
                tenant_id=tenant_id,
                material_id=body.material_id,
                quantity=Decimal(str(body.quantity)),
                unit_id=None,
                created_by=created_by,
                reference_type=body.reference_type,
                reference_id=body.reference_id,
                remarks=body.notes,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        
        res = StockReservationModel(
            tenant_id=tenant_id,
            material_id=body.material_id,
            location_id=body.location_id,
            quantity=body.quantity,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
            notes=body.notes,
            status="ACTIVE"
        )
        session.add(res)
        await session.commit()
        await session.refresh(res)
        return StockReservationResponse.model_validate(res)

@router.post("/reservations/{reservation_id}/consume", dependencies=[Depends(require_permission("inventory:write"))])
async def consume_reservation(
    reservation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    created_by: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        res = (
            await session.execute(
                select(StockReservationModel)
                .where(
                    StockReservationModel.id == reservation_id,
                    StockReservationModel.tenant_id == tenant_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not res:
            raise HTTPException(404, "Reservation not found")
        if res.status != "ACTIVE":
            raise HTTPException(400, f"Reservation is {res.status}")
        
        try:
            await InventoryService(session).consume_reference_reservation(
                tenant_id=tenant_id,
                material_id=res.material_id,
                quantity=Decimal(str(res.quantity)),
                unit_id=None,
                created_by=created_by,
                from_location_id=res.location_id,
                reference_type=res.reference_type,
                reference_id=res.reference_id,
                remarks=res.notes,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        res.status = "CONSUMED"
        await session.commit()
        return {"status": "success"}

@router.post("/reservations/{reservation_id}/cancel", dependencies=[Depends(require_permission("inventory:write"))])
async def cancel_reservation(
    reservation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    created_by: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        res = (
            await session.execute(
                select(StockReservationModel)
                .where(
                    StockReservationModel.id == reservation_id,
                    StockReservationModel.tenant_id == tenant_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not res:
            raise HTTPException(404, "Reservation not found")
        if res.status != "ACTIVE":
            raise HTTPException(400, f"Reservation is {res.status}")

        await InventoryService(session).cancel_reference_reservation(
            tenant_id=tenant_id,
            material_id=res.material_id,
            quantity=Decimal(str(res.quantity)),
            unit_id=None,
            created_by=created_by,
            reference_type=res.reference_type,
            reference_id=res.reference_id,
            remarks=res.notes,
        )
        res.status = "CANCELLED"
        
        await session.commit()
        return {"status": "success"}


# ── Ledger and Realtime ─────────────────────────────────────────────────────

@router.get("/ledger", response_model=List[StockLedgerResponse])
async def get_stock_ledger(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    material_id: Optional[uuid.UUID] = Query(None),
    limit: int = 100
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(StockLedgerModel).where(StockLedgerModel.tenant_id == tenant_id)
        if material_id:
            stmt = stmt.where(StockLedgerModel.material_id == material_id)
        stmt = stmt.order_by(StockLedgerModel.transaction_date.desc()).limit(limit)
        
        res = await session.execute(stmt)
        entries = res.scalars().all()
        return [StockLedgerResponse.model_validate(e) for e in entries]

@router.get("/realtime", response_model=List[RealtimeStockResponse])
async def get_realtime_stock(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(MaterialModel).where(MaterialModel.tenant_id == tenant_id, MaterialModel.is_active == True)
        res = await session.execute(stmt)
        materials = res.scalars().all()
        
        results = []
        for m in materials:
            results.append(RealtimeStockResponse(
                material_id=m.id,
                material_code=m.code,
                material_name=m.name,
                current_stock=float(m.current_stock),
                reserved_stock=float(m.reserved_stock),
                available_stock=float(m.current_stock - m.reserved_stock)
            ))
        return results


# ── Phase 3: Storekeeper Operational Flow (deprecated — prefer /api/v1/storekeeper/*) ──

@router.post("/scan/resolve")
async def resolve_scan(
    body: dict,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Resolve barcode/QR payload to material, batch, or work order."""
    from backend.app.application.inventory.services.barcode_resolution_service import (
        BarcodeResolutionService,
    )

    container = get_container(request)
    async with container.session_factory() as session:
        service = BarcodeResolutionService(session)
        return await service.resolve(tenant_id=tenant_id, payload=body.get("payload", ""))


@router.get("/storekeeper/issue-queue", deprecated=True)
async def get_issue_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get pending material issue queue for storekeeper dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        queue = await service.get_issue_queue(tenant_id=tenant_id)
        return queue


@router.get("/storekeeper/shortage-queue")
async def get_shortage_queue(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get shortage queue for storekeeper dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        queue = await service.get_shortage_queue(tenant_id=tenant_id)
        return queue


@router.get("/storekeeper/partially-issued")
async def get_partially_issued_wo(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get partially issued WOs for storekeeper dashboard."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        queue = await service.get_partially_issued_wo(tenant_id=tenant_id)
        return queue


@router.get("/storekeeper/pending-reservations", deprecated=True)
async def get_pending_reservations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Deprecated wrapper for canonical /storekeeper/pending-reservations."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        return await service.get_pending_reservations(tenant_id=tenant_id)


@router.get("/storekeeper/pending-returns", deprecated=True)
async def get_pending_returns(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Deprecated wrapper for canonical /storekeeper/pending-returns."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        return await service.get_pending_returns(tenant_id=tenant_id)


@router.get("/storekeeper/inventory-alerts", deprecated=True)
async def get_inventory_alerts(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Deprecated wrapper for canonical /storekeeper/inventory-alerts."""
    container = get_container(request)
    async with container.session_factory() as session:
        from backend.app.application.inventory.services.storekeeper_service import StorekeeperService
        service = StorekeeperService(session)
        return await service.get_inventory_alerts(tenant_id=tenant_id)


@router.post("/storekeeper/issue")
async def issue_material(
    body: IssueMaterialCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Issue material to work order."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = StorekeeperHandler(session)
        command = body.model_copy(update={"tenant_id": tenant_id, "issued_by": user_id})
        await handler.handle_issue_material(command)
        await session.commit()
        return {"status": "success"}


@router.post("/storekeeper/partial-issue")
async def partial_issue_material(
    body: PartialIssueCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Partially issue material to work order."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = StorekeeperHandler(session)
        command = body.model_copy(update={"tenant_id": tenant_id, "issued_by": user_id})
        await handler.handle_partial_issue(command)
        await session.commit()
        return {"status": "success"}


@router.post("/storekeeper/reject")
async def reject_issue(
    body: RejectIssueCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Reject material issue request."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = StorekeeperHandler(session)
        command = body.model_copy(update={"tenant_id": tenant_id, "rejected_by": user_id})
        await handler.handle_reject_issue(command)
        await session.commit()
        return {"status": "success"}


@router.post("/storekeeper/return")
async def return_material(
    body: ReturnMaterialCommand,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Return issued material back to inventory."""
    container = get_container(request)
    async with container.session_factory() as session:
        handler = StorekeeperHandler(session)
        command = body.model_copy(update={"tenant_id": tenant_id, "returned_by": user_id})
        await handler.handle_return_material(command)
        await session.commit()
        return {"status": "success"}


# ── Phase 10: Inventory Traceability ───────────────────────────────────────

@router.get("/traceability/material/{material_id}")
async def get_material_traceability(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get full traceability history for a material."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTraceabilityService(session)
        traceability = await service.get_material_traceability(
            tenant_id=tenant_id,
            material_id=material_id,
        )
        return {"items": traceability}

@router.get("/traceability/work-order/{work_order_id}")
async def get_work_order_traceability(
    work_order_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get traceability for a specific Work Order."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTraceabilityService(session)
        traceability = await service.get_work_order_traceability(
            tenant_id=tenant_id,
            work_order_id=work_order_id,
        )
        return {"items": traceability}


@router.get("/traceability/ledger")
async def get_stock_ledger(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    material_id: Optional[uuid.UUID] = Query(None),
    location_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=200),
):
    """Get stock ledger entries."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTraceabilityService(session)
        ledger = await service.get_stock_ledger(
            tenant_id=tenant_id,
            material_id=material_id,
            location_id=location_id,
            limit=limit,
        )
        return {"items": ledger}


@router.get("/traceability/transaction/{transaction_id}")
async def get_transaction_audit_trail(
    transaction_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get full audit trail for a specific transaction."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTraceabilityService(session)
        audit_trail = await service.get_transaction_audit_trail(
            tenant_id=tenant_id,
            transaction_id=transaction_id,
        )
        if not audit_trail:
            return JSONResponse(status_code=404, content={"error": "Transaction not found"})
        return audit_trail


@router.get("/traceability/lifecycle/{material_id}")
async def trace_material_lifecycle(
    material_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Trace material lifecycle from receipt to consumption."""
    container = get_container(request)
    async with container.session_factory() as session:
        service = InventoryTraceabilityService(session)
        lifecycle = await service.trace_material_lifecycle(
            tenant_id=tenant_id,
            material_id=material_id,
        )
        return lifecycle
