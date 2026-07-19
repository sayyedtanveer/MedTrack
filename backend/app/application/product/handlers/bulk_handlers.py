from __future__ import annotations

"""
Bulk variant operations handlers.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import uuid

from backend.app.application.product.commands.bulk_commands import (
    BulkCreateVariantsCommand,
    BulkUpdateVariantsCommand,
    BulkActivateVariantsCommand,
    BulkDeactivateVariantsCommand,
)
from backend.app.domain.product.entities.item_variant import ItemVariant
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class BulkImportError:
    """Represents a single error during bulk import."""
    row_number: int
    field: str
    message: str
    data: dict = None


@dataclass
class BulkImportResult:
    """Result of a bulk import operation."""
    success_count: int
    error_count: int
    errors: List[BulkImportError]
    variant_ids: List[str]  # IDs of successfully created variants


# ── Handlers ──────────────────────────────────────────────────────────────────

class BulkCreateVariantsHandler:
    """Handler for creating multiple variants at once."""

    def __init__(self, template_repo, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._template_repo = template_repo
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: BulkCreateVariantsCommand) -> BulkImportResult:
        """
        Bulk create variants with comprehensive error handling.
        Returns result with success count, error count, and detailed error list.
        """
        errors: List[BulkImportError] = []
        successful_variants: List[str] = []

        # Load template
        template = await self._template_repo.get_by_id(cmd.template_id, cmd.tenant_id)
        if not template:
            raise ValueError(f"Template {cmd.template_id} not found.")

        ordered_keys = template.attribute_keys()

        # Process each variant
        for row_num, variant_data in enumerate(cmd.variants_data, start=1):
            try:
                # Extract data
                attribute_values = variant_data.get("attribute_values", {})
                standard_cost = variant_data.get("standard_cost", "0")
                selling_price = variant_data.get("selling_price")

                # Normalize attribute keys
                normalised_values = {str(k).upper(): v for k, v in attribute_values.items()}

                # Validate all required attributes present
                for attr in template.attributes:
                    key = str(attr["key"]).upper()
                    val = normalised_values.get(key)
                    allowed_values = attr.get("values", [])

                    if not val:
                        raise BusinessRuleViolationException(
                            "Missing attribute",
                            f"Value for '{key}' is required."
                        )

                    if allowed_values and str(val) not in allowed_values:
                        raise BusinessRuleViolationException(
                            "Invalid attribute value",
                            f"Value '{val}' not valid for '{key}'. Allowed: {', '.join(allowed_values)}"
                        )

                # Check for duplicate variant
                from backend.app.domain.product.entities.item_variant import _build_variant_key
                variant_key = _build_variant_key(ordered_keys, normalised_values)

                existing = await self._variant_repo.get_by_variant_key(
                    variant_key=variant_key,
                    template_id=cmd.template_id,
                    tenant_id=cmd.tenant_id,
                )
                if existing:
                    raise BusinessRuleViolationException(
                        "Duplicate variant",
                        f"Variant with combination '{variant_key}' already exists."
                    )

                # Create and save variant
                from decimal import Decimal
                variant = ItemVariant(
                    tenant_id=cmd.tenant_id,
                    template_id=cmd.template_id,
                    template_code=template.code,
                    template_name=template.name,
                    attribute_keys_ordered=ordered_keys,
                    attribute_values=normalised_values,
                    base_unit_id=template.base_unit_id,
                    standard_cost=Decimal(str(standard_cost)),
                    selling_price=Decimal(str(selling_price)) if selling_price else None,
                )
                await self._variant_repo.save(variant)
                successful_variants.append(str(variant.id))

            except (ValueError, BusinessRuleViolationException) as e:
                errors.append(BulkImportError(
                    row_number=row_num,
                    field="variant",
                    message=str(e),
                    data=variant_data
                ))

        # Commit all successful variants together
        if successful_variants:
            await self._uow.commit()

        return BulkImportResult(
            success_count=len(successful_variants),
            error_count=len(errors),
            errors=errors,
            variant_ids=successful_variants,
        )


class BulkUpdateVariantsHandler:
    """Handler for bulk updating variant pricing and status."""

    def __init__(self, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: BulkUpdateVariantsCommand) -> BulkImportResult:
        """Bulk update variants with error handling."""
        errors: List[BulkImportError] = []
        updated_count = 0

        from decimal import Decimal

        for row_num, variant_data in enumerate(cmd.variants_data, start=1):
            try:
                variant_id = variant_data.get("id")
                if not variant_id:
                    raise ValueError("id is required for update.")

                variant = await self._variant_repo.get_by_id(uuid.UUID(variant_id), cmd.tenant_id)
                if not variant:
                    raise ValueError(f"Variant {variant_id} not found.")

                # Update pricing if provided
                if "standard_cost" in variant_data or "selling_price" in variant_data:
                    cost = variant_data.get("standard_cost")
                    price = variant_data.get("selling_price")
                    variant.update_pricing(
                        standard_cost=Decimal(str(cost)) if cost is not None else None,
                        selling_price=Decimal(str(price)) if price is not None else None,
                    )

                # Update status if provided
                if "is_active" in variant_data:
                    is_active = variant_data.get("is_active")
                    if is_active:
                        variant.activate()
                    else:
                        variant.deactivate()

                await self._variant_repo.save(variant)
                updated_count += 1

            except (ValueError, Exception) as e:
                errors.append(BulkImportError(
                    row_number=row_num,
                    field="variant",
                    message=str(e),
                    data=variant_data
                ))

        if updated_count > 0:
            await self._uow.commit()

        return BulkImportResult(
            success_count=updated_count,
            error_count=len(errors),
            errors=errors,
            variant_ids=[],
        )


class BulkActivateVariantsHandler:
    """Activate multiple variants."""

    def __init__(self, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: BulkActivateVariantsCommand) -> int:
        """Activate variants and return count."""
        count = 0
        for variant_id in cmd.variant_ids:
            variant = await self._variant_repo.get_by_id(variant_id, cmd.tenant_id)
            if variant:
                variant.activate()
                await self._variant_repo.save(variant)
                count += 1
        await self._uow.commit()
        return count


class BulkDeactivateVariantsHandler:
    """Deactivate multiple variants."""

    def __init__(self, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: BulkDeactivateVariantsCommand) -> int:
        """Deactivate variants and return count."""
        count = 0
        for variant_id in cmd.variant_ids:
            variant = await self._variant_repo.get_by_id(variant_id, cmd.tenant_id)
            if variant:
                variant.deactivate()
                await self._variant_repo.save(variant)
                count += 1
        await self._uow.commit()
        return count
