# Phase C — semi-finished BOM cost rollup verification

Implemented 16 November 2026 under the approved cost-precedence rules.

## Root cause and numerical result

The old cost service treated every `material_id` as a stored-cost leaf, while the browser expanded semi-finished materials through `ItemVariant.material_id → BOM.variant_id`. The cost path never called that resolver.

| Controlled case | Before | After |
|---|---:|---:|
| Child raw materials 100 + 10 + 10, outside making 30 | 150 | 150 |
| Parent: 2 child units + additional raw 12, referenced through variant | 312 | 312 |
| Same parent referenced through semi-finished material, with stored approved cost 90 | 192 | **312** |
| Stored semi-finished `Material.current_cost` | 90 | **90, unchanged** |
| Child also has 60 minutes of operations at 10/hour | Not rolled through material link | Child 160; parent **332** |

Child totals are multiplied once. The parent's material/component subtotal continues including a nested child's full total. Parent-only operation and making subtotals retain the existing convention. For the 312 example the parent categories are material/components 312 + direct operations 0 + direct making 0. The child's 60 making contribution is already inside its 300 branch contribution and is never added again.

## Approved precedence implemented

- Raw materials use the existing approved-material standard-cost provider.
- Semi-finished materials with one valid explicit manufacturing mapping and active child BOM use the child's live calculated cost, regardless of a different approved stored material cost.
- Semi-finished materials with no manufacturing mapping use approved stored material cost as a leaf.
- An existing mapping with missing/inactive/deleted/ambiguous targets or BOMs produces incomplete cost. No stored-cost fallback occurs for a broken mapping or incomplete child.
- No material cost, approval revision, history, inventory, PO/GRN, subcontract, or activation/version state is written by this calculation.

## Resolver and safety

The existing `BOMRepository.get_bom_for_material()` relationship is reused and strengthened. It checks the material's tenant/type/active/soft-delete state, distinguishes no mapping from invalid mappings, requires an unambiguous active nondeleted variant, verifies its template, and reuses `get_active_bom()` for version selection. Duplicate active BOMs are errors rather than arbitrary selections. Existing activation/versioning write rules are unchanged.

`InfrastructureBOMProvider.resolve_component()` supplies the same component resolution to the cost service used by both cost and tree API handlers. It checks tenant boundaries, component validity and child output units. Deleted component lines are excluded; corrupt cross-tenant lines produce incomplete cost rather than a silently understated valid total. Operation and workstation lookup is tenant scoped and excludes inactive/deleted records, preserving `(setup_minutes + run_minutes) / 60 × hourly_rate`.

Recursion uses an immutable ancestor set per branch. Cycles and maximum-depth truncation return explicit missing-cost reasons. Repeated child BOMs in separate branches remain valid. Missing child costs propagate to parents, with `is_complete=false` and the existing numeric-zero incomplete-total convention. Tree nodes use `cost=null` for unavailable contributions, and the UI labels them incomplete. Explicit configured zero remains valid.

### Output-unit semantics

The existing service defines cost per one output unit; the BOM model has no output-batch/yield quantity. The target variant has an explicit `base_unit_id`, inherited from the template at variant creation. Linked-child calculation requires the component line UOM, material/component base UOM and child target base UOM to identify the same configured active tenant UOM. Missing child output/quantity UOMs or incompatible UOMs are incomplete; there is no name-based equivalence, invented factor, implicit template-UOM substitution, or automatic conversion. Existing PER_PIECE making and scrap formulas are preserved.

## Tree, breakdown and API consistency

The application wires `BOMBrowserService` to the same `CostRollupService` traversal that produces the summary. The tree includes calculated child contributions, completeness/reasons, and explanatory making/operation subtotals. The component breakdown lists immediate branches once, including template/variant branches. Descendant raw components remain expandable explanatory details; they are not flattened into an additional contribution table. Repeated references have line IDs for stable UI keys.

The tree uses tenant currency through the existing currency formatter, replacing hardcoded dollar labels. Missing-cost contracts now accept `component_type="bom"` and optional `reason`/`message`; the API retains resolver-supplied names/messages. The same fields are represented in frontend types. Existing BOM types were moved into the BOM module with a compatibility re-export, preserving existing callers.

## Exact files changed

Relative to `C:\Users\sayye\source\repos\MedTrack`:

1. `backend/app/domain/bom/services/component_resolution.py` — shared resolution contract and error reasons.
2. `backend/app/domain/bom/services/cost_rollup_service.py` — linked child precedence, safe recursion, shared cost tree.
3. `backend/app/domain/bom/services/bom_browser_service.py` — use the injected cost traversal for application browsing; initialize structural path tracking with the root.
4. `backend/app/infrastructure/persistence/repositories/bom_repository.py` — exact component/UOM lookup, robust manufacturing mapping, deleted-line handling.
5. `backend/app/infrastructure/services/bom_providers.py` — shared resolver, exact child UOM checks, tenant-scoped operation/workstation query.
6. `backend/app/application/bom/handlers/bom_advanced_handlers.py` — wire the same resolver/traversal into tree and cost requests.
7. `backend/app/interfaces/api/v1/schemas/bom_schemas.py` — missing BOM/reason/message contract.
8. `backend/app/interfaces/api/v1/routes/boms.py` — preserve resolver-provided missing component labels.
9. `frontend/src/modules/bom/components/BOMCostBreakdown.tsx` — one contribution per branch; explicit incomplete reasons.
10. `frontend/src/modules/bom/components/BOMTreeView.tsx` — tenant currency and explanatory included-cost labels.
11. `frontend/src/modules/bom/types/bom.types.ts` — module-owned BOM types and expanded cost metadata.
12. `frontend/src/types/bom.types.ts` — compatibility re-export.
13. `tests/integration/test_semi_finished_bom_cost.py` — real repository/provider/handler regression tests in an isolated database.
14. `frontend/src/modules/bom/components/BOMCostConsistency.test.tsx` — reconciliation, explanatory expansion, currency, and incomplete-state tests.
15. `docs/audit-reports/phase-c-semi-finished-bom-verification.md` — this report.

## Verification results

**136 backend tests passed**: 35 new Phase C checks plus 101 existing selected Phase B, making-charge, BOM target immutability, pricing-contract, approval-safeguard and sales-pricing regressions.

The new integration fixture uses a disposable in-memory SQLite database with real SQLAlchemy models, BOM repository, infrastructure providers, and application handlers. It does not connect to the configured development or production database. It covers raw approved costs; template and variant children; linked and unmapped semi-finished materials; stored cost/history preservation; making and operations; nested levels; repeated branches; parent and child scrap; inactive/deleted material, variant, template, BOM and operation/workstation states; duplicate mappings/active BOMs; cycles; maximum depth; tenant isolation; incompatible/missing output units; missing approved costs; explicit zero; cost/tree reconciliation; and missing-BOM API serialization.

**7 frontend tests passed**: 3 new BOM consistency tests plus 4 existing Phase B Buy-tab tests. The new tests verify 300 + 12 = 312 without listing raw descendants as additional contributions, tenant currency and explanatory tree expansion, and missing child/unit costs remaining visibly incomplete.

TypeScript checking returned **the same 42 pre-existing errors with identical diagnostic output** as the saved baseline. Existing failures include duplicate BOM detail-page imports and unrelated procurement/location/form/client mismatches. No new TypeScript diagnostics were introduced. A successful full frontend build or live browser end-to-end run is not claimed.

Commands:

```text
python -B -m pytest --noconftest -p no:cacheprovider tests/integration/test_semi_finished_bom_cost.py tests/integration/test_onboarding_initial_standard_cost.py backend/tests/unit/bom/test_making_cost_rollup.py backend/tests/unit/bom/test_bom_target_immutability.py backend/tests/unit/domain/sales/test_pricing_service_option_b.py tests/unit/procurement/test_pricing_api_contracts.py tests/unit/procurement/test_pricing_cost_approval_safeguards.py -q --tb=short
frontend/node_modules/.bin/vitest run src/modules/bom/components/BOMCostConsistency.test.tsx src/modules/inventory/components/MaterialSupplierPrices.test.tsx --config vitest.config.ts
frontend/node_modules/.bin/tsc --noEmit --incremental false -p frontend/tsconfig.json --pretty false
```

The selected backend run uses its own fixtures and bypasses the repository's known two-test-tree conftest collision. Windows asyncio and Vitest temporary files required execution outside the sandbox. The full backend suite and a production performance/load test were not run.

## Preservation and remaining issues

- No schema change, migration, pending SQL, live-data repair, or historical recalculation was performed.
- No files were staged or committed. The Git index matches the Phase C starting snapshot.
- Phase B implementation files were not edited by this phase. A concurrent external change to the Excel template generator in `material_onboarding.py` was observed and preserved; it is not included in the changed-file list above.
- Nullable or incompatible child output UOM records must be corrected through existing master-data workflows; they now produce incomplete cost rather than guessed conversions. The separate UOM conversion repository defects remain outside scope.
- Existing frontend build failures remain. Verification establishes workspace behavior through isolated backend/component tests, not a live-data rollout or running-server restart.

Phase C stops here. PO supplier pricing integration, inventory valuation and other ERP workflows require separate approval.
