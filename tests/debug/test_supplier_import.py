import asyncio
import io
import uuid
import openpyxl
from backend.app.infrastructure.persistence.database import async_session_maker
from backend.app.application.procurement.supplier_import_service import SupplierImportService

async def main():
    async with async_session_maker() as session:
        # Generate dummy file
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Code", "Name*", "Email", "Performance Rating", "GST Number"])
        ws.append(["SUP1", "Test Sup", "test@sup.com", "4.5", "27AAAAA0000A1Z5"])
        output = io.BytesIO()
        wb.save(output)
        content = output.getvalue()
        
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        service = SupplierImportService(session, tenant_id, user_id)
        
        try:
            session_id = await service.parse_and_store_preview(content)
            print(f"Success! Session ID: {session_id}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
