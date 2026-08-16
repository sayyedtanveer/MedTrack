import uuid
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.shared.import_framework import BaseImportService
from backend.app.infrastructure.persistence.models.sales_models import ClientModel


class ClientImportService(BaseImportService):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        super().__init__(session, tenant_id, user_id)
        self.module_name = "CLIENTS"

    def get_template_columns(self) -> List[str]:
        return [
            "Code", "Name*", "Email", "Phone", "Address", "GST Number", 
            "Credit Limit", "Payment Terms (Days)"
        ]

    def get_instructions(self) -> List[Tuple[str, str]]:
        instructions = super().get_instructions()
        instructions.extend([
            ("Code", "Optional. Unique identifier for the client (max 50 chars). If blank, an auto-code is generated."),
            ("Name*", "Mandatory. Name of the client company (max 255 chars)."),
            ("Email", "Optional. Valid email address format."),
            ("Credit Limit", "Optional. Numeric value."),
            ("Payment Terms (Days)", "Optional. Integer value."),
        ])
        return instructions

    async def validate_row(self, row_data: Dict[str, Any]) -> List[Dict[str, str]]:
        errors = []
        
        # Mandatory fields
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
            
        credit_limit = row_data.get("Credit Limit")
        if credit_limit is not None and str(credit_limit).strip() != "":
            try:
                float(credit_limit)
            except ValueError:
                errors.append({"column": "Credit Limit", "value": str(credit_limit), "error": "Must be a number"})
                
        payment_terms = row_data.get("Payment Terms (Days)")
        if payment_terms is not None and str(payment_terms).strip() != "":
            try:
                int(payment_terms)
            except ValueError:
                errors.append({"column": "Payment Terms (Days)", "value": str(payment_terms), "error": "Must be an integer"})
                
        return errors

    async def bulk_insert(self, valid_rows_data: List[Dict[str, Any]], duplicate_strategy: str) -> None:
        if not valid_rows_data:
            return
            
        # Get all existing client codes for this tenant
        codes = []
        for r in valid_rows_data:
            c_raw = r.get("Code") if r.get("Code") is not None else r.get("Code*")
            if c_raw:
                codes.append(str(c_raw).strip())
                
        existing_codes = set()
        if codes:
            stmt = select(ClientModel.code).where(
                ClientModel.tenant_id == self.tenant_id,
                ClientModel.code.in_(codes)
            )
            result = await self.session.execute(stmt)
            existing_codes = set(result.scalars().all())
        
        new_clients = []
        update_clients = {}
        
        from backend.app.application.inventory.services.item_code_service import ItemCodeService
        item_code_service = ItemCodeService(self.session)
        
        for row in valid_rows_data:
            name_raw = row.get("Name*") if row.get("Name*") is not None else row.get("Name")
            name = str(name_raw).strip() if name_raw is not None else ""
            
            code_raw = row.get("Code") if row.get("Code") is not None else row.get("Code*")
            code = str(code_raw).strip() if code_raw is not None else ""
            
            if not code:
                # Auto-generate if code is not provided
                code = await item_code_service.generate_for_entity(
                    tenant_id=self.tenant_id,
                    entity_type="customer",
                    entity_name=name,
                    user_id=self.user_id
                )
            email = str(row.get("Email", "")).strip() if row.get("Email") else None
            phone = str(row.get("Phone", "")).strip() if row.get("Phone") else None
            address = str(row.get("Address", "")).strip() if row.get("Address") else None
            gst = str(row.get("GST Number", "")).strip() if row.get("GST Number") else None
            
            credit_limit_raw = row.get("Credit Limit")
            credit_limit = float(credit_limit_raw) if credit_limit_raw is not None and str(credit_limit_raw).strip() != "" else None
            
            payment_terms_raw = row.get("Payment Terms (Days)")
            payment_terms = int(payment_terms_raw) if payment_terms_raw is not None and str(payment_terms_raw).strip() != "" else 0
            
            client_dict = {
                "tenant_id": self.tenant_id,
                "code": code,
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "gst_number": gst,
                "credit_limit": credit_limit,
                "payment_terms_days": payment_terms,
            }
            
            if code in existing_codes:
                if duplicate_strategy == "FAIL_IMPORT":
                    raise ValueError(f"Duplicate client code found: {code}")
                elif duplicate_strategy == "UPDATE":
                    update_clients[code] = client_dict
                # if SKIP, do nothing
            else:
                new_clients.append(ClientModel(**client_dict))
                
        if new_clients:
            self.session.add_all(new_clients)
            
        if update_clients and duplicate_strategy == "UPDATE":
            # For update, we fetch the existing models and update them
            # This is safer for ORM than bulk update dictionaries if there are events,
            # but bulk update is faster. Let's do a fast fetch and update.
            stmt = select(ClientModel).where(
                ClientModel.tenant_id == self.tenant_id,
                ClientModel.code.in_(list(update_clients.keys()))
            )
            result = await self.session.execute(stmt)
            existing_models = result.scalars().all()
            
            for model in existing_models:
                update_data = update_clients[model.code]
                model.name = update_data["name"]
                model.email = update_data["email"]
                model.phone = update_data["phone"]
                model.address = update_data["address"]
                model.gst_number = update_data["gst_number"]
                if update_data["credit_limit"] is not None:
                    model.credit_limit = update_data["credit_limit"]
                model.payment_terms_days = update_data["payment_terms_days"]
                
        await self.session.flush()
