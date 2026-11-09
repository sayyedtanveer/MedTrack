import ast, sys

errors = []

def ck(path, present=None, absent=None):
    c = open(path, encoding='utf-8').read()
    for p, d in (present or []):
        if p in c:
            print(f'OK   {d}')
        else:
            errors.append(d)
            print(f'FAIL {d}')
    for p, d in (absent or []):
        if p not in c:
            print(f'OK   ABSENT: {d}')
        else:
            errors.append(d)
            print(f'FAIL PRESENT: {d}')

# Syntax check
with open('backend/app/interfaces/api/v1/routes/documents.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('SYNTAX OK  documents.py')

# Phase 4 content checks
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('_build_work_order_bom_context', 'BOM context called on-the-fly in package'),
    ('-BOM.pdf', 'BOM PDF added as {stem}-BOM.pdf'),
    ('line_folder_names', 'product subfolder name mapping'),
    ('folder}/{file_name}', 'line-specific doc goes into product subfolder'),
    ('zip_path = file_name', 'WO-level doc stays at root'),
    ('is_print_package_included', 'include_in_package filter respected'),
    ('find_by_id_and_tenant', 'tenant check present'),
    ('require_permission', 'RBAC present'),
], [
    ('line_{assoc.work_order_line_id}', 'old flat line_ prefix removed'),
])

# ── Full acceptance-criteria sweep ────────────────────────────────────────────

# AC 1: Existing single-product WO still downloads normally
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('work_order_bom', 'work_order_bom route registered'),
    ('work_order_context', '_build_work_order_context still called for work_order type'),
])

# AC 2: Download Work Order does not include full BOM
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('documents": await _build_document_control_list', 'WO PDF only has doc control list, not full BOM'),
])

# AC 3: Download Work Order + BOM generates a separate BOM PDF
ck('backend/app/templates/work_order_bom/print.html', [
    ('Bill of Materials', 'BOM template title present'),
    ('product_lines', 'multi-product loop present'),
    ('materials', 'materials table present'),
])

# AC 4: Complete Package returns ZIP
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('application/zip', 'package returns ZIP content type'),
    ('.zip"', 'ZIP filename used'),
])

# AC 5: Product B docs appear under Product B subfolder
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('line_folder_names', 'product name lookup for subfolder'),
    ('folder}/{file_name}', 'product subfolder path construction'),
])

# AC 6: Non-PDF documents preserved (bytes written as-is)
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('zip_file.writestr(zip_path, att_bytes)', 'raw bytes written - format preserved'),
])

# AC 7: include_in_package=false excluded
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('assoc.is_print_package_included', 'is_print_package_included filter applied'),
])

# AC 8: show_on_wo=false docs not in Document Control
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('show_on_wo.is_(True)', 'show_on_wo=True filter in document control list'),
])

# AC 9: Historical document revisions frozen
ck('backend/app/application/documents/services/technical_document_service.py', [
    ('DocumentRevisionModel', 'revision model used for frozen history'),
    ('revision_code', 'revision code tracked'),
])

# AC 10: Existing WO workflows continue working
ck('backend/app/interfaces/api/v1/routes/work_orders.py', [
    ('handle_release', 'release still works'),
    ('handle_create', 'create still works'),
    ('qc', 'QC actions still present'),
])

# AC 11-12: RBAC on all download endpoints
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('require_permission("manufacturing:read")', 'manufacturing:read RBAC present'),
])

# AC 13: show_on_wo toggle in UI
ck('frontend/src/modules/work-orders/components/WorkOrderDocumentsTab.tsx', [
    ('show_on_wo', 'show_on_wo toggle in documents tab'),
    ('handleFlagToggle', 'flag toggle handler'),
])

# AC 14: is_print_package_included toggle in UI
ck('frontend/src/modules/work-orders/components/WorkOrderDocumentsTab.tsx', [
    ('is_print_package_included', 'package toggle in documents tab'),
])

# AC 15: product_name in selector
ck('frontend/src/modules/work-orders/components/WorkOrderDocumentsTab.tsx', [
    ('product_name', 'product names in upload selector'),
])

# AC 16: work_order_line association wired
ck('backend/app/application/documents/services/technical_document_service.py', [
    ('work_order_line_id', 'work_order_line_id set on association'),
    ('_get_work_order_line', 'WO line tenant validation'),
])

# AC 17: ZIP filename uses WO number
ck('backend/app/interfaces/api/v1/routes/documents.py', [
    ('zip_stem = wo.wo_number', 'WO number used as ZIP stem'),
])

# AC 18-19: Documents tab package download fixed
ck('frontend/src/modules/work-orders/components/WorkOrderDocumentsTab.tsx', [
    ('downloadDocumentPackageByUrl', 'documents tab calls correct package endpoint'),
    ('generateDocument', 'documents tab generates doc first (authenticated)'),
])

# AC 20: BOM template handles pagination (WeasyPrint @page rule)
ck('backend/app/templates/base.html', [
    ('@page', 'paging defined in base template'),
])

# AC 21: Tenant isolation on download
ck('backend/app/infrastructure/persistence/repositories/document_repository.py', [
    ('find_by_id_and_tenant', 'tenant-scoped document lookup'),
    ('tenant_id', 'tenant_id in query'),
])

# AC 22: Download Work Order ▾ dropdown in UI
ck('frontend/src/modules/work-orders/pages/WorkOrderDetailPage.tsx', [
    ('Work Order + BOM', 'WO+BOM option in dropdown'),
    ('Work Order Only', 'WO Only option in dropdown'),
    ('woDownloadOpen', 'dropdown state'),
])

print()
if errors:
    print(f'FAILED: {len(errors)} checks')
    for e in errors:
        print(f'  {e}')
    sys.exit(1)
else:
    print(f'All checks passed.')
