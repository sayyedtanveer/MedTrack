from __future__ import annotations

"""
Product command handlers — Template & Variant creation/update.
Follows the same handler pattern used in Phase 1 inventory handlers.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from backend.app.application.product.commands.product_commands import (
    CreateItemTemplateCommand,
    UpdateItemTemplateCommand,
    ChangeProductStatusCommand,
    CreateItemVariantCommand,
    UpdateItemVariantCommand,
)
from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.domain.product.entities.item_variant import (
    ItemVariant,
    _build_variant_key,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.application.inventory.services.item_code_service import ItemCodeService


# ── DTOs ─────────────────────────────────────────────────────────────────────

@dataclass
class ItemTemplateResult:
    id: str
    tenant_id: str
    code: str
    item_code: str
    item_type: str
    name: str
    description: Optional[str]
    category_id: Optional[str]
    base_unit_id: Optional[str]
    attributes: List[Dict[str, Any]]
    status: str  # ProductStatus string value
    code_locked: bool
    is_active: bool


@dataclass
class ItemVariantResult:
    id: str
    tenant_id: str
    template_id: str
    code: str
    name: str
    variant_key: str
    attribute_values: Dict[str, Any]
    base_unit_id: Optional[str]
    material_id: Optional[str]
    standard_cost: str
    selling_price: Optional[str]
    is_active: bool


# ── Template Handlers ─────────────────────────────────────────────────────────

class CreateItemTemplateHandler:
    def __init__(self, template_repo, uow: SQLAlchemyUnitOfWork, item_code_service: ItemCodeService | None = None) -> None:
        self._repo = template_repo
        self._uow = uow
        self._item_code_service = item_code_service

    async def handle(self, cmd: CreateItemTemplateCommand) -> ItemTemplateResult:
        if cmd.category_id is None:
            raise ValueError("Category is required for item code generation.")
        code = (
            await self._item_code_service.validate_manual_code(
                tenant_id=cmd.tenant_id,
                code=cmd.code,
                target="product",
            )
            if self._item_code_service is not None and cmd.code
            else await self._item_code_service.generate(
                tenant_id=cmd.tenant_id,
                item_type="finished",
                category_id=cmd.category_id,
                target="product",
            )
            if self._item_code_service is not None
            else (cmd.code or "").strip().upper()
        )
        # Enforce unique code per tenant
        existing = await self._repo.get_by_code(code, cmd.tenant_id)
        if existing:
            raise ValueError(f"Item template with code '{code}' already exists.")

        template = ItemTemplate(
            tenant_id=cmd.tenant_id,
            code=code,
            name=cmd.name,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            attributes=cmd.attributes,
            status=cmd.status,
        )
        await self._repo.save(template)
        await self._uow.commit()
        return _to_template_result(template)


class UpdateItemTemplateHandler:
    def __init__(self, template_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = template_repo
        self._uow = uow

    async def handle(self, cmd: UpdateItemTemplateCommand) -> ItemTemplateResult:
        template = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not template:
            raise ValueError(f"Item template '{cmd.id}' not found.")

        template.update(
            name=cmd.name,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            attributes=cmd.attributes,
            is_active=cmd.is_active,
        )
        await self._repo.save(template)
        await self._uow.commit()
        return _to_template_result(template)


# ── Variant Handlers ──────────────────────────────────────────────────────────

class CreateItemVariantHandler:
    def __init__(self, template_repo, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._template_repo = template_repo
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: CreateItemVariantCommand) -> ItemVariantResult:
        # Load template
        template = await self._template_repo.get_by_id(cmd.template_id, cmd.tenant_id)
        if not template:
            raise ValueError(f"Item template '{cmd.template_id}' not found.")

        # Build variant_key and check uniqueness
        ordered_keys = template.attribute_keys()
        # Normalise incoming attribute_values: uppercase all keys
        normalised_values: dict = {str(k).upper(): v for k, v in cmd.attribute_values.items()}
        # Validate attribute values against allowed template values
        for attr in template.attributes:
            key = str(attr["key"]).upper()
            val = normalised_values.get(key)
            allowed_values = attr.get("values", [])
            
            if not val:
                raise BusinessRuleViolationException("Missing attribute", f"Value for '{key}' is required.")
                
            if allowed_values and str(val) not in allowed_values:
                raise BusinessRuleViolationException(
                    "Invalid attribute value", 
                    f"Value '{val}' is not valid for attribute '{key}'. Allowed values: {', '.join(allowed_values)}"
                )

        variant_key = _build_variant_key(ordered_keys, normalised_values)

        existing = await self._variant_repo.get_by_variant_key(
            variant_key=variant_key,
            template_id=cmd.template_id,
            tenant_id=cmd.tenant_id,
        )
        if existing:
            raise BusinessRuleViolationException(
                "Duplicate Variant", 
                f"A variant with attribute combination '{variant_key}' already exists for this template."
            )

        variant = ItemVariant(
            tenant_id=cmd.tenant_id,
            template_id=cmd.template_id,
            template_code=template.code,
            template_name=template.name,
            attribute_keys_ordered=ordered_keys,
            attribute_values=normalised_values,
            base_unit_id=cmd.base_unit_id or template.base_unit_id,
            material_id=cmd.material_id,
            standard_cost=cmd.standard_cost,
            selling_price=cmd.selling_price,
        )
        await self._variant_repo.save(variant)
        await self._uow.commit()
        return _to_variant_result(variant)


class UpdateItemVariantHandler:
    def __init__(self, variant_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._variant_repo = variant_repo
        self._uow = uow

    async def handle(self, cmd: UpdateItemVariantCommand) -> ItemVariantResult:
        variant = await self._variant_repo.get_by_id(cmd.id, cmd.tenant_id)
        if not variant:
            raise ValueError(f"Item variant '{cmd.id}' not found.")

        if cmd.material_id is not None:
            variant.set_material_link(cmd.material_id)
        if cmd.standard_cost is not None or cmd.selling_price is not None:
            variant.update_pricing(
                standard_cost=cmd.standard_cost,
                selling_price=cmd.selling_price,
            )
        if cmd.is_active is True:
            variant.activate()
        elif cmd.is_active is False:
            variant.deactivate()

        await self._variant_repo.save(variant)
        await self._uow.commit()
        return _to_variant_result(variant)


class ChangeProductStatusHandler:
    """Handler for changing product template status with validation."""
    def __init__(self, template_repo, uow: SQLAlchemyUnitOfWork) -> None:
        self._repo = template_repo
        self._uow = uow

    async def handle(self, cmd: ChangeProductStatusCommand) -> ItemTemplateResult:
        template = await self._repo.get_by_id(cmd.id, cmd.tenant_id)
        if not template:
            raise ValueError(f"Item template '{cmd.id}' not found.")

        # Attempt transition (validates business rules)
        template.transition_to(cmd.new_status)
        
        await self._repo.save(template)
        await self._uow.commit()
        return _to_template_result(template)


# ── Helper converters ─────────────────────────────────────────────────────────

def _to_template_result(t: ItemTemplate) -> ItemTemplateResult:
    return ItemTemplateResult(
        id=str(t.id),
        tenant_id=str(t.tenant_id),
        code=t.code,
        item_code=t.item_code,
        item_type=t.item_type,
        name=t.name,
        description=t.description,
        category_id=str(t.category_id) if t.category_id else None,
        base_unit_id=str(t.base_unit_id) if t.base_unit_id else None,
        attributes=t.attributes,
        status=t.status.value,
        code_locked=t.code_locked,
        is_active=t.is_active,
    )


def _to_variant_result(v: ItemVariant) -> ItemVariantResult:
    return ItemVariantResult(
        id=str(v.id),
        tenant_id=str(v.tenant_id),
        template_id=str(v.template_id),
        code=v.code,
        name=v.name,
        variant_key=v.variant_key,
        attribute_values=v.attribute_values,
        base_unit_id=str(v.base_unit_id) if v.base_unit_id else None,
        material_id=str(v.material_id) if v.material_id else None,
        standard_cost=str(v.standard_cost),
        selling_price=str(v.selling_price) if v.selling_price is not None else None,
        is_active=v.is_active,
    )
