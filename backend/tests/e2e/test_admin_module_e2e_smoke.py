from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

from backend.app.main import app


BASE = "/api/v1"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
ADMIN_EMAIL = "admin.e2e@medtrack-demo.com"
ADMIN_PASSWORD = "E2EAdmin@1234"
CLIENT_ID = "7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1c101"
UOM_ID = "7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1d001"
MATERIAL_KIT_ID = "7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1d101"


class SmokeClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.token: str | None = None

    async def call(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        expected: set[int] | None = None,
    ) -> Any:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = await self.client.request(
            method,
            BASE + path,
            json=data,
            headers=headers,
            timeout=30,
        )
        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
        if expected and response.status_code not in expected:
            raise AssertionError(
                f"{method} {path} expected {expected} got {response.status_code}: {payload}"
            )
        return payload


async def run() -> None:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as raw_client:
            client = SmokeClient(raw_client)
            login = await client.call(
                "POST",
                "/auth/login",
                {
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                    "tenant_id": TENANT_ID,
                },
                {200},
            )
            client.token = login["access_token"]
            run_id = str(uuid.uuid4())[:8].upper()

            code = f"E2E-PROD-{run_id}"
            template = await client.call(
                "POST",
                "/products/templates",
                {
                    "code": code,
                    "name": f"E2E Product {run_id}",
                    "description": "Created by admin module e2e smoke",
                    "base_unit_id": UOM_ID,
                    "attributes": [{"key": "SIZE", "label": "Size", "values": ["STD"]}],
                },
                {201},
            )
            template_id = template["id"]
            listed = await client.call(
                "GET",
                f"/products/templates?query={code}&page=1&page_size=20",
                expected={200},
            )
            assert any(item["id"] == template_id for item in listed["items"])
            template_get = await client.call("GET", f"/products/templates/{template_id}", expected={200})
            assert template_get["code"] == code
            template_update = await client.call(
                "PUT",
                f"/products/templates/{template_id}",
                {"name": f"E2E Product {run_id} Updated"},
                {200},
            )
            assert template_update["name"].endswith("Updated")

            variant = await client.call(
                "POST",
                f"/products/templates/{template_id}/variants",
                {
                    "attribute_values": {"SIZE": "STD"},
                    "base_unit_id": UOM_ID,
                    "standard_cost": 125.50,
                    "selling_price": 199.99,
                },
                {201},
            )
            variant_id = variant["id"]
            variants = await client.call(
                "GET",
                f"/products/templates/{template_id}/variants?page=1&page_size=20",
                expected={200},
            )
            assert any(item["id"] == variant_id for item in variants["items"])
            all_variants = await client.call(
                "GET",
                f"/products/variants?search={code}&page=1&page_size=20",
                expected={200},
            )
            assert any(item["id"] == variant_id for item in all_variants["items"])
            variant_update = await client.call(
                "PUT",
                f"/products/variants/{variant_id}",
                {"selling_price": 219.99},
                {200},
            )
            assert float(variant_update["selling_price"]) == 219.99

            version = f"v{run_id}"
            bom = await client.call(
                "POST",
                f"/products/{template_id}/boms",
                {
                    "version": version,
                    "valid_from": datetime.now(timezone.utc).isoformat(),
                    "template_id": template_id,
                    "lines": [
                        {
                            "material_id": MATERIAL_KIT_ID,
                            "quantity": 2,
                            "unit_id": UOM_ID,
                            "scrap_percentage": 0,
                        }
                    ],
                },
                {201},
            )
            bom_id = bom["id"]
            assert len(bom["lines"]) == 1
            bom_list = await client.call(
                "GET",
                f"/products/{template_id}/boms?is_template=true&page=1&page_size=20",
                expected={200},
            )
            assert any(item["id"] == bom_id for item in bom_list["items"])
            bom_get = await client.call("GET", f"/boms/{bom_id}", expected={200})
            assert bom_get["version"] == version
            assert "total_cost" in await client.call("GET", f"/boms/{bom_id}/cost", expected={200})
            assert await client.call("GET", f"/boms/{bom_id}/tree", expected={200}) is not None
            activated = await client.call("POST", f"/boms/{bom_id}/activate", expected={200})
            assert activated["is_active"] is True

            start = date.today()
            due = start + timedelta(days=7)
            work_order = await client.call(
                "POST",
                "/work-orders",
                {
                    "product_id": variant_id,
                    "bom_id": bom_id,
                    "planned_quantity": 1,
                    "start_date": start.isoformat(),
                    "due_date": due.isoformat(),
                    "priority": "NORMAL",
                    "notes": "Admin E2E smoke work order",
                },
                {201},
            )
            work_order_id = work_order["id"]
            work_orders = await client.call("GET", "/work-orders", expected={200})
            assert any(item["id"] == work_order_id for item in work_orders)
            detail = await client.call("GET", f"/work-orders/{work_order_id}", expected={200})
            assert detail["id"] == work_order_id
            assert len(detail["materials"]) == 1
            assert (await client.call("POST", f"/work-orders/{work_order_id}/release", {}, {200}))["status"] == "RELEASED"
            assert (await client.call("POST", f"/work-orders/{work_order_id}/start", {}, {200}))["status"] == "IN_PROGRESS"
            issued = await client.call(
                "POST",
                f"/work-orders/{work_order_id}/issue-materials",
                {"material_id": MATERIAL_KIT_ID, "quantity": 2, "unit_id": UOM_ID},
                {200},
            )
            assert issued["message"]
            produced = await client.call(
                "POST",
                f"/work-orders/{work_order_id}/record-production",
                {"produced_quantity": 1, "scrap_quantity": 0, "notes": "E2E production"},
                {200},
            )
            assert produced["message"]
            assert (await client.call("POST", f"/work-orders/{work_order_id}/complete", {}, {200}))["status"] == "COMPLETED"
            assert (await client.call("POST", f"/work-orders/{work_order_id}/close", {}, {200}))["status"] == "CLOSED"

            invoice_date = date.today()
            invoice_due = invoice_date + timedelta(days=30)
            invoice = await client.call(
                "POST",
                "/finance/invoices",
                {
                    "client_id": CLIENT_ID,
                    "invoice_date": invoice_date.isoformat(),
                    "due_date": invoice_due.isoformat(),
                    "lines": [
                        {
                            "product_id": MATERIAL_KIT_ID,
                            "product_type": "material",
                            "description": "Admin E2E invoice line",
                            "quantity": 1,
                            "unit_price": 1000,
                            "discount_amount": 0,
                            "tax_rate": 18,
                            "tax_amount": 180,
                            "total": 1180,
                        }
                    ],
                    "notes": "Admin E2E manual invoice",
                    "terms": "Net 30",
                },
                {201},
            )
            invoice_id = invoice["id"]
            invoices = await client.call(
                "GET",
                f"/finance/invoices?client_id={CLIENT_ID}&page=1&page_size=25",
                expected={200},
            )
            assert any(item["id"] == invoice_id for item in invoices["items"])
            invoice_get = await client.call("GET", f"/finance/invoices/{invoice_id}", expected={200})
            assert invoice_get["id"] == invoice_id
            sent = await client.call("POST", f"/finance/invoices/{invoice_id}/send", expected={200})
            assert sent["status"] == "SENT"
            payment = await client.call(
                "POST",
                "/finance/payments",
                {
                    "invoice_id": invoice_id,
                    "amount": 1180,
                    "payment_date": invoice_date.isoformat(),
                    "payment_method": "BANK_TRANSFER",
                    "reference_number": f"E2E-{run_id}",
                },
                {201},
            )
            payment_id = payment["id"]
            payments = await client.call(
                "GET",
                f"/finance/payments?invoice_id={invoice_id}&page=1&page_size=25",
                expected={200},
            )
            assert any(item["id"] == payment_id for item in payments["items"])
            dashboard = await client.call("GET", "/finance/dashboard", expected={200})
            assert "ar" in dashboard and "ap" in dashboard
            assert isinstance(await client.call("GET", "/finance/ar-aging", expected={200}), list)
            ledger = await client.call("GET", "/finance/ledger?page=1&page_size=50", expected={200})
            assert len(ledger["items"]) > 0

            print("ADMIN_PRODUCT_BOM_WORKORDER_FINANCE_ASGI_E2E_PASSED")
            print(f"template_id={template_id}")
            print(f"variant_id={variant_id}")
            print(f"bom_id={bom_id}")
            print(f"work_order_id={work_order_id}")
            print(f"invoice_id={invoice_id}")
            print(f"payment_id={payment_id}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_product_bom_workorder_finance_asgi_e2e() -> None:
    await run()


if __name__ == "__main__":
    asyncio.run(run())
