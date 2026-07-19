"""Document type value object."""

from enum import Enum


class DocumentType(str, Enum):
    """Supported document types for generation."""
    
    WORK_ORDER = "work_order"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    DELIVERY_CHALLAN = "delivery_challan"
    QC_REPORT = "qc_report"
    RECEIPT = "receipt"
    
    def __str__(self) -> str:
        return self.value
