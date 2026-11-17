# MedTrack Procurement Pricing Module
## Read-Only Gap Analysis Report

**Audit date:** 2026-11-13  
**Audit scope:** Procurement Pricing Phase 2 lifecycle  
**Audit completion:** 100% of the requested source-code inspection and reporting scope  
**Implementation performed:** None  
**Database access or changes:** None  
**Test result:** No test cases were executed; a targeted pytest invocation stopped during conftest import.

> This report records a read-only source audit. The live database schema, applied migration state, and runtime behavior have not been verified. A feature is not described as verified merely because a model, endpoint, UI component, or test exists.

## 1. Executive Summary

MedTrack contains substantial procurement pricing functionality, including material onboarding, supplier price agreements, standard-cost revisions, a six-level pricing engine, GRN workflows, and BOM cost rollup. The complete end-to-end pricing lifecycle is **not complete or verified**.

The highest-priority risks identified are:

1. Pricing API routes lack explicit route-level RBAC checks and appear to have a duplicated `/api/v1` prefix.
2. Supplier quotation persistence and lifecycle handling are incompatible with the current ORM model and status conventions.
3. Currency and UOM conversion are not integrated into pricing comparisons; the UOM repository mapping is inconsistent with its domain entity.
4. The PO screen uses manual prices and is not connected to the six-level pricing engine.
5. Price override routes/services/UI disagree on their contracts, and PO-line save does not record overrides.
6. BOM incomplete-cost results do not fit the backend response schema or frontend numeric-cost assumptions.
7. GRN receipt paths have different cumulative over-receipt protection, and purchase history does not preserve exact GRN-line linkage or currency/UOM metadata.

## 2. Scope, Safety, and Worktree

- The audit used source inspection, searches, and a targeted test invocation only.
- No source, test, migration, SQL, or database files were changed by the audit.
- No migration or SQL script was applied, and no database was accessed.
- No dependency was installed, removed, or updated.
- The worktree was already dirty: **73 tracked paths changed and 54 untracked paths** (127 total). Those changes were preserved.
- The modified `.env` was not opened.
- The live database schema/current migration state is unknown.
- No deployment or production action was taken.

## 3. Status Definitions

- **COMPLETE AND VERIFIED** — Observed behavior was supported by safe runtime/test evidence.
- **IMPLEMENTED BUT NOT VERIFIED** — Source path is present, but no safe runtime/test evidence confirms it.
- **PARTIALLY IMPLEMENTED** — Some required behavior exists, with material gaps remaining.
- **NOT IMPLEMENTED** — No implementation was found for the required behavior in the inspected workflow.
- **BROKEN / REGRESSION DETECTED** — Inspected producer/consumer contracts or workflow paths are incompatible or fail to satisfy the requirement as written.

No material end-to-end requirement received the status **COMPLETE AND VERIFIED** because behavior tests could not run.

## 4. Consolidated Gap Analysis

