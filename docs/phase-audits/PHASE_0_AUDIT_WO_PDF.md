# PHASE 0 — READ-ONLY AUDIT: WORK ORDER PDF, BOM PDF & DOCUMENT PACKAGE

## A. Current Architecture
**Work Order PDF Flow:**
`WorkOrderModel` stores snapshots of required materials (`WorkOrderMaterialModel`) and operations (`JobCardModel`). It links to a single `ItemVariantModel` (no multi-product Work Orders).
When generating a document, `DocumentGenerationService` calls `_build_work_order_context` to fetch the WO and its snapshotted materials. It then renders `backend/app/templates/work_order/print.html` with Jinja2, generates a PDF using WeasyPrint, and persists the PDF via `DocumentStorageService` into Cloudinary/Local storage. It logs versions in `DocumentRepository`.

**Document Package Architecture:**
`TechnicalDocumentModel` stores document metadata. Revisions are tracked in `DocumentRevisionModel` with Cloudinary attachments (`FileAttachmentModel`).
`DocumentAssociationModel` maps revisions directly to `work_order_id` (or variant/template). Crucially, this model includes the `is_print_package_included` flag which dictates whether the document should be bundled in the package.

## B. Current UI
The `WorkOrderDetailPage.tsx` component provides three relevant header actions:
| Action | Exists? | Current API | Current Output | Current Contents | Issues |
| --- | --- | --- | --- | --- | --- |
| **Download PDF** | Yes | `POST /documents/work_order/{id}/generate` followed by download | WO PDF | Header, BOM snapshot, Job Cards, Signatures | Forces the BOM into the main document. If the BOM is huge, the WO PDF becomes bloated. |
| **Print** | Yes | `POST /documents/work_order/{id}/generate` followed by preview | WO PDF in new tab | Same as above | Same as above |
| **Download Package** | Yes | `generate` then `GET /documents/{doc_id}/download-package` | Merged PDF | WO PDF + Technical Documents | Merges the bloated WO PDF with technical documents based on `is_print_package_included`. |
| **Download Work Order + BOM** | No | N/A | N/A | N/A | Missing entirely. |

## C. Current Download Package
The "Download Package" functionality is fully implemented on the backend.
**What it does:**
1. It fetches the primary generated WO document PDF.
2. Queries `TechnicalDocumentService` for all `DocumentAssociationModel` records linked to the Work Order where `is_print_package_included == True`.
3. Downloads the attachment bytes from Cloudinary for those specific revisions.
4. Uses `pypdf` via `DocumentGenerationService.generate_document_package()` to merge the base Work Order PDF and the technical drawing PDFs into a single file.

## D. Gaps
* **Incorrect:** The standard Work Order PDF rigidly includes the full BOM. The template (`work_order/print.html`) iterates over all `materials` indiscriminately.
* **Missing:** There is no separation between "Work Order PDF" (operational only) and "BOM PDF".
* **Missing:** Frontend lacks the "Download Work Order + BOM" button.
* **Needs Modification:** The API and context builder need a mechanism (like `?include_bom=true`) to control whether the BOM is passed to the template or if a separate BOM template should be used.

## E. Recommended Architecture
The existing architecture is robust. We will extend it minimally rather than replacing it:
1. **Download Work Order**: Modify `_build_work_order_context` and `work_order/print.html` to accept a parameter (e.g., `include_bom=False`). The standard WO will display operations and signatures, but hide the Materials table.
2. **Download Work Order + BOM**: The API will generate the Work Order PDF with `include_bom=True`. Large BOMs will be handled cleanly via CSS `page-break` rules and repeating `<thead>` tags in `print.html`.
3. **Download Package**: The existing backend logic is perfect. It will continue merging the WO PDF with the `is_print_package_included` documents.

## F. Proposed API Changes
* **`POST /documents/{document_type}/{entity_id}/generate`**: Add an optional query parameter `?include_bom=false` (default: false for standard WO). This ensures the generated version either contains or omits the BOM.

## G. Proposed Frontend Changes
* **`WorkOrderDetailPage.tsx`**: 
  - Change "Download PDF" to "Download Work Order" (calls API with `include_bom=false`).
  - Add new button: "Download Work Order + BOM" (calls API with `include_bom=true`).
  - "Print" will print the standard Work Order (no BOM).
  - "Download Package" will generate the WO (no BOM) and merge attachments.

## H. Proposed Database Changes
* **None.** The existing schema fully supports snapshots, historical revisions, package inclusion flags, and traceability.

## I. PDF Contents
* **Work Order PDF**: Header (WO#, Product, Qty, Dates), Operations (Job Cards), Signatures.
* **Work Order + BOM PDF**: Header, Operations, Signatures, **AND** the Materials table (Component Code, Name, Required Qty, Issued Qty, UOM).
* **Download Package**: Work Order PDF (no BOM) appended with all technical documents flagged with `is_print_package_included`.

## J. Implementation Phases
* **PHASE 1 — Template & Context Update**: Modify `_build_work_order_context` to accept the `include_bom` flag and update `work_order/print.html` to hide the materials table when false. Ensure the materials table uses `page-break-inside: avoid` and repeating headers for large BOMs.
* **PHASE 2 — API Extension**: Update the `documents.py` generation endpoints to accept and pass the `include_bom` query parameter through to the context builder.
* **PHASE 3 — Frontend UI Update**: Add the new "Download Work Order + BOM" button to `WorkOrderDetailPage.tsx` and adjust the existing buttons to pass the correct flags.
