"""Small onboarding policies; quotes stay independent from effective costs."""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
from uuid import UUID

from backend.app.application.procurement.pricing.direct_standard_cost import normalize_standard_cost


def parse_import_decimal(value: object, *, maximum: str = "999999999.99") -> Decimal:
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError("Must be a valid number") from exc
    if not result.is_finite() or result < 0 or result > Decimal(maximum):
        raise ValueError(f"Must be a finite number between 0 and {maximum}")
    return result


def import_date(value: object) -> str:
    """Normalize actual Excel date cells and ISO date/timestamp text."""
    if value is None or str(value).strip() == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text  # The row validator reports malformed dates.


def agreement_dates(data: Mapping[str, Any], today: date) -> tuple[datetime, datetime | None]:
    start = date.fromisoformat(import_date(data.get("effective_from_date")) or today.isoformat())
    end_text = import_date(data.get("effective_to_date"))
    end = date.fromisoformat(end_text) if end_text else None
    if end is not None and end < start:
        raise ValueError("Effective To must be on or after Effective From")
    return (
        datetime.combine(start, time.min, timezone.utc),
        datetime.combine(end, time(23, 59, 59), timezone.utc) if end else None,
    )


@dataclass(frozen=True)
class InitialCostPlan:
    cost: Decimal | None
    message: str


def plan_initial_cost(
    rows: Sequence[Mapping[str, Any]],
    *,
    base_uom_id: UUID | None,
    uom_ids: Mapping[str, UUID],
    currency_code: str | None,
    can_set_cost: bool,
    today: date | None = None,
) -> InitialCostPlan:
    """Evaluate every row before initializing a genuinely new material."""
    if not can_set_cost:
        return InitialCostPlan(None, "Standard cost not initialized: cost-setting permission is required.")
    if any(row.get("status") == "error" for row in rows):
        return InitialCostPlan(None, "Standard cost not initialized: another row for this material is invalid.")
    if not currency_code:
        return InitialCostPlan(None, "Standard cost not initialized: tenant costing currency is not configured.")
    data_rows = [row["data"] for row in rows]
    base_ids = {uom_ids.get(str(data.get("uom", "")).strip().upper()) for data in data_rows}
    if base_uom_id is None or base_ids != {base_uom_id}:
        return InitialCostPlan(None, "Standard cost not initialized: conflicting or missing base UOM.")
    explicit = {
        parse_import_decimal(data["proposed_initial_cost"])
        for data in data_rows if str(data.get("proposed_initial_cost", "")).strip()
    }
    if len(explicit) > 1:
        return InitialCostPlan(None, "Standard cost not initialized: conflicting explicit initial costs.")
    if explicit:
        return InitialCostPlan(normalize_standard_cost(explicit.pop()), "Explicit initial standard cost configured.")
    rates: set[Decimal] = set()
    today = today or datetime.now(timezone.utc).date()
    for data in data_rows:
        if not str(data.get("supplier_price", "")).strip():
            continue
        start, end = agreement_dates(data, today)
        if start.date() > today or (end is not None and end.date() < today):
            return InitialCostPlan(None, "Standard cost not initialized: supplier rate is not currently effective.")
        if not currency_code or str(data.get("supplier_currency", "")).upper() != currency_code.upper():
            return InitialCostPlan(None, "Standard cost not initialized: supplier currency differs from costing currency.")
        supplier_uom = uom_ids.get(str(data.get("supplier_uom", "")).strip().upper())
        if supplier_uom != base_uom_id:
            return InitialCostPlan(None, "Standard cost not initialized: supplier UOM differs from base UOM.")
        rates.add(parse_import_decimal(data["supplier_price"]))
    if len(rates) != 1:
        return InitialCostPlan(None, "Standard cost not initialized: conflicting supplier rates or no eligible supplier price.")
    return InitialCostPlan(normalize_standard_cost(rates.pop()), "Initial standard cost configured from the compatible supplier rate.")