| ID | Priority | Business area / requirement | Existing implementation and evidence | Status | Gap / risk | Recommended action |
|---|---|---|---|---|---|---|
| P1-01 | P1 | Material import without supplier; supplier price and standard cost kept separate | Active template/upload/preview/confirmation flow is in [material_onboarding.py](../backend/app/interfaces/api/v1/routes/material_onboarding.py). The active route creates materials at `current_cost=0`, supplier agreements separately in `DRAFT`, and proposed standard costs as `PENDING` revisions. | IMPLEMENTED BUT NOT VERIFIED | The active path does not directly set an approved cost, but no end-to-end execution was run. Draft agreements are not yet available to the PO engine. | Preserve this active path and verify no-supplier, supplier-price-only, and proposed-standard-cost cases with isolated tests. Do not wire the alternate service until its direct-cost update path is resolved. |
| P1-02 | P1 | Multiple suppliers, row correction, import counts, pricing status | [MaterialOnboardingPage.tsx](../frontend/src/modules/inventory/pages/MaterialOnboardingPage.tsx) supports preview/confirmation. The backend computes row results, but the UI correction payload omits supplier-price and proposed-cost fields, and its summary expectations differ from the API response shape. | PARTIALLY IMPLEMENTED | Price-field errors cannot be corrected in the UI. Multiple suppliers appear possible through repeated material rows but were not verified. “Pricing not configured” is not clearly displayed. | Align UI/API types; support correction of all price fields; verify duplicates, existing-material updates, multiple suppliers, and created/updated/skipped/rejected counts. |
| P1-03 | P1 | Agreement lifecycle, effective dates, overlap prevention, rejected editing and expiry | [entities.py](../backend/app/domain/procurement/pricing/entities.py), [handlers.py](../backend/app/application/procurement/pricing/handlers.py), and [procurement_pricing_repository.py](../backend/app/infrastructure/persistence/repositories/procurement_pricing_repository.py) implement transitions, date validation, and an application-level overlap check. | PARTIALLY IMPLEMENTED | Rejection transitions to `DRAFT`, but no complete operation to edit price/date/UOM after rejection was found. Out-of-date agreements are filtered by effective date, but no expiry transition/job was found. Lock/concurrency behavior was not tested. | Complete rejected-agreement editing/resubmission and expiry behavior; test overlap conditions and effective-date boundaries. |
| P1-04 | P1 | Approved supplier quotations integrated into PO pricing | The engine calls [quotation_lookup_service.py](../backend/app/application/procurement/pricing/quotation_lookup_service.py). [SupplierQuotationModel](../backend/app/infrastructure/persistence/models/quality_model.py) requires a non-null `quotation_number` and defines `unit_price`; creation routes in [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py) omit `quotation_number`. [supplier_quotation_handler.py](../backend/app/application/procurement/handlers/supplier_quotation_handler.py) reads `quoted_price` and `delivery_days`, which are not fields on that ORM model. Route code uses lowercase statuses while the domain enum/lookup expect uppercase. | BROKEN / REGRESSION DETECTED | Quote creation and submit/approve paths are incompatible with the current ORM/domain contracts. The approved-quotation fallback is not reliably reachable. | Reconcile model, route payload, handler, status values, and lookup fields. Add route-to-engine lifecycle tests. |
| P0-01 | P0 | Finance/Costing authorization, segregation of duties, direct-cost prevention | Cost approval in [handlers.py](../backend/app/application/procurement/pricing/handlers.py) checks requester/approver separation, locks revision/material rows, checks stale snapshots, updates material cost, and appends history. Ordinary material update rejects a supplied cost in [inventory_handlers.py](../backend/app/application/inventory/handlers/inventory_handlers.py). | PARTIALLY IMPLEMENTED | [procurement_pricing.py](../backend/app/interfaces/api/v1/routes/procurement_pricing.py) has no visible route-level `require_permission` checks. [rbac_audit.py](../backend/app/interfaces/api/v1/middleware/rbac_audit.py) logs 403 responses; it does not enforce permissions. The alternate [material_onboarding_service.py](../backend/app/application/inventory/services/material_onboarding_service.py) contains a direct cost assignment and appears unwired (no call sites found). | Add explicit read/write/approval permissions to pricing endpoints and verify role boundaries. Keep approved-cost changes confined to the revision workflow. Remove or make safe any reachable alternate direct-cost path in a later approved implementation. |
| P1-05 | P1 | Append-only cost history and correction/reversal | [MaterialCostHistory](../backend/app/domain/procurement/pricing/entities.py) is immutable at the domain level; repository/API paths add and read entries. | PARTIALLY IMPLEMENTED | No database-level update/delete protection or complete reversal/correction workflow was found. Reversal language appears in comments rather than a complete flow. | Record corrections as reversal entries, enforce immutability at the persistence boundary, and add tests for history integrity. |
| P0-02 | P0 | BOM missing approved cost and incomplete-cost representation | [bom_providers.py](../backend/app/infrastructure/services/bom_providers.py) only provides material cost if an approved revision exists. [cost_rollup_service.py](../backend/app/domain/bom/services/cost_rollup_service.py) records missing costs and returns `total_cost=None`, `is_complete=false`. | BROKEN / REGRESSION DETECTED | [BOMCostResponse](../backend/app/interfaces/api/v1/schemas/bom_schemas.py) requires numeric totals and omits completeness fields. [BOMCostBreakdown.tsx](../frontend/src/modules/bom/components/BOMCostBreakdown.tsx) assumes numeric totals and does not display incomplete/missing-cost status. | Make API and UI represent incomplete costs explicitly. Keep BOM preparation possible while preventing a fully-costed status when required material costs are missing. |
| P0-03 | P0 | BOM unit correctness and operation pricing | Scrap multiplier and setup/run time × workstation hourly-rate calculations remain in [cost_rollup_service.py](../backend/app/domain/bom/services/cost_rollup_service.py) and [bom_providers.py](../backend/app/infrastructure/services/bom_providers.py). | PARTIALLY IMPLEMENTED | BOM line `unit_id` is not converted before multiplying by material cost per base unit. Missing operation/workstation pricing returns zero rather than an incomplete result. No runtime calculation test was run. | Convert units before costing, represent unavailable operation costs consistently, and test scrap, setup/run time, and workstation calculations. |
| P1-06 | P1 | Six-level PO price priority and metadata | [po_pricing_engine.py](../backend/app/application/procurement/pricing/po_pricing_engine.py) implements agreement → quotation → same-supplier GRN history → any-supplier GRN history → approved standard cost → manual/no suggestion. | PARTIALLY IMPLEMENTED | Engine is isolated from the real PO create/save path. Quantity is not passed, so MOQ/tier pricing is not selected. Response omits required source date, currency, and UOM. Quote lookup is broken. | Stabilize data normalization and quote integration, pass PO quantity, and expose source metadata. |
| P1-07 | P1 | Actual PO UI integration and line-price persistence | [PurchaseOrdersPage.tsx](../frontend/src/modules/procurement/pages/PurchaseOrdersPage.tsx) submits manually entered prices (default `0`); [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py) persists submitted prices directly. | NOT IMPLEMENTED | The actual PO UI does not load or display a six-level suggestion and does not persist price-source/date/currency/UOM provenance. | Wire engine suggestions into PO create/edit and persist suggestion provenance plus actual price, preserving the existing PO workflow. |
| P1-08 | P1 | Price override persisted with PO line | Override route in [procurement_pricing.py](../backend/app/interfaces/api/v1/routes/procurement_pricing.py), [price_override_service.py](../backend/app/application/procurement/pricing/price_override_service.py), and [PriceOverrideRecordModel](../backend/app/infrastructure/persistence/models/procurement_pricing_models.py) disagree on fields. The route accesses request fields absent from its schema; the service supplies ORM attributes not present on the model. | BROKEN / REGRESSION DETECTED | The endpoint/service cannot reliably persist records, PO save does not invoke it, and frontend components call methods not exported by the service. | Define one override contract and save it transactionally with the PO line; test suggested/actual price, source, user, and optional reason. |
| P1-09 | P1 | Partial GRNs, cumulative quantity and concurrent receipts | [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py) contains a staged GRN path that checks remaining quantity at creation and a direct receive path that locks the PO and checks remaining quantity. | PARTIALLY IMPLEMENTED | Multiple pending GRNs can each pass against the same unreserved balance. Staged receipt later increments PO quantities without rechecking/locking; protection differs by path. | Revalidate cumulative accepted quantity under lock at receipt; test multiple pending and concurrent receipts. |
| P1-10 | P1 | Exact GRN-line history linkage, idempotency, rejected receipt behavior | Both receipt paths insert `supplier_price_history` without `grn_line_id`, currency, or unit. [purchase_history_query_service.py](../backend/app/application/procurement/services/purchase_history_query_service.py) labels history with tenant currency and material base UOM. [inventory.py](../backend/app/interfaces/api/v1/routes/inventory.py) exposes a tenant-scoped material purchase-history endpoint that calls this service. | PARTIALLY IMPLEMENTED | Nullable `grn_line_id` cannot ensure idempotency for these inserts. Prices can be mislabeled if PO currency/UOM differs. No standard-cost update on GRN was found, but rejected-GRN behavior was not executed. | Persist exact GRN-line linkage and normalized currency/UOM; test retries, reversals, and rejection behavior. |
| P0-04 | P0 | UOM/currency comparability and missing-rate blocking | UOM artifacts exist in [uom_conversion_model.py](../backend/app/infrastructure/persistence/models/uom_conversion_model.py), [uom_conversion.py](../backend/app/domain/inventory/entities/uom_conversion.py), and [uom_conversion_repository.py](../backend/app/infrastructure/persistence/repositories/uom_conversion_repository.py). | BROKEN / REGRESSION DETECTED | Repository mapping uses `multiply_by`, while the domain entity accepts/exposes `conversion_factor`; mapping is incompatible. No pricing conversion call sites or currency exchange-rate infrastructure were found. | Repair and test centralized UOM conversion; identify an approved currency-rate source; block price comparisons when a required conversion is unavailable. |
| P1-11 | P1 | Pricing API routing and frontend/backend contracts | [router.py](../backend/app/interfaces/api/v1/router.py) includes the pricing router; [main.py](../backend/app/main.py) mounts the API router at `/api/v1`; the pricing router itself also has `/api/v1` in its prefix. Frontend client uses `/api/v1` as its base. | BROKEN / REGRESSION DETECTED | Backend path is double-prefixed (`/api/v1/api/v1/...`) while frontend calls a single-prefix path. Further mismatches: API agreement list returns an array but UI expects a paginated object; hooks call `get`/`submit` while the service exports `getById`/`submitForApproval`; standard-cost list/body shapes differ. | Normalize the route prefix and reconcile request/response types, service exports, hooks, and page actions; validate with API contract and frontend type checks. |
| P1-12 | P1 | Migration/schema deployment consistency | An untracked Alembic migration exists at [20261110_1939_e06307f2f932_add_procurement_pricing_phase2_tables.py](../alembic/versions/20261110_1939_e06307f2f932_add_procurement_pricing_phase2_tables.py). The untracked [fix_procurement_pricing_migration.sql](../db_scripts/fix_procurement_pricing_migration.sql) adds a unique `(tenant_id, supplier_id, material_id)` constraint and omits model fields such as purchase UOM/MOQ. It also updates `operations` and commits before creating pricing tables. | PARTIALLY IMPLEMENTED | The unique constraint would prevent multiple agreement periods for the same supplier/material. Actual DB state is unknown; no SQL or migration was run. | Reconcile scripts with the model/migration through the separate database owner before use. |
| P1-13 | P1 | Test and regression evidence | Relevant tests exist: [test_material_standard_cost.py](../backend/tests/unit/inventory/test_material_standard_cost.py), [test_po_pricing_engine_six_levels.py](../tests/unit/procurement/test_po_pricing_engine_six_levels.py), [test_six_level_pricing_e2e.py](../tests/e2e/phase_2_pricing/test_six_level_pricing_e2e.py), [test_quotation_state_machine.py](../backend/app/tests/unit/test_quotation_state_machine.py), and [test_grn_flow.py](../backend/tests/api/test_grn_flow.py). | PARTIALLY IMPLEMENTED | A targeted pytest attempt stopped during conftest import with `ModuleNotFoundError: No module named 'backend'`; zero tests were collected or executed. Static inspection found test fixture/constructor names that do not match current ORM fields, including `agreed_price`, `quoted_price`, `standard_cost`, and `override_timestamp`. No test is reported as passing. | Fix test import/config and stale fixtures; run isolated unit tests first, then in-memory integration and frontend/API tests. Do not use a shared database. |

