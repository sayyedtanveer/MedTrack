# Material onboarding Excel dropdown diagnosis

16 November 2026. Scope: template generation and its frontend availability check.

## Observed evidence

Read the user's troubleshooting transcript and inspected the actual downloaded workbooks in `C:/Users/sayye/Downloads` using openpyxl:

- `material-onboarding-template (14).xlsx` and `(13).xlsx` each have Field Guide, Quick Start and Raw Materials sheets. Raw Materials has only the Yes/No validation. Base Unit and Storage Location validations are absent.
- `(9).xlsx` contains a Storage Location validation with no formula; this does not provide a usable master list.

## Root cause

`get_template` declared `tenant_id = Depends(lambda: None)`. This always supplies `None`, regardless of the signed-in user's JWT. The `if request and tenant_id` branch therefore never fetched tenant UOMs or locations, and no corresponding validations were added. Restarting the backend alone could not fix that code.

Two additional problems were present:

1. Both master dropdown formulas joined values into malformed quoted inline lists. Inline lists also cannot safely handle Excel's 255-character formula limit or commas/quotes in values.
2. Failed master reads were converted to empty lists; failed Excel generation silently fell back to CSV. Both could return a successful download without usable dropdowns.

The worksheet variable already points to Raw Materials. The sheet assignment was correct. `data_only=True` does not strip validations: the new regression test saves the generated file, reloads it with that option, and verifies both lists.

## Correction

- Use the existing JWT tenant dependency on the template endpoint.
- Keep active/nondeleted tenant filtering for both master queries.
- Store master values as strings on a hidden `_Master Data` sheet; use workbook named ranges for validations on Raw Materials, Base Unit column D and Storage Location column F, rows 2–1048576. The original three tabs remain visible.
- Set `showDropDown=False` explicitly; Excel interprets True as hiding the arrow.
- Preserve the default location in the sample row.
- Return HTTP 503 on master-query or Excel-generation failures rather than silently returning a degraded download.
- Use the authenticated frontend API client for the availability probe, consistent with the actual download.

Tenants with genuinely empty master tables still have no corresponding dropdown options; no data is borrowed from another tenant. CSV does not support dropdowns.

## Changed files for this correction

- `backend/app/interfaces/api/v1/routes/material_onboarding.py`
- `frontend/src/modules/inventory/services/materialOnboardingApi.ts`
- `tests/integration/test_onboarding_template_dropdowns.py`
- `frontend/src/modules/inventory/__tests__/materialOnboardingApi.test.ts`
- This report.

The first two files already contained prior work. Changes were reviewed against copies saved immediately before this correction. No index staging, database writes, migrations, SQL execution or BOM-cost changes were performed.

## Verification

- **81 backend tests passed:** 6 new template regressions, 40 Phase B onboarding regressions, 35 Phase C BOM regressions. Isolated SQLite databases; no configured development database used.
- **9 frontend tests passed:** 2 availability-probe tests, 4 supplier-price/Standard Cost tests, 3 BOM consistency tests.
- TypeScript still reports **42 pre-existing errors**, with diagnostics identical to the saved Phase C baseline; no new diagnostics.
- Template checks include authenticated HTTP routing, anonymous 401, tenant isolation, inactive/deleted exclusion, punctuation and lists over 255 characters, named-range values, correct visible sheets, default location, re-import sheet selection, and failure responses.
- Desktop Excel/WPS interaction and a fresh download from the user's running application have not been verified. Existing downloaded workbooks are unchanged. Apply/reload the backend and download a new Excel template while signed in; select D2 or F2 on Raw Materials to inspect the arrow.

## Supplier field extension — 16 November 2026

Reviewed the supplier model before implementing. `SupplierModel` has a name and supplier identifier but no currency default, purchase UOM default, or material catalogue. `SupplierPriceHistoryModel.currency_code` describes past purchases; it is not a supplier master default. `MaterialModel.supplier_item_code` is material metadata, not the supplier's own code.

| Column | Implemented behavior |
|---|---|
| Supplier Name | Dropdown of this tenant's active, nondeleted supplier names. Manual names remain allowed to preserve existing supplier creation during onboarding. |
| Supplier Currency | Suggested dropdown using the existing company-settings currency choices plus the configured tenant currency. Other uppercase three-letter codes remain allowed, consistent with existing import validation. |
| Supplier UOM | Dropdown from this tenant's active, nondeleted UOM master. No automatic conversion or assumption that the quote uses the base unit. |
| Supplier Item Code | Manual supplier catalogue code for the material. A dropdown from supplier identifiers would be incorrect. |

Quote cells remain blank until filled by the user; selecting a supplier does not invent currency, UOM, price, or catalogue defaults. No supplier-dependent Excel formulas or macros were added. The three visible tabs and previous Base Unit / Storage Location validations remain intact. The Field Guide explains these choices.

Review also exposed an existing omission: Supplier Item Code was mapped from Excel but not persisted by the active importer. The importer now saves it on material creation and updates it when a nonblank value is supplied. Blank values preserve the existing value. Values over the model's 120-character limit are rejected before writing. This remains the existing single material field; it does not introduce a separate catalogue for every supplier/material pair.

Changes for this extension only:

- `backend/app/interfaces/api/v1/routes/material_onboarding.py`
- `tests/integration/test_onboarding_template_dropdowns.py`
- `tests/integration/test_onboarding_initial_standard_cost.py`
- This report.

Verification: **84 backend tests passed** (6 template, 43 onboarding, 35 BOM); **9 frontend tests passed** (2 template availability, 4 Buy/Standard Cost, 3 BOM). The generated-template regression selects actual named-range values, uploads that workbook, previews with rollback, then executes: existing supplier reused, quote price **500**, explicit material Standard Cost **400**, catalogue code **CAT-ROD** saved. Additional checks cover inactive/deleted/other-tenant suppliers, punctuation, custom tenant currency, manual item-code updates and blank preservation, and oversized item-code rejection. No frontend source changed in this extension, so the preceding TypeScript comparison remains applicable.

No schema changes, migrations, SQL execution, configured database writes, staging or commits. Desktop Excel/WPS visual interaction remains unverified; download a fresh workbook after applying the backend changes.
