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
        "units",
        "categories",
        "locations",
        "operations",
        "supplier",
        "customer",
        "material",
        "product",
        "bom",
        "openingStock",
        "readyToStart",    # computed — excluded from mandatory count
    )

    # "users" is tracked but optional — not in REQUIRED_STEP_KEYS

    @staticmethod
    def calculate_progress(step_status: dict[str, bool]) -> int:
        mandatory_keys = [k for k in CompanySetupStatusService.REQUIRED_STEP_KEYS if k != "readyToStart"]
        completed_count = sum(1 for k in mandatory_keys if step_status.get(k, False))
        total_count = len(mandatory_keys)
        if total_count == 0:
            return 0
        return int(round((completed_count / total_count) * 100))

    @staticmethod
    def build_status_response(step_status: dict[str, bool]) -> dict[str, Any]:
        mandatory_keys = [k for k in CompanySetupStatusService.REQUIRED_STEP_KEYS if k != "readyToStart"]
        mandatory_complete = sum(1 for k in mandatory_keys if step_status.get(k, False))
        ready_to_start = mandatory_complete == len(mandatory_keys)
        return {
            **{k: step_status.get(k, False) for k in CompanySetupStatusService.REQUIRED_STEP_KEYS if k != "readyToStart"},
            "users": step_status.get("users", False),
            "readyToStart": ready_to_start,
            "progress": int(round(mandatory_complete / len(mandatory_keys) * 100)),
        }
