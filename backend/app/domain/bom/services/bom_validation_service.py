import uuid
from typing import Optional, Protocol

from backend.app.domain.bom.entities.bom import BillOfMaterial


class BOMProvider(Protocol):
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        ...


class BOMValidationService:
    def __init__(self, bom_provider: BOMProvider):
        self._bom_provider = bom_provider

    async def validate_no_circular_dependencies(
        self, tenant_id: uuid.UUID, new_bom: BillOfMaterial, max_depth: int = 20
    ) -> None:
        """
        Validates that saving the `new_bom` will not introduce a circular reference
        anywhere in the active BOM hierarchy. Checks across all active BOMs.
        """
        # A stack of (product_id, depth)
        target_product_id = new_bom.target_product_id
        
        # Fast fail self-reference
        for line in new_bom.lines:
            line_target = line.template_id or line.variant_id
            if line_target and line_target == target_product_id:
                raise ValueError("A BOM cannot reference its own product as a component.")

        await self._check_tree(
            tenant_id=tenant_id,
            bom=new_bom,
            visited=set([target_product_id]),
            depth=1,
            max_depth=max_depth
        )

    async def _check_tree(self, tenant_id: uuid.UUID, bom: BillOfMaterial, visited: set[uuid.UUID], depth: int, max_depth: int) -> None:
        if depth > max_depth:
            raise ValueError(f"BOM recursion depth exceeded limit of {max_depth}.")

        for line in bom.lines:
            target_id = line.template_id or line.variant_id
            if not target_id:
                continue # It's a raw material, no circular bom possible

            if target_id in visited:
                raise ValueError(f"Circular dependency detected involving product {target_id}.")

            child_bom = await self._bom_provider.get_active_bom(
                tenant_id=tenant_id,
                template_id=line.template_id,
                variant_id=line.variant_id
            )
            if child_bom:
                new_visited = visited.copy()
                new_visited.add(target_id)
                await self._check_tree(tenant_id, child_bom, new_visited, depth + 1, max_depth)