## 5. Architecture and End-to-End Workflow

### Material onboarding

The active frontend generates/downloads the onboarding template and uploads a file to the active onboarding router. The router validates and previews rows, supports row correction and confirmation, creates or updates materials, and separately creates optional supplier agreements and cost revisions. The active path initializes material cost at zero and proposes a standard cost as a pending revision rather than directly setting an approved cost.

An alternate [material_onboarding_service.py](../backend/app/application/inventory/services/material_onboarding_service.py) exists but no construction/call site was found. It contains a direct assignment to `mat.current_cost` and a call through the ordinary update handler with `current_cost`; this alternate path should not be treated as the active safe workflow.

### Supplier pricing and quotations

Supplier price agreements use a dedicated model, domain entity, repository, and application handlers. Agreements can be created, submitted, approved, activated, cancelled, and checked for overlapping effective intervals. Imported supplier prices are created as draft agreements and therefore require lifecycle progression before the active agreement lookup can select them.

Supplier quotations are maintained in a separate model and route/handler flow. The inspected field/status mismatches prevent treating this as a reliable input to PO pricing.

### Purchase order

The real PO screen sends manually entered line prices through the supply-chain API. The six-level pricing engine is a separate application service and is not connected to the real PO create/save path. Override persistence is not part of the transaction that saves PO lines.

