from types import SimpleNamespace

import pytest

from backend.app.application.procurement.handlers.purchase_order_handler import _normalize_po_status
from backend.app.domain.procurement.entities.purchase_order import PurchaseOrderStatus
from backend.app.interfaces.api.v1.routes.supply_chain import _po_to_dict


def test_normalize_po_status_accepts_legacy_values():
    assert _normalize_po_status("SENT") == PurchaseOrderStatus.SENT
    assert _normalize_po_status("completed") == PurchaseOrderStatus.COMPLETED
    assert _normalize_po_status("canceled") == PurchaseOrderStatus.CANCELLED


def test_normalize_po_status_rejects_unknown_values():
    with pytest.raises(ValueError):
        _normalize_po_status("mystery-status")


def test_po_to_dict_handles_missing_dates_and_amounts():
    po = SimpleNamespace(
        id="po-1",
        po_number="PO-001",
        supplier_id="supplier-1",
        status="COMPLETED",
        order_date=None,
        expected_delivery=None,
        total_amount=None,
        notes=None,
        lines=[
            SimpleNamespace(
                id="line-1",
                material_id="material-1",
                quantity=None,
                received_quantity=None,
                unit_price=None,
                line_total=None,
                is_deleted=False,
            )
        ],
    )

    payload = _po_to_dict(po)

    assert payload["status"] == "received"
    assert payload["order_date"] is None
    assert payload["expected_delivery"] is None
    assert payload["total_amount"] == 0.0
    assert payload["lines"][0]["quantity"] == 0.0
