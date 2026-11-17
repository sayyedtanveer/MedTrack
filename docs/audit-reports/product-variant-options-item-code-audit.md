# Product variant options and ERP item-code audit

## Attribute interaction

Product Template Form uses the shared TagInput for free-text options. Its old code committed text only from the Enter or comma key handler. There is no separate attribute master in this flow. Options belong to the template, and the variant create form reads them into controlled single-selection dropdowns. Changing a selection replaces the old value in the form payload. Existing variant attributes determine SKU and uniqueness. The variant edit form edits other fields and leaves the existing combination intact.

TagInput now has a visible Add button, with Enter and comma as optional shortcuts. It trims whitespace, reports case-insensitive duplicates, updates chips immediately, and has labelled remove buttons. Template validation and variant-key validation still govern the saved records.

## Code coverage

A = ERP-generated identifier. B = user-maintained reference or configuration. C = mixed or legacy manual ownership. D = technical identifier.

| Module and endpoint | Field and classification | Existing behavior | Result and enforcement |
| --- | --- | --- | --- |
| Products → New/Edit Template, POST /products/templates | Template item_code/code, A on generated path, C on explicit legacy create | Server generates with category-based ItemCodeService when omitted. Create also accepts explicit codes. Update does not accept a code change. | Ordinary form displays a copyable saved code or “Auto-generated on save” and omits code on save. Legacy API create remains compatible. |
| Products → Variants, POST /products/templates/{id}/variants | Variant code/SKU and variant_key, A | Server derives code from the template code and ordered options. The browser used to show a guessed SKU. Variant create/update does not offer a code override. | Remove guessed code. Show generation on save and display the persisted SKU in the existing list. Variant code and template combination uniqueness remain enforced. |
| Inventory → Materials and Inventory → Products, POST/PUT /inventory/materials | Item code, A when auto-generated, C under authorized manual policy or legacy inputs | Modern Number Series config when present. Category sequence fallback otherwise. New records lock their code. Legacy create accepts explicit code. | Read-only edit display. Create reads an additive, non-seeding code-entry policy endpoint. Manual-entry options remain available when configured. A valid material type change preserves its saved identifier. Locked-code override requests still fail. |
| Settings → Business Configuration → Number Series | Prefix, separator, manual override, sequence width, B | Saved settings and preview are existing configuration tools. | Configuration is unchanged. Opening an item form does not seed config, reserve a number, or call preview. |
| Operations Master and Workstations Master | operation_code, workstation code, C/B | Operation code can be supplied or generated. Workstation code is maintained by the user. | Existing fields and APIs retained pending a decision about hybrid operation codes. |
| Customers, suppliers and their imports | Client/supplier code, C | Generated and manual paths already use policy or established references. | Preserve manual paths and existing settings. |
| Sales, Procurement, Work Orders, Subcontracting, Dispatch and Finance | Order, PO, GRN, RFQ, work order, subcontract and invoice numbers, A where internally assigned | Existing document-number generators assign internal numbers. Forms display and select records with those numbers. Supplier invoices and customer references can contain external numbers. | Display and assignment paths retained. External references remain editable. |
| Catalog and item masters | Supplier item code, customer reference, SKU/barcode alias, UOM symbol, location code and category prefix, B | User, vendor, customer, or master-data reference. | Existing entry and matching remain available. |
| Inventory and subcontract traceability | Lot and batch labels, C/B | Supplier-entered and generated labels may coexist. | Preserve lot identity and existing entry rules. |
| Links and relationships | Material, template, variant, order, tenant, and BOM UUIDs, D | Stable database identities. | Foreign keys and request IDs preserved. |
| BOMs, sales, pricing and reporting | Displayed material_code, variant code, and product_code, A/C by source | Persisted code displayed for reference and search. Existing records may have legacy code matches. | Display values and references preserved. |

## Backend and deployment boundary

The deployed schema contract in ORM models and existing migrations already defines per-tenant unique material, template and variant codes, and a per-tenant, template and variant-key unique combination. Category counters are keyed by tenant, item type and category. Number Series counters are keyed by tenant, entity type and prefix. First-use counter creation now uses the existing unique scopes with PostgreSQL conflict handling, then the existing row locks. Counter allocation still commits with the caller's save. Formats and sequence scopes stay the same.

