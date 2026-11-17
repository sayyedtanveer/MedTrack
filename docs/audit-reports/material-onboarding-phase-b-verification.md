# Phase B — Raw-material onboarding and BOM standard cost

Implemented 16 November 2026. Scope: the existing Excel onboarding API, Material Edit → Buy, and shared authorized direct standard-cost saving.

## Implemented behavior

- New material with supplier price 500 and explicit initial cost 400: stores a DRAFT supplier agreement at 500 and sets effective standard cost to 400, with an APPROVED revision and immutable cost-history entry. No second Finance approver is required.
- With blank initial cost, all rows for that material are evaluated together. One unambiguous current rate can initialize cost only with matching configured UOM IDs, matching tenant currency, and `procurement_pricing:cost:propose` permission. Conflicting rates, incompatible units/currency, missing tenant currency, invalid/failed related rows, or insufficient permission leave cost unconfigured with an explicit warning.
- Explicitly configured zero remains valid. Effective costs, revision amounts and history use the material column's four-decimal precision; six-decimal supplier quotes remain separate.
- Re-import never changes the standard cost of a material that existed before the import, including an existing unconfigured material. Existing pending revisions and history are preserved, and imports no longer add duplicate pending proposals.
- Repeated material rows are matched before cost selection. Code/name conflicts are rejected. Identical supplier agreements are reused; changed overlapping price, UOM, MOQ, dates or tiers are reported as row errors. Agreement checks for an existing material execute under its row lock.
- Preview and dry run execute the same database validation/savepoint path and roll back. They report the same pricing counters and cost outcomes as execution. Execution preserves row-level partial success and reports validation and execution failures.
- Excel date/timestamp values are normalized. Pricing values reject nonfinite numbers, invalid ranges and unsupported precision; currency format and exact costing-currency compatibility are checked. Supplier UOM resolves through the active tenant UOM master. No conversion engine is used.

## Shared cost infrastructure

Both `/inventory/materials/{id}/set-standard-cost` and the importer call `DirectStandardCostHandler`. It reuses `StandardCostRevisionRepository.get_material_current_cost(lock=True)`, `get_approved_cost()`, and `update_material_current_cost()`, plus the existing revision/history models.

The handler locks before reading old cost or comparing `expected_current_cost`, then prepares the material update, APPROVED revision, and history in the caller's transaction. It never commits independently. Revision reason codes remain `INITIAL_SETUP` / `MANUAL_ADJUSTMENT`; history uses `INITIAL_SETUP` / `DIRECT_REVISION`, with the user's reason retained in notes. Permission checks remain at the existing API boundary and are separately evaluated for import; bulk-upload permission does not grant cost permission.

The Buy action sends an expected cost for first setup as well as revisions, displays the saved normalized amount, and retains its existing cache invalidation for live BOM costs.

## Supplier-price visibility

The existing drawer Buy tab includes a separate Supplier Prices section. It uses the existing agreement list API, supplier master lookup, and UOM lookup, displaying supplier name/code, price/currency, UOM, MOQ, dates and agreement status. It loads all result pages. Decimal-string prices/MOQs are normalized at the client boundary before formatting. DRAFT quotes are explicitly labelled and described as inactive purchasing agreements.

Purchasing Summary remains separate and displays **“No purchase history yet”** when no completed GRN exists. Quotes remain visible in that state. No preferred-supplier label is inferred from a quote. No GRN write path or PO pricing workflow was changed.

## Exact files changed in this phase

Paths below are relative to `C:\Users\sayye\source\repos\MedTrack`.

| File | Change |
|---|---|
| `backend/app/application/procurement/pricing/direct_standard_cost.py` | New shared, locked direct cost handler and precision validation |
| `backend/app/application/inventory/services/onboarding_pricing.py` | New grouped initial-cost policy and import number/date helpers |
| `backend/app/interfaces/api/v1/routes/inventory.py` | Existing direct endpoint delegates to shared handler |
| `backend/app/interfaces/api/v1/routes/material_onboarding.py` | Grouped initialization, permission checks, re-import validation, reliable preview/dry run, reporting and template copy |
| `backend/app/interfaces/api/v1/schemas/inventory_schemas.py` | Direct cost upper bound and precision/concurrency documentation |
| `frontend/src/modules/inventory/components/MaterialFormDrawer.tsx` | Supplier section, no-history text, expected-cost token, normalized saved amount |
| `frontend/src/modules/inventory/components/MaterialSupplierPrices.tsx` | New supplier quote section using existing APIs |
| `frontend/src/modules/inventory/components/MaterialSupplierPrices.test.tsx` | Buy drawer and Decimal response regression tests |
| `frontend/src/modules/inventory/pages/MaterialOnboardingPage.tsx` | Correct counters, warnings/outcomes, partial-success messages, preview errors and cache invalidation |
| `frontend/src/modules/inventory/services/materialOnboardingApi.ts` | Onboarding client moved into the inventory module with explicit response types |
| `frontend/src/services/material-onboarding.service.ts` | Compatibility re-export preserving existing callers |
| `frontend/src/modules/procurement/services/supplierPriceAgreementApi.ts` | Normalize Decimal-string agreement prices/MOQs |
| `tests/integration/test_onboarding_initial_standard_cost.py` | Active importer, persistence, standard-cost API, BOM, GRN summary and concurrency-ordering coverage |
| `docs/audit-reports/material-onboarding-phase-b-verification.md` | This report and separate follow-up issues |

