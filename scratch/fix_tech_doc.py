import sys

def main():
    path = r'c:\Users\sayye\source\repos\MedTrack\backend\app\application\documents\services\technical_document_service.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the WorkOrderLineModel import
    import_stmt = "from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderLineModel\n"
    content = content.replace(import_stmt, "")

    # Fix _get_and_verify_work_order_line to just fetch WorkOrderModel instead of WorkOrderLineModel
    find_method = """    async def _get_and_verify_work_order_line(
        self,
        tenant_id: uuid.UUID,
        line_id: uuid.UUID,
    ) -> WorkOrderLineModel:
        \"\"\"Fetch a WorkOrderLine and verify it belongs to the given tenant.

        Tenant isolation is enforced by joining through the parent WorkOrder
        \"\"\"
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
        stmt = (
            select(WorkOrderLineModel)
            .join(WorkOrderModel, WorkOrderModel.id == WorkOrderLineModel.work_order_id)
            .where(
                WorkOrderLineModel.id == line_id,
                WorkOrderLineModel.is_deleted.is_(False),
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        line = result.scalar_one_or_none()
        if not line:
            raise ValueError(f"Work order line not found: {line_id}")
        return line"""

    replace_method = """    async def _get_and_verify_work_order_line(
        self,
        tenant_id: uuid.UUID,
        line_id: uuid.UUID,
    ):
        \"\"\"Fetch a WorkOrder and verify it belongs to the given tenant.
        (Fallback logic since WorkOrderLineModel does not exist yet)
        \"\"\"
        from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
        stmt = (
            select(WorkOrderModel)
            .where(
                WorkOrderModel.id == line_id,
                WorkOrderModel.tenant_id == tenant_id,
                WorkOrderModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            raise ValueError(f"Work order not found: {line_id}")
        return wo"""

    content = content.replace(find_method, replace_method)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    main()
