from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from backend.app.application.inventory.commands.inventory_commands import (
    AddStockCommand, RemoveStockCommand, AdjustStockCommand,
    CreateMaterialCommand, UpdateMaterialCommand,
)
from backend.app.application.inventory.handlers.inventory_handlers import (
    AddStockHandler, AdjustStockHandler, CreateMaterialHandler,
    MaterialResult, RemoveStockHandler, UpdateMaterialHandler, _to_result,
)
from backend.app.application.inventory.queries.inventory_queries import (
    GetMaterialQuery, GetStockQuery, GetTransactionsQuery, ListMaterialsQuery,
)
from backend.app.domain.inventory.entities.inventory_transaction import InventoryTransaction
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.repositories.transaction_repository import TransactionRepository


@dataclass
class StockInfo:
    material_id: uuid.UUID
    material_code: str
    material_name: str
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    base_unit_id: Optional[uuid.UUID]
    is_low_stock: bool
    reorder_level: Optional[Decimal]


@dataclass
class SubcontractorStockDetail:
    """Stock at a specific subcontractor/vendor."""
    vendor_id: uuid.UUID
    vendor_name: str
    quantity: Decimal


@dataclass
class MaterialStockBreakdown:
    """Stock breakdown by location type for a single material."""
    warehouse_stock: Decimal
    subcontractor_stock: Decimal
    subcontractor_details: List[SubcontractorStockDetail]


@dataclass
class TransactionResult:
    id: uuid.UUID
    material_id: uuid.UUID
    transaction_type: str
    quantity: Decimal
    unit_id: Optional[uuid.UUID]
    from_location_id: Optional[uuid.UUID]
    to_location_id: Optional[uuid.UUID]
    reference_type: str
    reference_id: Optional[uuid.UUID]
    remarks: Optional[str]
    created_by: uuid.UUID
    created_at: str


@dataclass
class PaginatedMaterials:
    items: List[MaterialResult]
    total: int
    page: int
    page_size: int


