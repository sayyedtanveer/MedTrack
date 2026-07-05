from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SetupStepStatus:
    key: str
    label: str
    completed: bool
    details: str | None = None


class CompanySetupStatusService:
    REQUIRED_STEP_KEYS = (
        "company",
        "numberSeries",
        "supplier",
        "customer",
        "material",
        "product",
        "bom",
        "openingStock",
    )

    @staticmethod
    def calculate_progress(step_status: dict[str, bool]) -> int:
        completed_count = sum(1 for key in CompanySetupStatusService.REQUIRED_STEP_KEYS if step_status.get(key, False))
        total_count = len(CompanySetupStatusService.REQUIRED_STEP_KEYS)
        if total_count == 0:
            return 0
        return int(round((completed_count / total_count) * 100))

    @staticmethod
    def build_status_response(step_status: dict[str, bool]) -> dict[str, Any]:
        return {
            "company": step_status.get("company", False),
            "numberSeries": step_status.get("numberSeries", False),
            "supplier": step_status.get("supplier", False),
            "customer": step_status.get("customer", False),
            "material": step_status.get("material", False),
            "product": step_status.get("product", False),
            "bom": step_status.get("bom", False),
            "openingStock": step_status.get("openingStock", False),
            "progress": CompanySetupStatusService.calculate_progress(step_status),
        }
