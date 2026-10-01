import uuid
from typing import Any, Dict, List, Optional, Protocol

from backend.app.domain.bom.entities.bom import BillOfMaterial


class BOMProvider(Protocol):
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        ...
    
    async def get_bom_for_material(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
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
        Tracks visited BOM IDs to prevent circular references.
        """
        visited_bom_ids: set[uuid.UUID] = set()
        return await self._build_recursive(tenant_id, bom, depth=1, max_depth=max_depth, qty_multiplier=1.0, visited_bom_ids=visited_bom_ids)

    async def _build_recursive(
        self, tenant_id: uuid.UUID, bom: BillOfMaterial, depth: int, max_depth: int, qty_multiplier: float, visited_bom_ids: set[uuid.UUID]
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
                
                # Add material_type to node if it's a material (for frontend rendering)
                if is_material and details.get("material_type"):
                    child_node["material_type"] = details.get("material_type")

                # Recursion logic: check for child BOMs
                child_bom = None
                
                if not is_material:
                    # Existing logic: templates and variants
                    child_bom = await self._bom_provider.get_active_bom(
                        tenant_id=tenant_id, template_id=line.template_id, variant_id=line.variant_id
                    )
                elif is_material and details.get("material_type") == "semi_finished":
                    # New logic: semi-finished materials can have BOMs via variant-material link
                    child_bom = await self._bom_provider.get_bom_for_material(
                        tenant_id=tenant_id, material_id=line.material_id # type: ignore
                    )
                
                # Circular reference protection: only recurse if BOM not already visited
                if child_bom and child_bom.id not in visited_bom_ids:
                    visited_bom_ids.add(child_bom.id)
                    child_tree = await self._build_recursive(tenant_id, child_bom, depth + 1, max_depth, qty, visited_bom_ids)
                    child_node["children"] = child_tree.get("children", [])
                    visited_bom_ids.remove(child_bom.id)  # Allow this BOM in other branches
                
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