### GRN and purchase history

There are two receiving paths: pending/staged GRNs later accepted into inventory, and direct PO receiving. They do not enforce cumulative limits in the same way. Receipt history writes do not record the exact GRN line or conversion metadata. Purchase history lookup for pricing uses GRN lines directly, while the inventory purchase-history endpoint uses a separate query service.

### Standard cost and BOM

The standard-cost revision path approves revisions and updates the material cost with history. BOM material costing queries for an approved revision before using `materials.current_cost`. The rollup preserves scrap and operation calculation code, and marks missing material/child-BOM costs incomplete, but the API schema and UI do not represent incomplete output compatibly.

## 6. Functionality to Preserve

- Standard-cost approval row locking, stale-snapshot check, and requester/approver separation.
- Tenant-scoped material, supplier, agreement, revision, and history access.
- Distinct supplier price agreement and standard-cost revision records.
- Ordinary material update’s guard against direct current-cost changes.
- Onboarding opening-stock inventory transaction behavior.
- Existing PO and GRN workflows while making their quantity checks consistent.
- BOM scrap multiplication and setup/run/workstation cost calculations.
- Soft-delete filters and audit/business-event logging already present in active flows.

## 7. Critical Gaps by Area

### Business and financial correctness

- PO pricing does not use the six-level engine in the active UI/save workflow.
- Currency and UOM values may be compared without conversion.
- Quote lifecycle contracts do not match the model and expected status values.
- GRN history lacks exact line provenance and conversion metadata.
- Incomplete BOM cost is not represented end-to-end as incomplete.
- Override records are not transactionally connected to PO-line save.

