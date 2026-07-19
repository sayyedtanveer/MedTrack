from __future__ import annotations

"""
Product query handler — read operations for templates and variants.
"""

from dataclasses import dataclass
from typing import List, Optional

from backend.app.application.product.handlers.product_handlers import (
    ItemTemplateResult,
    ItemVariantResult,
    _to_template_result,
    _to_variant_result,
)
from backend.app.application.product.queries.product_queries import (
    GetItemTemplateQuery,
    ListItemTemplatesQuery,
    GetItemVariantQuery,
    ListItemVariantsQuery,
    ListAllVariantsQuery,
)


@dataclass
class TemplateListResult:
    items: List[ItemTemplateResult]
    total: int
    page: int
    page_size: int


@dataclass
class VariantListResult:
    items: List[ItemVariantResult]
    total: int
    page: int
    page_size: int


class ProductQueryHandler:
    def __init__(self, template_repo, variant_repo) -> None:
        self._template_repo = template_repo
        self._variant_repo = variant_repo

    async def get_template(self, query: GetItemTemplateQuery) -> Optional[ItemTemplateResult]:
        template = await self._template_repo.get_by_id(query.id, query.tenant_id)
        return _to_template_result(template) if template else None

    async def list_templates(self, query: ListItemTemplatesQuery) -> TemplateListResult:
        items, total = await self._template_repo.list_templates(
            tenant_id=query.tenant_id,
            category_id=query.category_id,
            search=query.query,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        return TemplateListResult(
            items=[_to_template_result(t) for t in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_variant(self, query: GetItemVariantQuery) -> Optional[ItemVariantResult]:
        variant = await self._variant_repo.get_by_id(query.id, query.tenant_id)
        return _to_variant_result(variant) if variant else None

    async def list_variants(self, query: ListItemVariantsQuery) -> VariantListResult:
        items, total = await self._variant_repo.list_variants(
            template_id=query.template_id,
            tenant_id=query.tenant_id,
            search=query.query,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        return VariantListResult(
            items=[_to_variant_result(v) for v in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def list_all_variants(self, query: ListAllVariantsQuery) -> VariantListResult:
        items, total = await self._variant_repo.list_all_variants(
            tenant_id=query.tenant_id,
            search=query.query,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        return VariantListResult(
            items=[_to_variant_result(v) for v in items],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
