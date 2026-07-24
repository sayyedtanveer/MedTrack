from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from difflib import SequenceMatcher
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.inventory.commands.inventory_commands import CreateMaterialCommand, UpdateMaterialCommand
from backend.app.application.inventory.handlers.inventory_handlers import CreateMaterialHandler, UpdateMaterialHandler
from backend.app.application.inventory.services.item_code_service import ItemCodeService
from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.material_onboarding_model import (
    MaterialImportMappingModel, MaterialOnboardingProfileModel, MaterialOnboardingRowModel,
    MaterialOnboardingSessionModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.unit_of_measure_model import UnitOfMeasureModel
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

FIELDS = [
    "item_code", "material_name", "material_category", "material_type", "uom",
    "batch_tracking_enabled", "shelf_life", "expiry_tracking", "warehouse", "zone", "rack_bin",
    "min_stock", "max_stock", "reorder_level", "reorder_quantity", "barcode", "traceability_enabled",
    "qc_required", "approved_supplier", "supplier_item_code", "purchase_uom", "lead_time", "moq",
    "length_uom", "cuttable_inventory", "remaining_quantity_tracking", "decimal_precision", "reusable_remainder",
    "opening_stock", "standard_cost",
]
ALIASES = {"material code": "item_code", "code": "item_code", "item code": "item_code", "name": "material_name",
           "material": "material_name", "material name": "material_name", "category": "material_category",
           "unit": "uom", "uom": "uom", "batch tracked": "batch_tracking_enabled", "supplier": "approved_supplier",
           "supplier code": "approved_supplier", "bin": "rack_bin", "rack/bin": "rack_bin",
           "standard purchase cost": "standard_cost", "purchase cost": "standard_cost", "cost": "standard_cost",
           "current cost": "standard_cost"}

def jload(v, default):
    try: return json.loads(v or "")
    except Exception: return default
def norm(v): return " ".join(str(v or "").strip().lower().replace("_", " ").split())
def as_bool(v): return str(v or "").strip().lower() in {"1","true","yes","y","enabled"}
def optional_bool(v):
    return None if clean(v) is None else as_bool(v)
def clean(v):
    if v is None: return None
    text = str(v).strip()
    return text if text != "" else None
def parse_int(v, field, issues, minimum=None, maximum=None):
    v = clean(v)
    if v is None: return None
    try:
        n = int(v)
        if minimum is not None and n < minimum: raise ValueError
        if maximum is not None and n > maximum: raise ValueError
        return n
    except ValueError:
        msg = f"{field.replace('_',' ').title()} must be an integer"
        if minimum is not None and maximum is not None: msg += f" from {minimum} to {maximum}"
        issues.append({"field":field,"severity":"error","type":"invalid_number","message":msg})
        return None
def parse_decimal(v, field, issues, minimum=None):
    v = clean(v)
    if v is None: return None
    try:
        n = Decimal(str(v))
        if minimum is not None and n < Decimal(str(minimum)): raise ValueError
        return n
    except Exception:
        issues.append({"field":field,"severity":"error","type":"invalid_number","message":f"{field.replace('_',' ').title()} must be a number"})
        return None

class MaterialOnboardingService:
    def __init__(self, session: AsyncSession): self.session = session
    @staticmethod
    def suggest_mapping(headers):
        out={}
        for h in headers:
            key=norm(h)
            if key in ALIASES: out[h]=ALIASES[key]; continue
            best=max(FIELDS,key=lambda f:SequenceMatcher(None,key,f.replace("_"," ")).ratio())
            if SequenceMatcher(None,key,best.replace("_"," ")).ratio()>=.72: out[h]=best
        return out
    @staticmethod
    def template_csv():
        b=io.StringIO(); w=csv.writer(b); w.writerow(FIELDS); return b.getvalue().encode()
    @staticmethod
    def template_xlsx():
        def col(n):
            s=""
            while n:
                n, rem = divmod(n - 1, 26)
                s = chr(65 + rem) + s
            return s
        cells="".join(f'<c r="{col(i+1)}1" t="inlineStr"><is><t>{v}</t></is></c>' for i,v in enumerate(FIELDS))
        sheet=f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">{cells}</row></sheetData></worksheet>'
        ct='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'
        rel='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        wb='<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Raw Materials" sheetId="1" r:id="rId1"/></sheets></workbook>'
        wbr='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        o=io.BytesIO()
        with zipfile.ZipFile(o,"w") as z:
            z.writestr("[Content_Types].xml",ct); z.writestr("_rels/.rels",rel); z.writestr("xl/workbook.xml",wb); z.writestr("xl/_rels/workbook.xml.rels",wbr); z.writestr("xl/worksheets/sheet1.xml",sheet)
        return o.getvalue()
    async def create_session(self, tenant_id, user_id, filename, content):
        if not filename:
            raise ValueError("Upload file must have a filename")
        if not filename.lower().endswith((".csv",".xlsx")):
            raise ValueError("Only CSV and XLSX files are supported")
        if filename.lower().endswith(".xlsx"):
            rows = self._read_xlsx(content)
        else:
            try:
                rows=list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            except UnicodeDecodeError as exc:
                raise ValueError("CSV file must be UTF-8 encoded") from exc
        rows=[{k: clean(v) for k,v in r.items() if k is not None} for r in rows]
        if not rows:
            raise ValueError("Upload file has no data rows")
        headers=list(rows[0].keys()) if rows else []
        if not headers:
            raise ValueError("Upload file has no header row")
        s=MaterialOnboardingSessionModel(tenant_id=tenant_id, uploaded_by=user_id, filename=filename, original_headers_json=json.dumps(headers), mapping_json=json.dumps(self.suggest_mapping(headers)))
        self.session.add(s); await self.session.flush()
        for i,r in enumerate(rows,2): self.session.add(MaterialOnboardingRowModel(session_id=s.id, tenant_id=tenant_id, row_number=i, raw_json=json.dumps(r)))
        await self.session.commit(); return s
    @staticmethod
    def _read_xlsx(content: bytes):
        from xml.etree import ElementTree as ET
        def cell_index(ref: str) -> int:
            letters = "".join(ch for ch in ref if ch.isalpha())
            n = 0
            for ch in letters:
                n = n * 26 + ord(ch.upper()) - 64
            return max(n - 1, 0)
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            shared=[]
            if "xl/sharedStrings.xml" in z.namelist():
                root=ET.fromstring(z.read("xl/sharedStrings.xml"))
                shared=["".join(n.itertext()) for n in root]
            root=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        matrix=[]
        for row in root.iter(f"{ns}row"):
            vals=[]
            for cell in row.iter(f"{ns}c"):
                idx = cell_index(cell.attrib.get("r", ""))
                while len(vals) < idx:
                    vals.append("")
                text=""
                if cell.attrib.get("t")=="inlineStr":
                    text="".join(cell.itertext())
                else:
                    v=cell.find(f"{ns}v")
                    text=v.text if v is not None and v.text is not None else ""
                    if cell.attrib.get("t")=="s" and text:
                        text=shared[int(text)]
                vals.append(text)
            matrix.append(vals)
        if not matrix: return []
        headers=matrix[0]
        return [dict(zip(headers, r + [""] * max(0, len(headers)-len(r)))) for r in matrix[1:]]
    async def list_mappings(self,tenant_id): return (await self.session.execute(select(MaterialImportMappingModel).where(MaterialImportMappingModel.tenant_id==tenant_id))).scalars().all()
    async def save_mapping(self,tenant_id,name,mapping):
        m=MaterialImportMappingModel(tenant_id=tenant_id,name=name,mapping_json=json.dumps(mapping)); self.session.add(m); await self.session.commit(); return m
    async def list_profiles(self,tenant_id): return (await self.session.execute(select(MaterialOnboardingProfileModel).where(MaterialOnboardingProfileModel.tenant_id==tenant_id,MaterialOnboardingProfileModel.is_active.is_(True)))).scalars().all()
    async def save_profile(self,tenant_id,name,defaults):
        p=MaterialOnboardingProfileModel(tenant_id=tenant_id,name=name,defaults_json=json.dumps(defaults)); self.session.add(p); await self.session.commit(); return p
    async def validate(self, session_id, tenant_id, mapping):
        s=await self.session.get(MaterialOnboardingSessionModel,session_id)
        if s is None or s.tenant_id != tenant_id: raise ValueError("Import session not found")
        mapping={src:target for src,target in mapping.items() if target in FIELDS}
        if not mapping:
            raise ValueError("Map at least one upload column before validation")
        rows=(await self.session.execute(select(MaterialOnboardingRowModel).where(MaterialOnboardingRowModel.session_id==session_id).order_by(MaterialOnboardingRowModel.row_number))).scalars().all()
        counts={k:0 for k in ["create","update","exact_duplicate","probable_duplicate","conflict","invalid"]}; protected=0
        for r in rows:
            data={target:jload(r.raw_json,{}).get(src) for src,target in mapping.items()}
            data.setdefault("material_type","raw")
            for k in ["cuttable_inventory","remaining_quantity_tracking","reusable_remainder"]:
                if data.get("length_uom") and not data.get(k): data[k]="yes"
            issues,cls,changes=await self._validate_row(tenant_id,data)
            r.normalized_json=json.dumps(data); r.validation_json=json.dumps(issues); r.protected_changes_json=json.dumps(changes)
            r.classification="invalid" if any(x["severity"]=="error" for x in issues) else cls; r.status="VALIDATED"
            counts[r.classification]+=1; protected+=len(changes)
        s.mapping_json=json.dumps(mapping); s.status="VALIDATED"; s.summary_json=json.dumps({**counts,"protected_changes":protected}); await self.session.commit(); return jload(s.summary_json,{})
    async def _validate_row(self,tenant_id,data):
        issues=[]
        for k,v in list(data.items()):
            data[k]=clean(v)
        for f in ["material_name","material_category","uom"]:
            if not data.get(f): issues.append({"field":f,"severity":"error","type":"required","message":f"{f.replace('_',' ').title()} is required"})
        cat=await self.session.scalar(select(MaterialCategoryModel).where(MaterialCategoryModel.tenant_id==tenant_id,func.lower(MaterialCategoryModel.name)==norm(data.get("material_category"))))
        unit=await self.session.scalar(select(UnitOfMeasureModel).where(UnitOfMeasureModel.tenant_id==tenant_id,func.lower(UnitOfMeasureModel.code)==norm(data.get("uom"))))
        if data.get("material_category") and not cat: issues.append({"field":"material_category","severity":"error","type":"invalid_category","message":"Category must already exist"})
        if data.get("uom") and not unit: issues.append({"field":"uom","severity":"error","type":"invalid_uom","message":"UOM must already exist"})
        if data.get("approved_supplier") and not await self.session.scalar(select(SupplierModel).where(SupplierModel.tenant_id==tenant_id,func.lower(SupplierModel.code)==norm(data["approved_supplier"]))):
            issues.append({"field":"approved_supplier","severity":"error","type":"invalid_supplier","message":"Supplier must already exist"})
        location_name=data.get("rack_bin") or data.get("zone") or data.get("warehouse")
        if location_name and not await self.session.scalar(select(LocationModel).where(LocationModel.tenant_id==tenant_id,LocationModel.is_deleted.is_(False),func.lower(LocationModel.name)==norm(location_name))):
            issues.append({"field":"rack_bin","severity":"error","type":"invalid_location","message":"Warehouse, zone, or rack/bin must already exist as a location"})
        precision=parse_int(data.get("decimal_precision"),"decimal_precision",issues,0,6)
        parse_int(data.get("shelf_life"),"shelf_life",issues,0)
        parse_int(data.get("lead_time"),"lead_time",issues,0)
        for f in ["min_stock","max_stock","reorder_level","reorder_quantity","moq"]:
            parse_decimal(data.get(f),f,issues,0)
        # Opening stock validation: numeric, >= 0, max 999,999,999.99
        _opening = parse_decimal(data.get("opening_stock"), "opening_stock", issues, 0)
        if _opening is not None and _opening > Decimal("999999999.99"):
            issues.append({"field": "opening_stock", "severity": "error", "type": "invalid_number", "message": "Opening Stock must not exceed 999,999,999.99"})
        # Standard cost validation: numeric, >= 0, max 999,999,999.9999
        _std_cost = parse_decimal(data.get("standard_cost"), "standard_cost", issues, 0)
        if _std_cost is not None and _std_cost > Decimal("999999999.9999"):
            issues.append({"field": "standard_cost", "severity": "error", "type": "invalid_number", "message": "Standard Cost must not exceed 999,999,999.9999"})
        exact=await self.session.scalar(select(MaterialModel).where(MaterialModel.tenant_id==tenant_id,func.upper(MaterialModel.code)==str(data.get("item_code") or "").upper(),MaterialModel.is_deleted.is_(False))) if data.get("item_code") else None
        barcode=await self.session.scalar(select(MaterialModel).where(MaterialModel.tenant_id==tenant_id,MaterialModel.barcode==data["barcode"],MaterialModel.is_deleted.is_(False))) if data.get("barcode") else None
        supplier=await self.session.scalar(select(MaterialModel).where(MaterialModel.tenant_id==tenant_id,MaterialModel.supplier_item_code==data["supplier_item_code"],MaterialModel.is_deleted.is_(False))) if data.get("supplier_item_code") else None
        same=await self.session.scalar(select(MaterialModel).where(MaterialModel.tenant_id==tenant_id,func.lower(MaterialModel.name)==norm(data.get("material_name")),MaterialModel.is_deleted.is_(False))) if data.get("material_name") else None
        ids={m.id for m in [exact,barcode,supplier,same] if m}
        if len(ids)>1: issues.append({"field":"duplicate","severity":"error","type":"conflict","message":"Identifiers match different materials"}); return issues,"conflict",[]
        mat=exact or barcode or supplier or same
        cls="update" if exact else ("probable_duplicate" if mat else "create")
        if mat and not exact: issues.append({"field":"duplicate","severity":"warning","type":"probable_duplicate","message":"Possible existing material; review before import"})
        changes=[]
        if mat:
            checks={"item_code":mat.code,"material_type":mat.material_type,"uom":str(mat.base_unit_id or ""),"batch_tracking_enabled":mat.is_batch_tracked,"traceability_enabled":mat.traceability_enabled,"decimal_precision":mat.decimal_precision}
            requested={"item_code":data.get("item_code"),"material_type":data.get("material_type"),"uom":str(unit.id) if unit else "","batch_tracking_enabled":optional_bool(data.get("batch_tracking_enabled")),"traceability_enabled":optional_bool(data.get("traceability_enabled")),"decimal_precision":precision}
            changes=[{"field":f,"from":str(v),"to":str(requested[f])} for f,v in checks.items() if requested.get(f) not in (None,"") and requested.get(f)!=v]
        if exact and exact.name == data.get("material_name") and str(exact.material_type) == str(data.get("material_type") or "raw") and not changes:
            cls="exact_duplicate"
        return issues,cls,changes
    async def preview(self,session_id, tenant_id):
        s=await self.session.get(MaterialOnboardingSessionModel,session_id)
        if s is None or s.tenant_id != tenant_id: raise ValueError("Import session not found")
        rows=(await self.session.execute(select(MaterialOnboardingRowModel).where(MaterialOnboardingRowModel.session_id==session_id).order_by(MaterialOnboardingRowModel.row_number))).scalars().all()
        return {"summary":jload(s.summary_json,{}),"rows":[{"id":str(r.id),"row_number":r.row_number,"classification":r.classification,"status":r.status,"data":jload(r.normalized_json,{}),"issues":jload(r.validation_json,[]),"protected_changes":jload(r.protected_changes_json,[])} for r in rows]}
    async def confirm_protected(self,session_id, tenant_id):
        s=await self.session.get(MaterialOnboardingSessionModel,session_id)
        if s is None or s.tenant_id != tenant_id: raise ValueError("Import session not found")
        s.protected_changes_confirmed=True; await self.session.commit()
    async def update_row(self, row_id, tenant_id, data):
        row=await self.session.get(MaterialOnboardingRowModel,row_id)
        if row is None or row.tenant_id != tenant_id: raise ValueError("Import row not found")
        merged={**jload(row.normalized_json,{}), **data}
        issues,cls,changes=await self._validate_row(tenant_id, merged)
        row.normalized_json=json.dumps(merged); row.validation_json=json.dumps(issues); row.protected_changes_json=json.dumps(changes)
        row.classification="invalid" if any(x["severity"]=="error" for x in issues) else cls; row.status="CORRECTED"
        await self.session.flush()
        await self._refresh_summary(row.session_id, tenant_id)
        await self.session.commit()
        return {"classification":row.classification,"issues":issues,"protected_changes":changes}
    async def _refresh_summary(self, session_id, tenant_id):
        s=await self.session.get(MaterialOnboardingSessionModel,session_id)
        if s is None or s.tenant_id != tenant_id: raise ValueError("Import session not found")
        rows=(await self.session.execute(select(MaterialOnboardingRowModel).where(MaterialOnboardingRowModel.session_id==session_id))).scalars().all()
        counts={k:0 for k in ["create","update","exact_duplicate","probable_duplicate","conflict","invalid"]}
        protected=0
        for r in rows:
            if r.classification in counts: counts[r.classification]+=1
            protected+=len(jload(r.protected_changes_json,[]))
        s.summary_json=json.dumps({**counts,"protected_changes":protected})
    async def report_csv(self, session_id, tenant_id):
        preview=await self.preview(session_id, tenant_id)
        b=io.StringIO(); w=csv.writer(b); w.writerow(["row_number","classification","status","issues"])
        for r in preview["rows"]: w.writerow([r["row_number"], r["classification"], r["status"], "; ".join(i["message"] for i in r["issues"])])
        return b.getvalue().encode()
    async def execute(self,session_id,tenant_id,user_id,dry_run=False):
        s=await self.session.get(MaterialOnboardingSessionModel,session_id)
        if s is None or s.tenant_id != tenant_id: raise ValueError("Import session not found")
        if s.status not in {"VALIDATED","DRY_RUN_COMPLETE"}:
            raise ValueError("Validate the upload before executing")
        rows=(await self.session.execute(select(MaterialOnboardingRowModel).where(MaterialOnboardingRowModel.session_id==session_id).order_by(MaterialOnboardingRowModel.row_number))).scalars().all()
        if any(jload(r.protected_changes_json,[]) for r in rows) and not dry_run and not s.protected_changes_confirmed: raise ValueError("Protected field changes require explicit confirmation")
        if dry_run: s.status="DRY_RUN_COMPLETE"; s.dry_run=True; await self.session.commit(); return jload(s.summary_json,{})
        counts={"created":0,"updated":0,"skipped":0,"failed":0}
        for r in rows:
            if r.classification in {"invalid","conflict","exact_duplicate","probable_duplicate"}: r.status="SKIPPED"; counts["skipped"]+=1; continue
            try:
                await self._apply_row(tenant_id,user_id,r); counts["updated" if r.classification=="update" else "created"]+=1
            except Exception as exc:
                await self.session.rollback(); r=await self.session.get(MaterialOnboardingRowModel,r.id); r.status="FAILED"; r.validation_json=json.dumps(jload(r.validation_json,[])+[{"field":"row","severity":"error","type":"import_failure","message":str(exc)}]); counts["failed"]+=1; await self.session.commit()
        s=await self.session.get(MaterialOnboardingSessionModel,session_id); s.status="COMPLETED_WITH_ERRORS" if counts["failed"] else "COMPLETED"; s.summary_json=json.dumps({**jload(s.summary_json,{}),**counts,"health_check":await self.health_check(tenant_id)})
        self.session.add(AuditLogModel(tenant_id=tenant_id,user_id=user_id,action="RAW_MATERIAL_IMPORT",entity_type="material_onboarding_session",entity_id=s.id,extra=counts)); await self.session.commit(); return jload(s.summary_json,{})
    async def _apply_row(self,tenant_id,user_id,row):
        d=jload(row.normalized_json,{})
        cat=await self.session.scalar(select(MaterialCategoryModel).where(MaterialCategoryModel.tenant_id==tenant_id,func.lower(MaterialCategoryModel.name)==norm(d["material_category"])))
        unit=await self.session.scalar(select(UnitOfMeasureModel).where(UnitOfMeasureModel.tenant_id==tenant_id,func.lower(UnitOfMeasureModel.code)==norm(d["uom"])))
        location=await self.session.scalar(select(LocationModel).where(LocationModel.tenant_id==tenant_id,LocationModel.is_deleted.is_(False),func.lower(LocationModel.name)==norm(d.get("rack_bin") or d.get("zone") or d.get("warehouse")))) if (d.get("rack_bin") or d.get("zone") or d.get("warehouse")) else None
        mat=await self.session.scalar(select(MaterialModel).where(MaterialModel.tenant_id==tenant_id,func.upper(MaterialModel.code)==str(d.get("item_code") or "").upper(),MaterialModel.is_deleted.is_(False))) if d.get("item_code") else None
        repo=MaterialRepository(self.session); uow=SQLAlchemyUnitOfWork(session=self.session,event_dispatcher=None)
        std_cost = Decimal(str(d["standard_cost"])) if d.get("standard_cost") else None
        if mat is None:
            result=await CreateMaterialHandler(repo,uow,ItemCodeService(self.session)).handle(CreateMaterialCommand(tenant_id=tenant_id,created_by=user_id,code=d.get("item_code") or None,name=d["material_name"],material_type=d.get("material_type") or "raw",category_id=cat.id,base_unit_id=unit.id,reorder_level=Decimal(str(d["reorder_level"])) if d.get("reorder_level") else None,location_id=location.id if location else None,is_batch_tracked=as_bool(d.get("batch_tracking_enabled"))))
            mat=await self.session.get(MaterialModel,result.id); row.classification="create"
            # Apply standard_cost after create (CreateMaterialCommand doesn't carry it yet)
            if std_cost is not None:
                mat.current_cost = float(std_cost)
        else:
            await UpdateMaterialHandler(repo,uow).handle(UpdateMaterialCommand(id=mat.id,tenant_id=tenant_id,name=d.get("material_name"),category_id=cat.id,base_unit_id=unit.id,material_type=d.get("material_type") or mat.material_type,reorder_level=Decimal(str(d["reorder_level"])) if d.get("reorder_level") else None,location_id=location.id if location else None,is_batch_tracked=optional_bool(d.get("batch_tracking_enabled")),current_cost=std_cost)); mat=await self.session.get(MaterialModel,mat.id)
            if d.get("item_code") and d["item_code"] != mat.code:
                if getattr(mat, "code_locked", False):
                    raise ValueError("Item code is immutable")
                mat.code = await ItemCodeService(self.session).validate_manual_code(
                    tenant_id=tenant_id, code=d["item_code"], target="material"
                )
                mat.item_code = mat.code
        sup=await self.session.scalar(select(SupplierModel).where(SupplierModel.tenant_id==tenant_id,func.lower(SupplierModel.code)==norm(d["approved_supplier"]))) if d.get("approved_supplier") else None
        mat.barcode=d.get("barcode") or mat.barcode
        if optional_bool(d.get("traceability_enabled")) is not None: mat.traceability_enabled=as_bool(d.get("traceability_enabled"))
        if optional_bool(d.get("qc_required")) is not None: mat.qc_required_flag=as_bool(d.get("qc_required"))
        mat.preferred_supplier_id=sup.id if sup else mat.preferred_supplier_id
        mat.supplier_item_code=d.get("supplier_item_code") or mat.supplier_item_code; mat.purchase_uom=d.get("purchase_uom") or mat.purchase_uom; mat.length_uom=d.get("length_uom") or mat.length_uom
        if optional_bool(d.get("cuttable_inventory")) is not None: mat.cuttable_inventory=as_bool(d.get("cuttable_inventory"))
        if optional_bool(d.get("remaining_quantity_tracking")) is not None: mat.remaining_quantity_tracking=as_bool(d.get("remaining_quantity_tracking"))
        if optional_bool(d.get("reusable_remainder")) is not None: mat.reusable_remainder=as_bool(d.get("reusable_remainder"))
        mat.decimal_precision=int(d["decimal_precision"]) if d.get("decimal_precision") else mat.decimal_precision
        if optional_bool(d.get("expiry_tracking")) is not None: mat.expiry_tracking=as_bool(d.get("expiry_tracking"))
        mat.shelf_life_days=int(d["shelf_life"]) if d.get("shelf_life") else mat.shelf_life_days; mat.lead_time_days=int(d["lead_time"]) if d.get("lead_time") else mat.lead_time_days; mat.min_stock=Decimal(str(d["min_stock"])) if d.get("min_stock") else mat.min_stock; mat.max_stock=Decimal(str(d["max_stock"])) if d.get("max_stock") else mat.max_stock; mat.reorder_quantity=Decimal(str(d["reorder_quantity"])) if d.get("reorder_quantity") else mat.reorder_quantity; mat.moq=Decimal(str(d["moq"])) if d.get("moq") else mat.moq
        row.result_material_id=mat.id; row.status="IMPORTED"; await self.session.commit()
    async def health_check(self,tenant_id):
        broken=(await self.session.execute(select(MaterialModel.id).where(MaterialModel.tenant_id==tenant_id,MaterialModel.cuttable_inventory.is_(True),MaterialModel.remaining_quantity_tracking.is_(False)))).scalars().all()
        return [{"type":"measured_configuration","count":len(broken)}] if broken else []