### Technical integration

- Pricing router prefix appears duplicated relative to the app mount and frontend base path.
- Frontend hooks, services, and backend response/action contracts are inconsistent.
- UOM conversion repository and domain entity disagree on attribute names.
- Test execution is blocked by conftest import configuration; stale fixture contracts were also observed.

### Security and data integrity

- Pricing endpoints have no visible route-level `require_permission` checks.
- Global 403 logging is not an authorization control.
- Domain-level cost-history immutability is not backed by a found database-level guard.
- Staged GRNs can reserve the same unreceived PO balance more than once.
- Unapplied migration/SQL scripts are not evidence of the current database schema.

## 8. Frontend and Backend Integration Gaps

- Pricing endpoints are included in the API router, but the nested prefix produces a likely double `/api/v1`.
- Agreement list response is an array while the frontend hook expects a paginated response.
- Agreement service exposes `getById` and `submitForApproval`; the hook invokes `get` and `submit`.
- UI uses a submit path that differs from the backend’s `/submit-for-approval`.
- Cost-revision list and request/approval bodies have incompatible shapes.
- PO page does not consume pricing suggestions or show source/date/currency/UOM.
- Price suggestion and override components are not part of the PO form save workflow.
- Override UI calls list/record functions not exported by its service.
- BOM cost UI and TS types assume numeric totals and omit completeness/missing costs.
- Material onboarding UI cannot correct all supplier and proposed-cost fields and does not clearly display unconfigured pricing.

## 9. Test Coverage and Validation Results

### Executed

- Targeted command: `pytest -q -p no:cacheprovider --confcutdir=backend/tests/unit/inventory backend/tests/unit/inventory/test_material_standard_cost.py`
- Outcome: **failed before collection** while loading `backend/tests/unit/inventory/conftest.py`; `ModuleNotFoundError: No module named 'backend'`.
- Tests collected: **0**.
- Tests passed: **0**.
- Tests failed at assertion/runtime level: **0**; execution did not reach test cases.

### Not run

- No integration/API/E2E test was run because no test case could be shown safe and isolated from database creation or writes under the read-only restriction.
- No tests were run against a shared database.
- No frontend test/type-check was run.
- No database schema inspection or migration command was run.

### Important missing/blocked tests

- Material import with no supplier, one supplier price, multiple suppliers, proposed standard cost, duplicate material, existing material update, row correction, and accurate outcome counts.
- Tenant isolation and authorization for agreement, revision, quotation, override, PO, and GRN endpoints.
- Initial standard cost approval, rejection, requester self-approval denial, stale revision, concurrent approvals, and direct update prevention.
- Agreement overlap/effective dates and quote approval/fallback.
- Six priority levels with quantity tiers, source metadata, missing currency rate, and missing UOM conversion.
- BOM missing cost, incomplete display, subsequent recalculation, scrap, setup/run time, and workstation rate.
- PO override persistence and correct source/user/reason.
- Partial/multiple GRNs, cumulative excess prevention, staged receipt races, rejection/resubmission, idempotency, and exact history linkage.
- Cost history update/delete prevention and correction/reversal entries.

## 10. Regression Risks

The source audit identified these concrete or likely regressions:

1. Supplier quotation route/model/handler contracts conflict, including required `quotation_number`, `unit_price` vs. `quoted_price`, and lowercase vs. uppercase status.
2. Pricing API route prefix conflicts with app mounting and frontend base URL.
3. BOM incomplete-cost return values conflict with required numeric response fields and frontend assumptions.
4. UOM conversion repository field names do not match the domain entity constructor/properties.
5. Staged and direct GRN paths have materially different cumulative receipt checks.
6. PO pricing engine and override implementation are disconnected from PO line persistence.
7. Migration SQL has a uniqueness rule inconsistent with multiple effective-period agreements and does not match model fields.

