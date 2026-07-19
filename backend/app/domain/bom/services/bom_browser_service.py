import uuid
from typing import Any, Dict, List, Optional, Protocol

from backend.app.domain.bom.entities.bom import BillOfMaterial


class BOMProvider(Protocol):
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        ...

class ComponentDetailProvider(Protocol):
    async def get_component_details(self, tenant_id: uuid.UUID, is_material: bool, component_id: uuid.UUID) -> Dict[str, Any]:
        """Returns name, code, etc., for rendering tree"""
        ...


class BOMBrowserService:
    def __init__(self, bom_provider: BOMProvider, details_provider: ComponentDetailProvider):
        self._bom_provider = bom_provider
        self._details = details_provider

    async def build_tree(self, tenant_id: uuid.UUID, bom: BillOfMaterial, max_depth: int = 20) -> Dict[str, Any]:
        """
        Builds a nested JSON tree of the BOM up to max_depth.
        """
        return await self._build_recursive(tenant_id, bom, depth=1, max_depth=max_depth, qty_multiplier=1.0)

    async def _build_recursive(
        self, tenant_id: uuid.UUID, bom: BillOfMaterial, depth: int, max_depth: int, qty_multiplier: float
    ) -> Dict[str, Any]:

        children: List[Dict[str, Any]] = []

        if depth <= max_depth:
            for line in bom.lines:
                qty = float(line.quantity) * (1.0 + float(line.scrap_percentage)/100.0) * qty_multiplier
                is_material = line.material_id is not None
                component_id = line.material_id or line.variant_id or line.template_id

                details = await self._details.get_component_details(tenant_id, is_material, component_id) # type: ignore
                
                child_node = {
                    "id": str(component_id),
                    "name": details.get("name", "Unknown"),
                    "code": details.get("code", "Unknown"),
                    "type": "material" if is_material else "variant" if line.variant_id else "template",
                    "quantity": qty,
                    "unit": details.get("unit_name", "pcs"),
                    "children": []
                }

                if not is_material:
                    child_bom = await self._bom_provider.get_active_bom(
                        tenant_id=tenant_id, template_id=line.template_id, variant_id=line.variant_id
                    )
                    if child_bom:
                        child_tree = await self._build_recursive(tenant_id, child_bom, depth + 1, max_depth, qty)
                        child_node["children"] = child_tree.get("children", [])
                
                children.append(child_node)

        # Base node assumes details are loaded for the root by API handler
        return {
            "id": str(bom.id),
            "version": bom.version,
            "children": children
        }

    def find_node_in_tree(self, tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
        if tree.get("id") == node_id:
            return tree
        for child in tree.get("children", []):
            result = self.find_node_in_tree(child, node_id)
            if result is not None:
                return result
        return None
