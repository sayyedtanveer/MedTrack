"""Phase 1 verification script."""
import sys

errors = []

def check_file(filepath, patterns_present, patterns_absent=None):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    for p, desc in patterns_present:
        if p in content:
            print(f"OK   {filepath}: {desc}")
        else:
            errors.append(f"FAIL {filepath}: MISSING — {desc} ({repr(p)})")
            print(f"FAIL {filepath}: MISSING — {desc}")
    for p, desc in (patterns_absent or []):
        if p not in content:
            print(f"OK   {filepath}: ABSENT (good) — {desc}")
        else:
            errors.append(f"FAIL {filepath}: STILL PRESENT — {desc} ({repr(p)})")
            print(f"FAIL {filepath}: STILL PRESENT — {desc}")

# document.service.ts
check_file(
    "frontend/src/services/document.service.ts",
    [
        (".zip", "ZIP extension default in downloadDocumentPackageByUrl"),
        ("downloadDocumentPackageByUrl", "method present"),
    ],
    # The .pdf default was only on downloadDocumentPackageByUrl — verify the
    # specific old default string is gone (the WO PDF download keeping .pdf is fine)
    [("document_package_${documentId}.pdf", "old .pdf package filename removed")],
)

# technical-document.service.ts
check_file(
    "frontend/src/services/technical-document.service.ts",
    [
        ("work_order_line_id", "work_order_line_id in DocumentAssociation interface"),
        ("work_order_line", "work_order_line in target_type union"),
    ],
)

# WorkOrderDocumentsTab.tsx
check_file(
    "frontend/src/modules/work-orders/components/WorkOrderDocumentsTab.tsx",
    [
        ("documentService.generateDocument", "uses authenticated generate flow"),
        ("downloadDocumentPackageByUrl", "uses correct package download method"),
        ("packageLoading", "loading state present"),
        ("product_name", "product names shown in selector"),
        ("work_order_line", "uses correct target_type for line-specific upload"),
        ("getMappedToLabel", "proper mapped-to label resolution"),
    ],
    # The old broken URL was window.open(`/api/v1/documents/package/work-order/${id}`)
    # It now appears only in a comment (acceptable); the live call is gone
    [("window.open(`/api/v1/documents/package/work-order", "old broken window.open call removed")],
)

# Backend schemas
check_file(
    "backend/app/interfaces/api/v1/schemas/work_order_schemas.py",
    [("product_name", "product_name on WorkOrderLineResponse")],
)

check_file(
    "backend/app/interfaces/api/v1/schemas/technical_document_schemas.py",
    [
        ("work_order_line_id", "work_order_line_id in DocumentAssociationResponse"),
        ("work_order_line", "work_order_line in target_type description"),
    ],
)

# Backend services
check_file(
    "backend/app/application/documents/services/technical_document_service.py",
    [
        ("work_order_line", "work_order_line target_type handled"),
        ("_get_work_order_line", "_get_work_order_line helper exists"),
        ("work_order_line_id", "work_order_line_id set on association"),
    ],
)

# document_repository
check_file(
    "backend/app/infrastructure/persistence/repositories/document_repository.py",
    [
        ("find_by_id_and_tenant", "tenant-scoped find_by_id_and_tenant method"),
    ],
)

# documents.py routes
check_file(
    "backend/app/interfaces/api/v1/routes/documents.py",
    [
        ("find_by_id_and_tenant", "tenant check on download"),
        ("require_permission", "RBAC on endpoints"),
        ("zip_stem", "WO number filename logic"),
    ],
    [("download_target_package", "broken endpoint removed")],
)

# work_orders.py
check_file(
    "backend/app/interfaces/api/v1/routes/work_orders.py",
    [
        ("WorkOrderModel.lines", "lines loaded via selectinload"),
        ("product_name", "product names resolved for lines"),
    ],
)

# Migration
check_file(
    "alembic/versions/20260926_1200_b3f8e1a2c9d4_add_technical_documents_and_wo_line_assoc.py",
    [
        ("b3f8e1a2c9d4", "correct revision ID"),
        ("a0cbf2de5265", "correct down_revision"),
        ("work_order_line_id", "work_order_line_id column added"),
        ("show_on_wo", "show_on_wo column added"),
    ],
)

print()
if errors:
    print(f"FAILED: {len(errors)} check(s) failed:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print(f"All {sum(1 for _ in range(10))} file checks passed — Phase 1 verification OK.")
