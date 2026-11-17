import uuid
from decimal import Decimal
from typing import Optional, Protocol, Dict, Any, Tuple, cast

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.services.component_resolution import ComponentResolver, ComponentResolution


class TenantProvider(Protocol):
    async def get_tenant_currency(self, tenant_id: uuid.UUID) -> Tuple[Optional[str], Optional[str]]:
        ...


class BOMProvider(Protocol):
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        ...


class CostProvider(Protocol):
    async def get_material_cost(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Optional[Decimal]:
        ...

    async def get_operation_cost(self, tenant_id: uuid.UUID, operation_id: uuid.UUID) -> Optional[Decimal]:
        ...


class CostRollupService:
    def __init__(
        self, bom_provider: BOMProvider, cost_provider: CostProvider, tenant_provider: TenantProvider,
        component_resolver: Optional[ComponentResolver] = None,
    ):
        self._bom_provider = bom_provider
        self._cost_provider = cost_provider
        self._tenant_provider = tenant_provider
        # Application callers wire the shared tenant-scoped component resolver.
        # Basic providers remain usable for pure cost arithmetic.
        self._resolver = component_resolver or (
            cast(ComponentResolver, bom_provider) if hasattr(type(bom_provider), "resolve_component") else None
        )

    async def calculate_standard_cost(
        self, tenant_id: uuid.UUID, current_bom: BillOfMaterial, max_depth: int = 20, *, exact_tree: bool = False,
        tree_row_limit: int | None = None
    ) -> Dict[str, Any]:
        """Live cost per ONE target output base unit; never writes historical costs.

        Each child's full total stays in the parent's material subtotal. Direct
        operations and PER_PIECE making retain separate subtotals. Descendant
        tree rows explain that contribution and must not be added a second time.
        """
        mat, op, making, total, missing, tree = await self._calculate_recursive(
            tenant_id, current_bom, 1, max_depth, frozenset(), Decimal("1"), exact_tree=exact_tree,
            remaining_rows=[tree_row_limit] if tree_row_limit is not None else None,
        )
        currency, symbol = await self._tenant_provider.get_tenant_currency(tenant_id)
        tree.update(currency_code=currency, currency_symbol=symbol)
        return {
            "material_cost": mat, "operation_cost": op, "making_cost": making,
            "total_cost": total if not missing else Decimal("0"),
            "currency_code": currency, "currency_symbol": symbol,
            "is_complete": not missing, "missing_costs": missing, "tree": tree,
        }

    async def _calculate_recursive(
        self, tenant_id: uuid.UUID, bom: BillOfMaterial, depth: int, max_depth: int,
        path: frozenset[uuid.UUID], multiplier: Decimal, *, structure_only: bool = False,
        exact_tree: bool = False, remaining_rows: list[int] | None = None,
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal, list[Dict[str, Any]], Dict[str, Any]]:
        number = (lambda value: value) if exact_tree else float
        mat = op = making = Decimal("0")
        missing: list[Dict[str, Any]] = []
        children: list[Dict[str, Any]] = []
        tree: Dict[str, Any] = {
            "id": str(bom.id), "bom_id": str(bom.id), "name": f"BOM {bom.version}",
            "code": bom.version, "version": bom.version,
            "type": "variant" if bom.variant_id else "template", "depth": depth - 1,
            "quantity": number(multiplier), "children": children,
        }
        failure = (
            ("TENANT_MISMATCH", "BOM belongs to a different tenant") if bom.tenant_id != tenant_id else
            ("BOM_DELETED", "BOM is deleted") if bom.is_deleted else
            ("CYCLE_DETECTED", "Cyclic BOM reference detected on this branch") if bom.id in path else
            ("MAX_DEPTH", f"Maximum BOM cost depth {max_depth} reached") if depth > max_depth else None
        )
        if failure:
            missing.append({"component_type": "bom", "component_id": str(bom.id),
                            "name": tree["name"], "reason": failure[0], "message": failure[1]})
        else:
            next_path = path | {bom.id}
            for line in bom.lines:
                if remaining_rows is not None:
                    remaining_rows[0] -= 1
                    if remaining_rows[0] < 0:
                        raise OverflowError("BOM report exceeds the component and operation row limit")
                component_id = line.material_id or line.variant_id or line.template_id
                component_type = "material" if line.material_id else "bom"
                quantity = Decimal(str(line.quantity)) * (
                    Decimal("1") + Decimal(str(line.scrap_percentage)) / Decimal("100")
                )
                global_quantity = quantity * multiplier
                if self._resolver is not None:
                    resolution = await self._resolver.resolve_component(tenant_id, line)
                else:
                    child = None if line.material_id else await self._bom_provider.get_active_bom(
                        tenant_id=tenant_id, template_id=line.template_id, variant_id=line.variant_id,
                    )
                    resolution = ComponentResolution(child_bom=child)
                    if not line.material_id and child is None:
                        resolution.reason, resolution.message = "BOM_MISSING", "Active child BOM is missing"
                details = resolution.details
                node: Dict[str, Any] = {
                    "id": str(component_id), "line_id": str(line.id),
                    "name": details.get("name", str(component_id)), "code": details.get("code"),
                    "type": "material" if line.material_id else "variant" if line.variant_id else "template",
                    "material_type": details.get("material_type"),
                    "quantity": number(global_quantity), "unit": details.get("unit_name"),
                    "unit_id": str(line.unit_id) if line.unit_id else None,
                    "scrap_percentage": number(line.scrap_percentage), "depth": depth,
                    "cost": None, "children": [], "is_complete": True,
                    **({"version": resolution.child_bom.version} if exact_tree and resolution.child_bom else {}),
                    "cost_basis": "CHILD_BOM" if resolution.child_bom else "STANDARD_COST",
                }
                children.append(node)
                reason, message = resolution.reason, resolution.message
                if line.tenant_id != tenant_id:
                    reason, message = "TENANT_MISMATCH", "Component line belongs to a different tenant"
                if reason:
                    missing.append({"component_type": component_type, "component_id": str(component_id),
                                    "name": node["name"], "code": node["code"], "reason": reason, "message": message})
                    node.update(is_complete=False, reason=reason, message=message, cost_basis="UNRESOLVED")
                child = resolution.child_bom
                if reason or structure_only:
                    if child is not None and reason in (None, "OUTPUT_UOM_MISSING", "UOM_INCOMPATIBLE"):
                        # Show the recipe per child output unit when the parent quantity cannot be converted.
                        _, _, _, _, child_issues, recipe = await self._calculate_recursive(
                            tenant_id, child, depth + 1, max_depth, next_path,
                            Decimal("1") if reason else global_quantity, structure_only=True,
                            exact_tree=exact_tree, remaining_rows=remaining_rows,
                        )
                        node.update(bom_id=str(child.id), children=recipe["children"], cost_basis="UNRESOLVED")
                        missing.extend(child_issues)
                    continue
                if resolution.child_bom is not None:
                    cm, co, ck, child_total, child_missing, child_tree = await self._calculate_recursive(
                        tenant_id, resolution.child_bom, depth + 1, max_depth, next_path, global_quantity,
                        exact_tree=exact_tree, remaining_rows=remaining_rows,
                    )
                    node.update(
                        bom_id=str(resolution.child_bom.id), children=child_tree["children"],
                        component_material_cost=number(cm * global_quantity),
                        operation_cost=number(co * global_quantity), making_cost=number(ck * global_quantity),
                    )
                    if exact_tree:
                        if line.material_id is not None and not structure_only:
                            node["stored_standard_cost"] = await self._cost_provider.get_material_cost(tenant_id, line.material_id)
                        node["operations"] = child_tree.get("operations", [])
                    if child_missing:
                        missing.extend(child_missing)
                        node.update(is_complete=False, reason="CHILD_INCOMPLETE", message="Child BOM costing is incomplete")
                        continue
                    unit_cost = child_total
                else:
                    if line.material_id is None:
                        missing.append({"component_type": "bom", "component_id": str(component_id),
                                        "name": node["name"], "reason": "BOM_MISSING",
                                        "message": "Active child BOM is missing"})
                        node.update(is_complete=False, reason="BOM_MISSING", message="Active child BOM is missing")
                        continue
                    unit_cost = await self._cost_provider.get_material_cost(tenant_id, line.material_id)
                    if unit_cost is None:
                        missing.append({"component_type": "material", "component_id": str(component_id),
                                        "name": node["name"], "code": node["code"],
                                        "reason": "STANDARD_COST_MISSING", "message": "Approved material standard cost is missing"})
                        node.update(is_complete=False, reason="STANDARD_COST_MISSING", message="Approved material standard cost is missing")
                        continue
                mat += quantity * unit_cost
                node.update(unit_cost=number(unit_cost), cost=number(global_quantity * unit_cost))
            for bom_op in (() if structure_only else bom.operations):
                if remaining_rows is not None:
                    remaining_rows[0] -= 1
                    if remaining_rows[0] < 0:
                        raise OverflowError("BOM report exceeds the component and operation row limit")
                value = (await self._cost_provider.get_operation_cost(tenant_id, bom_op.operation_id)
                         if bom_op.tenant_id == tenant_id else None)
                if exact_tree:
                    tree.setdefault("operations", []).append({
                        "operation_id": str(bom_op.operation_id),
                        "cost": value * multiplier if value is not None else None,
                    })
                if value is None:
                    missing.append({"component_type": "operation", "component_id": str(bom_op.operation_id),
                                    "name": "Operation", "reason": "OPERATION_COST_MISSING",
                                    "message": "Operation or workstation is missing, inactive, deleted or outside this tenant"})
                else:
                    op += value
            if not structure_only and bom.making_charge is not None and bom.making_charge_basis == "PER_PIECE":
                making = Decimal(str(bom.making_charge))
        total = mat + op + making
        tree.update(is_complete=not missing, missing_costs=missing,
                    cost=None if missing else number(total * multiplier),
                    component_material_cost=number(mat * multiplier),
                    operation_cost=number(op * multiplier), making_cost=number(making * multiplier))
        return mat, op, making, total, missing, tree
