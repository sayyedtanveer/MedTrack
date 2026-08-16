import uuid
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.shared.import_framework import BaseImportService
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel


class SupplierImportService(BaseImportService):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        super().__init__(session, tenant_id, user_id)
        self.module_name = "SUPPLIERS"

    def get_template_columns(self) -> List[str]:
        return [
            "Code", "Name*", "Contact Person", "Email", "Phone", "Address", 
            "GST Number", "Payment Terms", "Performance Rating"
        ]

    def get_instructions(self) -> List[Tuple[str, str]]:
        instructions = super().get_instructions()
        instructions.extend([
            ("Code", "Optional. Unique identifier for the supplier (max 50 chars). If blank, an auto-code is generated."),
            ("Name*", "Mandatory. Name of the supplier company (max 255 chars)."),
            ("Email", "Optional. Valid email address format."),
            ("Performance Rating", "Optional. Decimal between 0.00 and 5.00."),
        ])
        return instructions

    async def validate_row(self, row_data: Dict[str, Any]) -> List[Dict[str, str]]:
        errors = []
        
        code_raw = row_data.get("Code") if row_data.get("Code") is not None else row_data.get("Code*")
        code = str(code_raw).strip() if code_raw is not None else ""
        
        name_raw = row_data.get("Name*") if row_data.get("Name*") is not None else row_data.get("Name")
        name = str(name_raw).strip() if name_raw is not None else ""
        
        if code and len(code) > 50:
            errors.append({"column": "Code", "value": code, "error": "Code exceeds 50 characters"})
            
        if not name:
            errors.append({"column": "Name*", "value": "", "error": "Name is mandatory"})
        elif len(name) > 255:
            errors.append({"column": "Name*", "value": name, "error": "Name exceeds 255 characters"})
            
        email = str(row_data.get("Email", "")).strip() if row_data.get("Email") is not None else ""
        if email and ("@" not in email or "." not in email):
            errors.append({"column": "Email", "value": email, "error": "Invalid email format"})
            
        gst = str(row_data.get("GST Number", "")).strip() if row_data.get("GST Number") is not None else ""
        import re
        if gst and not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gst):
            errors.append({"column": "GST Number", "value": gst, "error": "Invalid GST format"})
            
        perf_rating = row_data.get("Performance Rating")
        if perf_rating is not None and str(perf_rating).strip() != "":
            try:
                rating = float(perf_rating)
                if rating < 0 or rating > 5:
                    errors.append({"column": "Performance Rating", "value": str(perf_rating), "error": "Must be between 0 and 5"})
            except ValueError:
                errors.append({"column": "Performance Rating", "value": str(perf_rating), "error": "Must be a number"})
                
        return errors

    async def bulk_insert(self, valid_rows: List[Dict[str, Any]], duplicate_strategy: str = "SKIP") -> None:
        from backend.app.application.inventory.services.item_code_service import ItemCodeService
        if not valid_rows:
            return
            
        item_code_service = ItemCodeService(self.session)
            
        codes = []
        for r in valid_rows:
            c_raw = r.get("Code") if r.get("Code") is not None else r.get("Code*")
            if c_raw:
                codes.append(str(c_raw).strip())
        
        existing_codes = set()
        if codes:
            stmt = select(SupplierModel.code).where(
                SupplierModel.tenant_id == self.tenant_id,
                SupplierModel.code.in_(codes)
            )
            result = await self.session.execute(stmt)
            existing_codes = set(result.scalars().all())
        
        new_suppliers = []
        update_suppliers = {}
        
        from backend.app.application.inventory.services.item_code_service import ItemCodeService
        item_code_service = ItemCodeService(self.session)
        
        for row in valid_rows:
            name_raw = row.get("Name*") if row.get("Name*") is not None else row.get("Name")
            name = str(name_raw).strip() if name_raw is not None else ""
            
            code_raw = row.get("Code") if row.get("Code") is not None else row.get("Code*")
            code = str(code_raw).strip() if code_raw is not None else ""
            
            if not code:
                # Auto-generate if code is not provided
                code = await item_code_service.generate_for_entity(
                    tenant_id=self.tenant_id,
                    entity_type="supplier",
                    entity_name=name,
                    user_id=self.user_id
                )
            contact_person = str(row.get("Contact Person", "")).strip() if row.get("Contact Person") else None
            email = str(row.get("Email", "")).strip() if row.get("Email") else None
            phone = str(row.get("Phone", "")).strip() if row.get("Phone") else None
            address = str(row.get("Address", "")).strip() if row.get("Address") else None
            gst = str(row.get("GST Number", "")).strip() if row.get("GST Number") else None
            payment_terms = str(row.get("Payment Terms", "")).strip() if row.get("Payment Terms") else None
            
            perf_rating_raw = row.get("Performance Rating")
            perf_rating = float(perf_rating_raw) if perf_rating_raw is not None and str(perf_rating_raw).strip() != "" else None
            
            supplier_dict = {
                "tenant_id": self.tenant_id,
                "code": code,
                "name": name,
                "contact_person": contact_person,
                "email": email,
                "phone": phone,
                "address": address,
                "gst": gst,
                "payment_terms": payment_terms,
                "performance_rating": perf_rating,
                "created_by": self.user_id,
                "updated_by": self.user_id
            }
            
            if code in existing_codes:
                if duplicate_strategy == "FAIL_IMPORT":
                    raise ValueError(f"Duplicate supplier code found: {code}")
                elif duplicate_strategy == "UPDATE":
                    update_suppliers[code] = supplier_dict
            else:
                new_suppliers.append(SupplierModel(**supplier_dict))
                
        if new_suppliers:
            self.session.add_all(new_suppliers)
            
        if update_suppliers and duplicate_strategy == "UPDATE":
            stmt = select(SupplierModel).where(
                SupplierModel.tenant_id == self.tenant_id,
                SupplierModel.code.in_(list(update_suppliers.keys()))
            )
            result = await self.session.execute(stmt)
            existing_models = result.scalars().all()
            
            for model in existing_models:
                update_data = update_suppliers[model.code]
                model.name = update_data["name"]
                model.contact_person = update_data["contact_person"]
                model.email = update_data["email"]
                model.phone = update_data["phone"]
                model.address = update_data["address"]
                model.gst = update_data["gst"]
                model.payment_terms = update_data["payment_terms"]
                if update_data["performance_rating"] is not None:
                    model.performance_rating = update_data["performance_rating"]
                model.updated_by = self.user_id
                
        await self.session.flush()
