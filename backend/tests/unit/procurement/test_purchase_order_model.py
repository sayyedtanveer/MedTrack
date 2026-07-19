from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel


def test_purchase_order_supplier_relationship_is_not_eager_joined():
    assert PurchaseOrderModel.supplier.property.lazy == "select"