ERP settings already support manual overrides and disabling auto-generation for materials. Existing create APIs also accept explicit codes in paths that predate that policy. Blocking every explicit create code would change an existing API contract. Before enforcing a generated-only API contract, identify authorized manual-import and client creation paths and agree on an explicit transition. Distinct legacy counter scopes can still share a rendered prefix if category configuration permits it. The existing tenant/code uniqueness constraint guards persistence. Changing how those scopes share a sequence would require a numbering-policy decision.

Raw Material Excel onboarding treats a supplied item code as a match key and checks code/name conflicts before posting. Blank values can use the established generator. Existing supplied values, duplicate handling, supplier references and Phase B Standard Cost behavior stay available. Variant imports also continue using current option validation and SKU generation. Existing codes are never bulk-converted by this change.

No migration or data rewrite is required by the implementation. The SQL paths rely on the already-defined unique scopes.



## Change evidence and checks

| File | Change |
| --- | --- |
| frontend/src/components/ui/tag-input.tsx | Visible Add button, duplicate feedback, keyboard shortcut and accessible removal |
| frontend/src/modules/products/pages/ProductTemplateFormPage.tsx | Copyable read-only item code and clearer option field |
| frontend/src/modules/products/components/VariantManager.tsx | Accessible option selector labels and server-generated SKU placeholder |
| frontend/src/modules/inventory/components/MaterialFormDrawer.tsx | Read-only saved code and policy-aware create field |
| frontend/src/modules/inventory/components/ProductFormDrawer.tsx | Same policy on the Inventory Products drawer |
| frontend/src/modules/inventory/hooks/useMaterialCodeEntry.ts | Reuses tenant settings and existing role checks in both drawers |
| frontend/src/services/number-series.service.ts | Calls the additive read-only policy route |
| backend/app/interfaces/api/v1/routes/number_series.py and schemas/number_series_schemas.py | Tenant-scoped policy read without seeding |
| backend/app/application/inventory/services/item_code_service.py | Race-safe first counter row with existing unique keys |
| backend/app/application/inventory/handlers/inventory_handlers.py | Preserve code when an otherwise-permitted material type change is saved |
| frontend/src/modules/products/__tests__/VariantAttributeOptions.test.tsx and ProductVariantHandoff.test.tsx | Free-text interaction and immediate variant selection/payload checks |
| tests/integration/test_item_code_concurrency.py | Retype and override checks, both counter scopes, and tenant isolation |

- `vitest run src/modules/products/__tests__ src/modules/bom/components/BOMCostConsistency.test.tsx src/modules/reports/__tests__ src/modules/inventory/components/MaterialSupplierPrices.test.tsx` passed 13 tests. These are browser-DOM emulation checks. A separate mobile browser session was outside the verification.
- `tsc --noEmit` and the frontend production build passed.
- `pytest --noconftest -p no:cacheprovider -q tests/integration/test_item_code_concurrency.py` passed 3 tests. The two concurrency cases used disposable PostgreSQL 17. The other case exercised the update handler without database writes.
- `pytest --noconftest -p no:cacheprovider -q tests/integration/test_subcontract_stock_integrity.py` passed 16 tests on disposable PostgreSQL 17.
- The focused pytest run for onboarding and Standard Cost integration, multi-level BOM costing, reporting contracts, variant SKU generation and sales pricing passed 131 tests.
- The separate Standard Cost property suite requires Hypothesis and was blocked at collection. No dependency was installed. No operational database writes or migrations ran.


The configured database catalog was read in a read-only transaction and confirmed all six existing constraints used in this review. No SQL migration or script is needed.

The 131-test backend run used the following targets.

```powershell
python -B -m pytest --noconftest -p no:cacheprovider -q tests/integration/test_onboarding_initial_standard_cost.py tests/integration/test_semi_finished_bom_cost.py tests/integration/test_reporting_contracts.py tests/integration/test_onboarding_template_dropdowns.py backend/tests/unit/product/test_variant_sku_generation.py backend/tests/unit/domain/sales/test_pricing_service_option_b.py
```
