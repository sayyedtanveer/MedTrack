"""Quality Inspection domain entity."""
from __future__ import annotations

import uuid
import enum
from datetime import date
from typing import Optional, List, Dict, Any
from decimal import Decimal


class InspectionResult(str, enum.Enum):
    """QC inspection result."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    CONDITIONAL = "CONDITIONAL"


class InspectionDetail:
    """Individual inspection parameter with measured value and tolerance."""
    
    def __init__(
        self,
        *,
        parameter: str,
        measured_value: Optional[str] = None,
        tolerance_min: Optional[float] = None,
        tolerance_max: Optional[float] = None,
        is_passed: bool = False,
    ):
        self.parameter = parameter
        self.measured_value = measured_value
        self.tolerance_min = tolerance_min
        self.tolerance_max = tolerance_max
        self.is_passed = is_passed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "measured_value": self.measured_value,
            "tolerance_min": self.tolerance_min,
            "tolerance_max": self.tolerance_max,
            "is_passed": self.is_passed,
        }


class QualityInspection:
    """Quality Inspection domain entity for Work Order QC flow.
    
    Links to Work Order via reference_type="work_order", reference_id=work_order_id.
    Triggers WO status transitions: QC_PENDING → QC_APPROVED/REJECTED.
    Triggers FG inventory increase on approval.
    """
    
    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
        inspection_date: date,
        inspector_id: Optional[uuid.UUID] = None,
        result: InspectionResult = InspectionResult.PASSED,
        remarks: Optional[str] = None,
        details: Optional[List[InspectionDetail]] = None,
        defect_details: Optional[Dict[str, Any]] = None,
        rework_required: bool = False,
        scrap_quantity: Optional[Decimal] = None,
    ):
        self.id = id or uuid.uuid4()
        self.tenant_id = tenant_id
        self.reference_type = reference_type  # "work_order"
        self.reference_id = reference_id  # work_order_id
        self.inspection_date = inspection_date
        self.inspector_id = inspector_id
        self.result = result
        self.remarks = remarks
        self.details = details or []
        self.defect_details = defect_details or {}
        self.rework_required = rework_required
        self.scrap_quantity = scrap_quantity
    
    def approve(self, inspector_id: uuid.UUID, remarks: Optional[str] = None) -> None:
        """Mark inspection as passed.
        
        Triggers WO transition: QC_PENDING → QC_APPROVED.
        Downstream: FG receipt.
        """
        if self.result != InspectionResult.PASSED:
            self.result = InspectionResult.PASSED
        self.inspector_id = inspector_id
        if remarks:
            self.remarks = remarks
        self.rework_required = False
    
    def reject(
        self,
        inspector_id: uuid.UUID,
        reason: str,
        defect_details: Optional[Dict[str, Any]] = None,
        rework_required: bool = False,
        scrap_quantity: Optional[Decimal] = None,
    ) -> None:
        """Mark inspection as failed.
        
        Triggers WO transition: QC_PENDING → QC_REJECTED.
        Downstream: Rework or Scrap decision.
        """
        self.result = InspectionResult.FAILED
        self.inspector_id = inspector_id
        self.remarks = reason
        self.defect_details = defect_details or {}
        self.rework_required = rework_required
        self.scrap_quantity = scrap_quantity
    
    def add_detail(self, detail: InspectionDetail) -> None:
        """Add inspection parameter detail."""
        self.details.append(detail)
    
    def is_passed(self) -> bool:
        """Check if inspection passed."""
        return self.result == InspectionResult.PASSED
    
    def is_failed(self) -> bool:
        """Check if inspection failed."""
        return self.result == InspectionResult.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "reference_type": self.reference_type,
            "reference_id": str(self.reference_id),
            "inspection_date": self.inspection_date.isoformat(),
            "inspector_id": str(self.inspector_id) if self.inspector_id else None,
            "result": self.result.value,
            "remarks": self.remarks,
            "details": [d.to_dict() for d in self.details],
            "defect_details": self.defect_details,
            "rework_required": self.rework_required,
            "scrap_quantity": str(self.scrap_quantity) if self.scrap_quantity else None,
        }