class InventoryQueryHandler:
    def __init__(self, material_repo: MaterialRepository, tx_repo: TransactionRepository):
        self._material_repo = material_repo
        self._tx_repo = tx_repo

    async def _compute_stock_by_location_bulk(
        self,
        material_ids: List[uuid.UUID],
        tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, MaterialStockBreakdown]:
        """
        Compute warehouse and subcontractor stock for multiple materials in one bulk query.
        Resolves vendor names from subcontract orders.
        
        Returns:
            {
                material_id_1: MaterialStockBreakdown(...),
                material_id_2: MaterialStockBreakdown(...),
            }
        """
        if not material_ids:
            return {}
        
        from backend.app.infrastructure.persistence.models.stock_level_model import StockLevelModel
        from backend.app.infrastructure.persistence.models.location_model import LocationModel
        from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
        from backend.app.infrastructure.persistence.models.subcontract_model import (
            SubcontractOrderModel,
            SubcontractMaterialIssueModel,
        )
        from sqlalchemy import select, and_, func
        from collections import defaultdict
        
        session = self._material_repo._session
        
        # Step 1: Get stock levels with locations for all materials
        stmt = (
            select(
                StockLevelModel.material_id,
                LocationModel.id.label('location_id'),
                LocationModel.type.label('location_type'),
                LocationModel.name.label('location_name'),
                StockLevelModel.quantity,
            )
            .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
            .where(
                StockLevelModel.tenant_id == tenant_id,
                StockLevelModel.material_id.in_(material_ids),
                StockLevelModel.is_deleted == False,
                StockLevelModel.quantity > 0,
                LocationModel.is_deleted == False,
                StockLevelModel.stock_status == 'available',  # Only available stock
            )
        )
        result = await session.execute(stmt)
        stock_rows = result.all()
        
        # Step 2: Get all suppliers/vendors upfront for vendor name resolution
        supplier_stmt = select(SupplierModel).where(
            SupplierModel.tenant_id == tenant_id,
            SupplierModel.is_deleted == False,
        )
        supplier_result = await session.execute(supplier_stmt)
        suppliers = {s.id: s for s in supplier_result.scalars().all()}
        
        # Step 3: Get active subcontract orders that have issued materials
        # We need to map: material_id -> supplier_id for materials at subcontractor locations
        orders_stmt = (
            select(SubcontractOrderModel)
            .where(
                SubcontractOrderModel.tenant_id == tenant_id,
                SubcontractOrderModel.is_deleted == False,
                SubcontractOrderModel.status.in_(['materials_issued', 'partially_received']),
            )
        )
        orders_result = await session.execute(orders_stmt)
        orders = {o.id: o for o in orders_result.scalars().all()}
        
        # Step 4: Get material issues to map material -> subcontract order -> supplier
        if orders:
            issues_stmt = select(SubcontractMaterialIssueModel).where(
                SubcontractMaterialIssueModel.tenant_id == tenant_id,
                SubcontractMaterialIssueModel.subcontract_order_id.in_(orders.keys()),
                SubcontractMaterialIssueModel.material_id.in_(material_ids),
            )
            issues_result = await session.execute(issues_stmt)
            issues = issues_result.scalars().all()
            
            # Build map: material_id -> supplier_id
            material_to_supplier = {}
            for issue in issues:
                order = orders.get(issue.subcontract_order_id)
                if order and issue.material_id not in material_to_supplier:
                    material_to_supplier[issue.material_id] = order.supplier_id
        else:
            material_to_supplier = {}
        
        # Step 5: Aggregate stock by material and location type
        breakdown_map = {}
        
        # Group by material_id
        material_stocks = defaultdict(lambda: {
            'warehouse': Decimal("0"),
            'subcontractor': Decimal("0"),
            'subcontractor_by_vendor': defaultdict(Decimal),
        })
        
        for row in stock_rows:
            mat_id = row.material_id
            loc_type = row.location_type
            qty = Decimal(str(row.quantity))
            
            if loc_type in ['warehouse', 'zone', 'rack', 'bin', 'production']:
                material_stocks[mat_id]['warehouse'] += qty
            elif loc_type == 'subcontractor':
                material_stocks[mat_id]['subcontractor'] += qty
                
                # Resolve vendor for this material
                supplier_id = material_to_supplier.get(mat_id)
                if supplier_id:
                    material_stocks[mat_id]['subcontractor_by_vendor'][supplier_id] += qty
        
        # Step 6: Build final breakdown objects
        for mat_id, stocks in material_stocks.items():
            subcontractor_details = []
            for vendor_id, qty in stocks['subcontractor_by_vendor'].items():
                vendor = suppliers.get(vendor_id)
                if vendor:
                    subcontractor_details.append(
                        SubcontractorStockDetail(
                            vendor_id=vendor_id,
                            vendor_name=vendor.name,
                            quantity=qty,
                        )
                    )
            
            breakdown_map[mat_id] = MaterialStockBreakdown(
                warehouse_stock=stocks['warehouse'],
                subcontractor_stock=stocks['subcontractor'],
                subcontractor_details=subcontractor_details,
            )
        
        # Ensure all requested materials have an entry (even if zero stock)
        for mat_id in material_ids:
            if mat_id not in breakdown_map:
                breakdown_map[mat_id] = MaterialStockBreakdown(
                    warehouse_stock=Decimal("0"),
                    subcontractor_stock=Decimal("0"),
                    subcontractor_details=[],
                )
        
        return breakdown_map

    async def list_materials(self, query: ListMaterialsQuery) -> PaginatedMaterials:
        # Step 1: Get materials
        items = await self._material_repo.search(
            tenant_id=query.tenant_id,
            query=query.query,
            category=query.category,
            material_type=query.material_type,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        total = await self._material_repo.count(
            tenant_id=query.tenant_id,
            query=query.query,
            category=query.category,
            material_type=query.material_type,
            is_active=query.is_active,
        )
        
        # Step 2: Bulk fetch stock breakdown with vendor details
        material_ids = [m.id for m in items]
        stock_breakdown = await self._compute_stock_by_location_bulk(material_ids, query.tenant_id)
        
        # Step 3: Merge breakdown into results
        results = []
        for m in items:
            result = _to_result(m)
            breakdown = stock_breakdown.get(m.id)
            if breakdown:
                result.warehouse_stock = breakdown.warehouse_stock
                result.subcontractor_stock = breakdown.subcontractor_stock
                result.subcontractor_details = [
                    {
                        'vendor_id': detail.vendor_id,
                        'vendor_name': detail.vendor_name,
                        'quantity': detail.quantity,
                    }
                    for detail in breakdown.subcontractor_details
                ]
            results.append(result)
        
        return PaginatedMaterials(
            items=results,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_material(self, query: GetMaterialQuery) -> Optional[MaterialResult]:
        material = await self._material_repo.get_by_id(query.id, query.tenant_id)
        if not material:
            return None
            
        from backend.app.application.procurement.services.purchase_history_query_service import PurchaseHistoryQueryService
        
        session = self._material_repo._session
        purchase_history_svc = PurchaseHistoryQueryService(session)
        summary = await purchase_history_svc.get_purchasing_summary(query.id, query.tenant_id)
        
        result = _to_result(material)
        result.latest_purchase_price = summary.get("latest_purchase_price")
        result.last_purchase_date = summary.get("last_purchase_date")
        result.last_supplier_name = summary.get("last_supplier_name")
        result.last_supplier_id = summary.get("last_supplier_id")
        result.purchase_count = summary.get("purchase_count", 0)
        return result

    async def get_stock(self, query: GetStockQuery) -> Optional[StockInfo]:
        material = await self._material_repo.get_by_id(query.material_id, query.tenant_id)
        if not material:
            return None
        return StockInfo(
            material_id=material.id,
            material_code=material.code,
            material_name=material.name,
            current_stock=material.current_stock,
            reserved_stock=material.reserved_stock,
            available_stock=material.get_available_stock(),
            base_unit_id=material.base_unit_id,
            is_low_stock=material.is_low_stock(),
            reorder_level=material.reorder_level,
        )

    async def get_transactions(self, query: GetTransactionsQuery) -> List[TransactionResult]:
        if query.material_id:
            txs = await self._tx_repo.list_by_material(
                material_id=query.material_id,
                tenant_id=query.tenant_id,
                page=query.page,
                page_size=query.page_size,
            )
        else:
            txs = await self._tx_repo.list_all(
                tenant_id=query.tenant_id,
                page=query.page,
                page_size=query.page_size,
            )
        return [
            TransactionResult(
                id=tx.id,
                material_id=tx.material_id,
                transaction_type=tx.transaction_type.value,
                quantity=tx.quantity,
                unit_id=tx.unit_id,
                from_location_id=tx.from_location_id,
                to_location_id=tx.to_location_id,
                reference_type=tx.reference_type.value,
                reference_id=tx.reference_id,
                remarks=tx.remarks,
                created_by=tx.created_by,
                created_at=tx.created_at.isoformat(),
            )
            for tx in txs
        ]
