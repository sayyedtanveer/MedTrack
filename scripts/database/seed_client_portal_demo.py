from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher


TENANT_ID = uuid.UUID("b5ef68c4-18be-4fa6-a439-a23c34877550")
TENANT_SLUG = "medtrack-demo"

CLIENT_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1c101")
CLIENT_USER_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1c102")
CLIENT_EMAIL = "client.portal@acme-demo.com"
CLIENT_PASSWORD = "Client@1234"

OTHER_CLIENT_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1c201")

UOM_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1d001")
MATERIAL_KIT_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1d101")
MATERIAL_LOW_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1d102")

ORDER_CONFIRMED_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1e101")
ORDER_PRODUCTION_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1e102")
ORDER_SHIPPED_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1e103")
ORDER_DELIVERED_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1e104")
OTHER_ORDER_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1e201")

INVOICE_PAID_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1f101")
INVOICE_SENT_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1f102")
INVOICE_OVERDUE_ID = uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1f103")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def execute(conn, sql: str, **params) -> None:
    await conn.execute(text(sql), params)


async def seed() -> None:
    now = utcnow()
    today = date.today()
    password_hash = BcryptPasswordHasher().hash(CLIENT_PASSWORD)
    order_ids = [ORDER_CONFIRMED_ID, ORDER_PRODUCTION_ID, ORDER_SHIPPED_ID, ORDER_DELIVERED_ID, OTHER_ORDER_ID]
    invoice_ids = [INVOICE_PAID_ID, INVOICE_SENT_ID, INVOICE_OVERDUE_ID]

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await execute(conn, "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS created_by UUID NULL")
        await execute(conn, "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS updated_by UUID NULL")
        await execute(conn, "ALTER TABLE materials ADD COLUMN IF NOT EXISTS created_by UUID NULL")
        await execute(conn, "ALTER TABLE materials ADD COLUMN IF NOT EXISTS updated_by UUID NULL")

        await execute(
            conn,
            """
            INSERT INTO tenants (id, name, slug, plan, is_active, is_deleted, created_at, updated_at, currency_code, currency_symbol)
            VALUES (:id, 'MedTrack Demo Tenant', :slug, 'starter', true, false, :now, :now, 'INR', 'Rs')
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                is_active = true,
                is_deleted = false,
                updated_at = EXCLUDED.updated_at
            """,
            id=TENANT_ID,
            slug=TENANT_SLUG,
            now=now,
        )

        await execute(
            conn,
            """
            INSERT INTO units_of_measure (id, tenant_id, code, name, precision, is_active, is_deleted, created_at, updated_at)
            VALUES (:id, :tenant_id, 'EA', 'Each', 2, true, false, :now, :now)
            ON CONFLICT (tenant_id, code) DO UPDATE SET
                id = EXCLUDED.id,
                name = EXCLUDED.name,
                precision = EXCLUDED.precision,
                is_active = true,
                is_deleted = false,
                updated_at = EXCLUDED.updated_at
            """,
            id=UOM_ID,
            tenant_id=TENANT_ID,
            now=now,
        )

        for material in [
            (MATERIAL_KIT_ID, "CLIENT-KIT", "Client Portal Starter Kit", 120, 12),
            (MATERIAL_LOW_ID, "CLIENT-LOW", "Low Stock Demo Component", 2, 10),
        ]:
            await execute(
                conn,
                """
                INSERT INTO materials (
                    id, tenant_id, code, name, description, base_unit_id, material_type,
                    current_stock, reserved_stock, reorder_level, current_cost,
                    is_batch_tracked, is_serialized, inspection_required,
                    is_active, is_deleted, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :code, :name, 'Seeded for client portal e2e testing', :uom_id, 'raw',
                    :stock, 0, :reorder_level, 100,
                    false, false, false,
                    true, false, :now, :now
                )
                ON CONFLICT (tenant_id, code) DO UPDATE SET
                    id = EXCLUDED.id,
                    name = EXCLUDED.name,
                    base_unit_id = EXCLUDED.base_unit_id,
                    current_stock = EXCLUDED.current_stock,
                    reserved_stock = EXCLUDED.reserved_stock,
                    reorder_level = EXCLUDED.reorder_level,
                    is_active = true,
                    is_deleted = false,
                    updated_at = EXCLUDED.updated_at
                """,
                id=material[0],
                tenant_id=TENANT_ID,
                code=material[1],
                name=material[2],
                stock=material[3],
                reorder_level=material[4],
                uom_id=UOM_ID,
                now=now,
            )

        for client in [
            (CLIENT_ID, "CLIENT-DEMO", "Acme Demo Client", CLIENT_EMAIL, "8005550101", "Demo Industrial Park, Pune", "27AAECA1234A1Z5", 75000, 62000),
            (OTHER_CLIENT_ID, "CLIENT-OTHER", "Other Demo Client", "other.client@acme-demo.com", "8005550102", "Other Park, Pune", "27AAECO9876A1Z5", 50000, 1000),
        ]:
            await execute(
                conn,
                """
                INSERT INTO sales_clients (
                    id, tenant_id, code, name, email, phone, address, gst_number,
                    credit_limit, credit_used, payment_terms_days,
                    is_active, is_deleted, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :code, :name, :email, :phone, :address, :gst,
                    :credit_limit, :credit_used, 30,
                    true, false, :now, :now
                )
                ON CONFLICT (tenant_id, code) DO UPDATE SET
                    id = EXCLUDED.id,
                    name = EXCLUDED.name,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    address = EXCLUDED.address,
                    gst_number = EXCLUDED.gst_number,
                    credit_limit = EXCLUDED.credit_limit,
                    credit_used = EXCLUDED.credit_used,
                    payment_terms_days = EXCLUDED.payment_terms_days,
                    is_active = true,
                    is_deleted = false,
                    updated_at = EXCLUDED.updated_at
                """,
                id=client[0],
                tenant_id=TENANT_ID,
                code=client[1],
                name=client[2],
                email=client[3],
                phone=client[4],
                address=client[5],
                gst=client[6],
                credit_limit=client[7],
                credit_used=client[8],
                now=now,
            )

        await execute(
            conn,
            """
            DELETE FROM users
            WHERE tenant_id = :tenant_id
              AND email = :email
              AND id <> :id
            """,
            tenant_id=TENANT_ID,
            email=CLIENT_EMAIL,
            id=CLIENT_USER_ID,
        )
        await execute(
            conn,
            """
            INSERT INTO users (
                id, tenant_id, email, hashed_password, first_name, last_name, role,
                supplier_id, client_id, is_active, totp_enabled, backup_codes,
                is_deleted, created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :email, :hashed_password, 'Client', 'Portal', 'client',
                NULL, :client_id, true, false, '[]'::jsonb,
                false, :now, :now
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                hashed_password = EXCLUDED.hashed_password,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                role = 'client',
                client_id = EXCLUDED.client_id,
                supplier_id = NULL,
                is_active = true,
                is_deleted = false,
                updated_at = EXCLUDED.updated_at
            """,
            id=CLIENT_USER_ID,
            tenant_id=TENANT_ID,
            email=CLIENT_EMAIL,
            hashed_password=password_hash,
            client_id=CLIENT_ID,
            now=now,
        )

        await execute(conn, "DELETE FROM payments WHERE invoice_id = ANY(:invoice_ids)", invoice_ids=invoice_ids)
        await execute(conn, "DELETE FROM invoice_lines WHERE invoice_id = ANY(:invoice_ids)", invoice_ids=invoice_ids)
        await execute(conn, "DELETE FROM invoices WHERE id = ANY(:invoice_ids)", invoice_ids=invoice_ids)
        await execute(
            conn,
            """
            DELETE FROM sales_order_lines
            WHERE sales_order_id IN (
                SELECT id
                FROM sales_orders
                WHERE tenant_id = :tenant_id
                  AND client_id = :client_id
                  AND created_by = 'client-portal'
            )
            """,
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
        )
        await execute(
            conn,
            """
            DELETE FROM sales_orders
            WHERE tenant_id = :tenant_id
              AND client_id = :client_id
              AND created_by = 'client-portal'
            """,
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
        )
        await execute(conn, "DELETE FROM sales_order_lines WHERE sales_order_id = ANY(:order_ids)", order_ids=order_ids)
        await execute(conn, "DELETE FROM sales_orders WHERE id = ANY(:order_ids)", order_ids=order_ids)
        await execute(conn, "DELETE FROM client_addresses WHERE client_id IN (:client_id, :other_client_id)", client_id=CLIENT_ID, other_client_id=OTHER_CLIENT_ID)
        await execute(conn, "DELETE FROM client_notification_settings WHERE user_id = :user_id", user_id=CLIENT_USER_ID)
        await execute(conn, "DELETE FROM notifications WHERE user_id = :user_id", user_id=CLIENT_USER_ID)
        await execute(
            conn,
            """
            DELETE FROM notifications
            WHERE tenant_id = :tenant_id
              AND type = 'CLIENT_SUPPORT'
              AND reference_type = 'support_request'
            """,
            tenant_id=TENANT_ID,
        )

        address_rows = [
            (uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1a101"), CLIENT_ID, "billing", "Billing HQ", "Acme Finance", "Tower A, Demo Industrial Park", "Pune", "Maharashtra", "411045", True),
            (uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1a102"), CLIENT_ID, "shipping", "Main Dock", "Acme Warehouse", "Dock 4, Demo Industrial Park", "Pune", "Maharashtra", "411045", True),
            (uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1a201"), OTHER_CLIENT_ID, "shipping", "Other Dock", "Other Warehouse", "Other Dock", "Pune", "Maharashtra", "411046", True),
        ]
        for row in address_rows:
            await execute(
                conn,
                """
                INSERT INTO client_addresses (
                    id, tenant_id, client_id, type, label, contact_name, address_line1,
                    city, state, postal_code, country, phone, email, is_default, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :client_id, :type, :label, :contact_name, :address_line1,
                    :city, :state, :postal_code, 'India', '8005550101', :email, :is_default, :now, :now
                )
                """,
                id=row[0],
                tenant_id=TENANT_ID,
                client_id=row[1],
                type=row[2],
                label=row[3],
                contact_name=row[4],
                address_line1=row[5],
                city=row[6],
                state=row[7],
                postal_code=row[8],
                email=CLIENT_EMAIL,
                is_default=row[9],
                now=now,
            )

        orders = [
            (ORDER_CONFIRMED_ID, CLIENT_ID, "CLIENT-DEMO-CONFIRMED", today - timedelta(days=8), today + timedelta(days=5), "CONFIRMED", 11800),
            (ORDER_PRODUCTION_ID, CLIENT_ID, "CLIENT-DEMO-PRODUCTION", today - timedelta(days=6), today + timedelta(days=4), "PRODUCTION", 23600),
            (ORDER_SHIPPED_ID, CLIENT_ID, "CLIENT-DEMO-SHIPPED", today - timedelta(days=4), today + timedelta(days=1), "SHIPPED", 17700),
            (ORDER_DELIVERED_ID, CLIENT_ID, "CLIENT-DEMO-DELIVERED", today - timedelta(days=20), today - timedelta(days=12), "DELIVERED", 14160),
            (OTHER_ORDER_ID, OTHER_CLIENT_ID, "CLIENT-DEMO-OTHER-HIDDEN", today - timedelta(days=3), today + timedelta(days=2), "SHIPPED", 9999),
        ]
        for order_id, client_id, order_number, order_date, delivery_date, status, total in orders:
            await execute(
                conn,
                """
                INSERT INTO sales_orders (
                    id, tenant_id, order_number, client_id, order_date, delivery_date,
                    status, payment_status, subtotal, discount_amount, tax_amount, grand_total,
                    notes, created_by, is_active, is_deleted, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :order_number, :client_id, :order_date, :delivery_date,
                    :status, 'PENDING', :subtotal, 0, :tax_amount, :grand_total,
                    'Seeded client portal demo order', 'client-demo-seed', true, false, :now, :now
                )
                """,
                id=order_id,
                tenant_id=TENANT_ID,
                order_number=order_number,
                client_id=client_id,
                order_date=order_date.isoformat(),
                delivery_date=delivery_date.isoformat(),
                status=status,
                subtotal=round(total / 1.18, 2),
                tax_amount=round(total - (total / 1.18), 2),
                grand_total=total,
                now=now,
            )

        line_rows = [
            (ORDER_CONFIRMED_ID, MATERIAL_KIT_ID, 10, 1000),
            (ORDER_PRODUCTION_ID, MATERIAL_LOW_ID, 20, 1000),
            (ORDER_SHIPPED_ID, MATERIAL_KIT_ID, 15, 1000),
            (ORDER_DELIVERED_ID, MATERIAL_KIT_ID, 12, 1000),
            (OTHER_ORDER_ID, MATERIAL_KIT_ID, 3, 2824.86),
        ]
        for order_id, material_id, qty, unit_price in line_rows:
            subtotal = round(qty * unit_price, 2)
            tax = round(subtotal * 0.18, 2)
            await execute(
                conn,
                """
                INSERT INTO sales_order_lines (
                    id, sales_order_id, product_id, product_type, uom_id,
                    quantity, unit_price, tax_rate, tax_amount, line_total,
                    allocated_quantity, shipped_quantity, backorder_quantity,
                    status, created_at, updated_at
                )
                VALUES (
                    :id, :sales_order_id, :product_id, 'material', :uom_id,
                    :quantity, :unit_price, 18, :tax_amount, :line_total,
                    0, :shipped_quantity, :backorder_quantity,
                    'PENDING', :now, :now
                )
                """,
                id=uuid.uuid4(),
                sales_order_id=order_id,
                product_id=material_id,
                uom_id=UOM_ID,
                quantity=qty,
                unit_price=unit_price,
                tax_amount=tax,
                line_total=subtotal + tax,
                shipped_quantity=qty if order_id in (ORDER_SHIPPED_ID, ORDER_DELIVERED_ID) else 0,
                backorder_quantity=qty if material_id == MATERIAL_LOW_ID else 0,
                now=now,
            )

        invoices = [
            (INVOICE_PAID_ID, "CLIENT-DEMO-INV-PAID", ORDER_DELIVERED_ID, "PAID", today - timedelta(days=15), today - timedelta(days=5), 14160, 14160),
            (INVOICE_SENT_ID, "CLIENT-DEMO-INV-SENT", ORDER_SHIPPED_ID, "SENT", today - timedelta(days=2), today + timedelta(days=28), 17700, 0),
            (INVOICE_OVERDUE_ID, "CLIENT-DEMO-INV-OVERDUE", ORDER_PRODUCTION_ID, "OVERDUE", today - timedelta(days=40), today - timedelta(days=10), 23600, 2500),
        ]
        for invoice_id, number, order_id, status, invoice_date, due_date, total, paid in invoices:
            await execute(
                conn,
                """
                INSERT INTO invoices (
                    id, tenant_id, invoice_number, sales_order_id, client_id,
                    client_name, client_address, client_gst_number,
                    status, invoice_date, due_date,
                    subtotal, discount_amount, tax_amount, grand_total, paid_amount,
                    notes, terms, created_by, is_deleted, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :invoice_number, :order_id, :client_id,
                    'Acme Demo Client', 'Tower A, Demo Industrial Park, Pune', '27AAECA1234A1Z5',
                    :status, :invoice_date, :due_date,
                    :subtotal, 0, :tax_amount, :grand_total, :paid_amount,
                    'Seeded client portal invoice', 'Net 30', :created_by, false, :now, :now
                )
                """,
                id=invoice_id,
                tenant_id=TENANT_ID,
                invoice_number=number,
                order_id=order_id,
                client_id=CLIENT_ID,
                status=status,
                invoice_date=invoice_date,
                due_date=due_date,
                subtotal=round(total / 1.18, 2),
                tax_amount=round(total - (total / 1.18), 2),
                grand_total=total,
                paid_amount=paid,
                created_by=CLIENT_USER_ID,
                now=now,
            )
            await execute(
                conn,
                """
                INSERT INTO invoice_lines (
                    id, tenant_id, invoice_id, product_id, product_type, description,
                    quantity, unit_price, discount_amount, tax_rate, tax_amount, total, created_at
                )
                VALUES (
                    :id, :tenant_id, :invoice_id, :product_id, 'material', :description,
                    1, :subtotal, 0, 18, :tax_amount, :total, :now
                )
                """,
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                invoice_id=invoice_id,
                product_id=MATERIAL_KIT_ID,
                description=f"Invoice line for {number}",
                subtotal=round(total / 1.18, 2),
                tax_amount=round(total - (total / 1.18), 2),
                total=total,
                now=now,
            )

        await execute(
            conn,
            """
            INSERT INTO payments (
                id, tenant_id, payment_number, invoice_id, client_id, amount,
                payment_date, payment_method, reference_number, notes, created_by, created_at
            )
            VALUES (
                :id, :tenant_id, 'CLIENT-DEMO-PAY-PAID', :invoice_id, :client_id, 14160,
                :payment_date, 'BANK_TRANSFER', 'UTR-DEMO-001', 'Seeded paid invoice payment', :created_by, :now
            )
            """,
            id=uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1f201"),
            tenant_id=TENANT_ID,
            invoice_id=INVOICE_PAID_ID,
            client_id=CLIENT_ID,
            payment_date=today - timedelta(days=8),
            created_by=CLIENT_USER_ID,
            now=now,
        )

        await execute(
            conn,
            """
            INSERT INTO client_notification_settings (
                id, tenant_id, client_id, user_id,
                order_confirmed, order_shipped, order_delivered, invoice_overdue, low_credit, marketing,
                created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :client_id, :user_id,
                true, true, true, true, true, false,
                :now, :now
            )
            """,
            id=uuid.UUID("7f3b1d54-8e8a-4d5c-9a0d-1ef8c0a1f301"),
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            user_id=CLIENT_USER_ID,
            now=now,
        )

        notifications = [
            ("ORDER_CONFIRMED", "Order CLIENT-DEMO-CONFIRMED confirmed", "Your order has been confirmed.", "sales_order", ORDER_CONFIRMED_ID),
            ("ORDER_SHIPPED", "Order CLIENT-DEMO-SHIPPED shipped", "Your order is on the way.", "sales_order", ORDER_SHIPPED_ID),
            ("INVOICE_OVERDUE", "Invoice CLIENT-DEMO-INV-OVERDUE overdue", "One invoice is overdue.", "invoice", INVOICE_OVERDUE_ID),
            ("LOW_CREDIT", "Low credit remaining", "Available credit is below 20 percent.", "client", CLIENT_ID),
        ]
        for ntype, title, message, ref_type, ref_id in notifications:
            await execute(
                conn,
                """
                INSERT INTO notifications (
                    id, tenant_id, user_id, type, title, message,
                    reference_type, reference_id, is_read, sent_at, email_sent
                )
                VALUES (
                    :id, :tenant_id, :user_id, :type, :title, :message,
                    :reference_type, :reference_id, false, :now, false
                )
                """,
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                user_id=CLIENT_USER_ID,
                type=ntype,
                title=title,
                message=message,
                reference_type=ref_type,
                reference_id=ref_id,
                now=now,
            )

    await engine.dispose()
    print("CLIENT_PORTAL_DEMO_SEEDED")
    print(f"Frontend URL: http://localhost:3000/client/login")
    print(f"Email: {CLIENT_EMAIL}")
    print(f"Password: {CLIENT_PASSWORD}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Client ID: {CLIENT_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