These are source-level findings, not claims that a live production deployment currently exhibits the behavior. No runtime or database was inspected.

## 11. Recommended Implementation Sequence

1. Resolve authorization and route reachability first: normalize route prefix and add explicit pricing permissions.
2. Reconcile quotation model, request schema, route, lifecycle handler, status casing, and lookup.
3. Define and test currency/UOM normalization, including an approved currency-rate source; block incomparable prices.
4. Integrate the six-level engine into PO create/edit, pass quantity, show price source/date/currency/UOM, and persist the selected source.
5. Unify override contracts and persist override records in the same PO-line save transaction.
6. Make GRN cumulative quantity validation consistent under locking; persist idempotent history tied to exact GRN lines with currency/UOM.
7. Update BOM API and frontend for incomplete costs while preserving engineering/BOM editing and existing costing formulas.
8. Complete import correction/status UX and test import combinations.
9. Reconcile migrations/SQL separately with the database owner; do not apply the inspected scripts without review.
10. Repair test configuration/fixtures, then run isolated unit tests, safe in-memory integration tests, API contract tests, and frontend checks.

## 12. Likely Files for Follow-Up Changes

| Workstream | Expected files |
|---|---|
| Pricing route permissions and prefix | [procurement_pricing.py](../backend/app/interfaces/api/v1/routes/procurement_pricing.py), [router.py](../backend/app/interfaces/api/v1/router.py), [permissions.py](../backend/app/interfaces/api/v1/dependencies/permissions.py), pricing frontend API services/hooks |
| Quotation lifecycle | [quality_model.py](../backend/app/infrastructure/persistence/models/quality_model.py), [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py), [supplier_quotation_handler.py](../backend/app/application/procurement/handlers/supplier_quotation_handler.py), [quotation_lookup_service.py](../backend/app/application/procurement/pricing/quotation_lookup_service.py) |
| Currency/UOM comparison | [uom_conversion.py](../backend/app/domain/inventory/entities/uom_conversion.py), [uom_conversion_repository.py](../backend/app/infrastructure/persistence/repositories/uom_conversion_repository.py), [po_pricing_engine.py](../backend/app/application/procurement/pricing/po_pricing_engine.py), [purchase_history_lookup_service.py](../backend/app/application/procurement/pricing/purchase_history_lookup_service.py), [any_supplier_history_lookup_service.py](../backend/app/application/procurement/pricing/any_supplier_history_lookup_service.py), BOM costing and purchase-history serializers |
| PO pricing and override | [PurchaseOrdersPage.tsx](../frontend/src/modules/procurement/pages/PurchaseOrdersPage.tsx), PO routes/models in [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py), [price_override_service.py](../backend/app/application/procurement/pricing/price_override_service.py), pricing schemas/routes, pricing UI/services |
| GRN and price history | [supply_chain.py](../backend/app/interfaces/api/v1/routes/supply_chain.py), GRN/history models and repositories, both pricing history lookups, GRN tests |
| Incomplete BOM costing | [cost_rollup_service.py](../backend/app/domain/bom/services/cost_rollup_service.py), [bom_providers.py](../backend/app/infrastructure/services/bom_providers.py), [bom_schemas.py](../backend/app/interfaces/api/v1/schemas/bom_schemas.py), [BOMCostBreakdown.tsx](../frontend/src/modules/bom/components/BOMCostBreakdown.tsx), [bom.types.ts](../frontend/src/types/bom.types.ts) |
| Import UI and validation | [material_onboarding.py](../backend/app/interfaces/api/v1/routes/material_onboarding.py), [MaterialOnboardingPage.tsx](../frontend/src/modules/inventory/pages/MaterialOnboardingPage.tsx), onboarding tests |
| Test configuration and coverage | [conftest.py](../backend/tests/conftest.py), inventory/procurement/GRN/BOM tests and fixtures |
| Database reconciliation | [20261110_1939_e06307f2f932_add_procurement_pricing_phase2_tables.py](../alembic/versions/20261110_1939_e06307f2f932_add_procurement_pricing_phase2_tables.py), [fix_procurement_pricing_migration.sql](../db_scripts/fix_procurement_pricing_migration.sql), and current ORM models — separate DB-owner review required |

## 13. Final Acceptance

The source audit is complete, but **the Procurement Pricing lifecycle is not complete or verified**. No code, schema, migration, or database change was made during the audit. The next step is implementation only after explicit approval, followed by isolated tests and regression verification.