## Verification

**40 new backend checks passed.** Tests use an isolated in-memory SQLite database and real SQLAlchemy models/repositories, with number-series generation and permission outcomes stubbed where appropriate. Coverage includes actual XLSX upload → mapping → validation → rollback preview → execution, explicit/blank/zero costs, repeated/conflicting suppliers, existing-material re-import, changed agreement terms, UOM/currency mismatch, denied cost permission, pending revision preservation, partial failure, precision, atomic rollback, tenant boundaries, and the existing direct endpoint.

BOM verification uses the existing `InfrastructureCostProvider` and `CostRollupService`: 400 per unit × quantity 5 = **2,000**; a later direct update to 450 yields **2,250** on a fresh live calculation. Earlier history remains at 400. Missing configuration returns no provider cost; explicit zero returns zero as a configured cost.

GRN-summary regression starts with no purchase history, adds completed and noncompleted/reversed receipt records in the isolated fixture, and verifies that only completed receipts supply the latest price/supplier/count. Standard cost remains 400 and its history remains unchanged. This checks the existing query behavior; it is not a live authenticated GRN receiving test.

**25 existing backend checks passed:** pricing route/OpenAPI/permission contracts, separate approval safeguards, and making-charge/nested-BOM rollup tests. These workflows were not modified.

**4 frontend checks passed:** actual drawer Buy tab renders supplier name/code, normalized price, UOM and DRAFT label with no GRN history; direct saving sends the expected-cost token; pricing failures are explicit; malformed Decimal-string data is rejected.

Commands:

```text
python -B -m pytest --noconftest -p no:cacheprovider tests/integration/test_onboarding_initial_standard_cost.py -q -x --tb=short
python -B -m pytest --noconftest -p no:cacheprovider tests/unit/procurement/test_pricing_api_contracts.py tests/unit/procurement/test_pricing_cost_approval_safeguards.py backend/tests/unit/bom/test_making_cost_rollup.py -q --tb=short
frontend/node_modules/.bin/vitest run src/modules/inventory/components/MaterialSupplierPrices.test.tsx --config vitest.config.ts
frontend/node_modules/.bin/tsc --noEmit --incremental false -p frontend/tsconfig.json --pretty false
```

The selected backend runs bypass repository conftest loading to avoid the known two-test-tree import collision; the new test file owns its database fixtures. Windows asyncio and Vitest temporary-file operations required execution outside the sandbox. No test connected to or mutated the development database.

Concurrency verification checks two competing handler calls under a simulated transaction lock, and separately compiles the actual repository query with the PostgreSQL dialect to require `FOR UPDATE`, tenant scope and soft-delete filtering. This is not a live multi-connection PostgreSQL race test. SQLite does not prove PostgreSQL locking behavior.

Frontend type checking was captured before edits. Its pre-existing failures include duplicate BOM page imports, invalid router imports, missing storage-location modules/types, proposal form typing, and pricing history/override client mismatches. Final verification returned **exactly the same 42 errors and identical diagnostic output** as the saved baseline. None were repaired as part of this scope. A full frontend build and live browser end-to-end flow are not claimed. The complete backend suite was not run; the previously identified missing `hypothesis` dependency and wider fixture issues remain outside this phase.

## Schema and preservation

Before implementation, a read-only metadata query verified the configured **local development** schema. Required `materials.current_cost`, supplier agreement `purchase_uom_id`/`minimum_order_quantity`, standard-cost revision, history, tenant currency, and UOM columns exist. Material cost is Numeric(18,4); revision/history amounts are Numeric(18,6). No migration is required for this implementation, and none was created or executed.

An initial content/hash snapshot and Git index snapshot were saved outside the repository. Existing unrelated source changes and staged work were preserved; nothing was staged or committed in this phase. Runtime-generated tracked bytecode is restored only when its exact original content can be verified against the saved baseline and unchanged index.

## Separate follow-up issues — not implemented

1. **BOM-COST-LEAF-01:** BOM browsing expands a semi-finished component referenced by `material_id`, but cost rollup treats that reference as a material-cost leaf. Resolve and test independently; this phase leaves multi-level resolution and making-charge logic unchanged.
2. Existing frontend build failures listed above need their own fixes.
3. Existing PO/GRN currency/UOM propagation, legacy pricing suggestion fallback, and the old GRN-page generic cost-update action remain as identified in Phase A. No PO redesign, optional last-purchase-cost action, or automatic GRN-to-standard-cost update was added.
4. The existing UOM conversion repository defects remain. This phase uses exact configured UOM matches only.
5. Existing manual database setup/repair scripts and unrelated BOM schema additions still require separate deployment review. This phase's development-schema check does not certify other installations.
6. Preferred Supplier import mapping still does not persist a preferred relationship in the active importer; the Buy section therefore makes no preference claim. Existing unrelated onboarding metadata limitations were not expanded into this costing fix.

Phase B stops here; production data, migrations, PO redesign and automatic receipt-driven standard-cost changes remain outside scope.
