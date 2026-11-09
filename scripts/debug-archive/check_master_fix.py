"""Master fix verification script — checks all files changed in this session."""
import ast, sys

errors = []

def syntax(path):
    with open(path, encoding="utf-8") as f:
        ast.parse(f.read())
    print(f"SYNTAX OK  {path}")

def check(path, present=None, absent=None):
    with open(path, encoding="utf-8") as f:
        c = f.read()
    for p, d in (present or []):
        if p in c:
            print(f"OK   {d}")
        else:
            errors.append(f"MISSING in {path}: {d}")
            print(f"FAIL {d}")
    for p, d in (absent or []):
        if p not in c:
            print(f"OK   ABSENT: {d}")
        else:
            errors.append(f"STILL PRESENT in {path}: {d}")
            print(f"FAIL STILL PRESENT: {d}")

# ── Syntax checks ─────────────────────────────────────────────────────────────
print("=== SYNTAX ===")
for f in [
    "backend/app/infrastructure/persistence/models/technical_document_model.py",
    "backend/app/infrastructure/persistence/models/work_order_model.py",
    "backend/app/application/manufacturing/commands/work_order_commands.py",
    "backend/app/application/manufacturing/handlers/work_order_handler.py",
    "backend/app/application/documents/services/technical_document_service.py",
    "backend/app/interfaces/api/v1/routes/work_orders.py",
    "backend/app/interfaces/api/v1/routes/documents.py",
    "alembic/versions/20260926_1400_c5d9f2b1e8a3_add_work_order_lines_table.py",
]:
    syntax(f)

# ── Content checks ────────────────────────────────────────────────────────────
print("\n=== CONTENT ===")

# 1. DocumentAssociationModel now has both columns
check("backend/app/infrastructure/persistence/models/technical_document_model.py", [
    ("work_order_line_id", "DocumentAssociationModel has work_order_line_id column"),
    ("show_on_wo", "DocumentAssociationModel has show_on_wo column"),
    ('ForeignKey("work_order_lines.id"', "work_order_line_id FK → work_order_lines"),
])

# 2. WorkOrderLineModel defined
check("backend/app/infrastructure/persistence/models/work_order_model.py", [
    ("class WorkOrderLineModel", "WorkOrderLineModel class defined"),
    ('__tablename__ = "work_order_lines"', "work_order_lines tablename"),
    ("lines: Mapped[list", "WorkOrderModel.lines relationship"),
    ("back_populates=\"lines\"", "WorkOrderLineModel back-reference to lines"),
    # Materials and job_cards now have work_order_line_id
    ("work_order_line_id", "work_order_line_id on WorkOrderMaterialModel and/or JobCardModel"),
])

# 3. Migration
check("alembic/versions/20260926_1400_c5d9f2b1e8a3_add_work_order_lines_table.py", [
    ("c5d9f2b1e8a3", "correct revision ID"),
    ("b3f8e1a2c9d4", "correct down_revision"),
    ("work_order_lines", "creates work_order_lines table"),
    ("gen_random_uuid", "backfills existing WOs"),
    ("work_order_materials", "adds work_order_line_id to materials"),
    ("job_cards", "adds work_order_line_id to job_cards"),
    ("_table_exists", "idempotent guard"),
    ("_column_exists", "column idempotent guard"),
])

# 4. CreateWorkOrderCommand accepts lines
check("backend/app/application/manufacturing/commands/work_order_commands.py", [
    ("class WorkOrderLineCommand", "WorkOrderLineCommand model defined"),
    ("lines: Optional[List[WorkOrderLineCommand]]", "lines field on CreateWorkOrderCommand"),
    ("product_id: Optional[uuid.UUID] = None", "product_id now Optional"),
    ("has_lines", "cross-field validator checks lines or single-product"),
])

# 5. handle_create processes lines
check("backend/app/application/manufacturing/handlers/work_order_handler.py", [
    ("WorkOrderLineModel", "WorkOrderLineModel used in handler"),
    ("line_specs", "line_specs normalisation logic"),
    ("work_order_line_id=wol.id", "materials and job_cards get work_order_line_id"),
    ("for product_id, bom_id, planned_quantity in line_specs", "per-line BOM snapshot loop"),
])

# 6. technical_document_service top-level imports
check("backend/app/application/documents/services/technical_document_service.py", [
    ("from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderLineModel, WorkOrderModel",
     "WorkOrderLineModel and WorkOrderModel top-level import"),
    ("select(WorkOrderLineModel)", "_get_work_order_line uses WorkOrderLineModel"),
])
check("backend/app/application/documents/services/technical_document_service.py",
    absent=[("from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel\n",
             "redundant inline WorkOrderModel import removed from _get_work_order_line")]
)

# 7. documents.py — show_on_wo filter, WorkOrderLineModel imports still inline (OK)
check("backend/app/interfaces/api/v1/routes/documents.py", [
    ("show_on_wo.is_(True)", "show_on_wo=True filter in document control list"),
    ("WorkOrderLineModel", "WorkOrderLineModel imported/used in documents.py"),
    ("-BOM.pdf", "BOM PDF added to ZIP"),
    ("zip_stem = wo.wo_number", "WO number in ZIP filename"),
    ("require_permission", "RBAC on endpoints"),
])

# 8. Work order route uses selectinload for lines
check("backend/app/interfaces/api/v1/routes/work_orders.py", [
    ("selectinload(WorkOrderModel.lines)", "lines selectinloaded in get_work_order"),
    ("product_name", "product_name resolved for lines"),
    ("lines_with_names", "lines_with_names passed to wo_dict"),
])

print()
if errors:
    print(f"FAILED: {len(errors)} check(s):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print(f"All checks passed.")
