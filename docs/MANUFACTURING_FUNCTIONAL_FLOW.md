# Manufacturing Functional Flow

This document maps the current manufacturing functional flow from Sales through Delivery and Finance.
It follows the format:

Step → Screen → API → DB → Status → Next Step

> Status values reflect the current audit state: Implemented, Partial, or Pending verification.

---

## 1. Create Sales Order

Step
Create Sales Order

Screen
Sales → Orders → New Order

API
POST /sales/orders

DB
sales_orders, sales_order_lines

Status
Implemented

Next Step
Submit for Approval

---

## 2. Submit Sales Order for Approval

Step
Submit for Approval

Screen
Sales Order Detail

API
POST /sales/orders/{id}/submit-approval

DB
sales_orders, approval_state

Status
Implemented

Next Step
Approve Sales Order

---

## 3. Approve Sales Order

Step
Approve Sales Order

Screen
Sales Order Detail

API
POST /sales/orders/{id}/approve

DB
sales_orders, order_status_history

Status
Implemented

Next Step
Confirm Sales Order

---

## 4. Confirm Sales Order

Step
Confirm Sales Order

Screen
Sales Order Detail

API
POST /sales/orders/{id}/confirm

DB
sales_orders, inventory_reservations, manufacturing_links

Status
Implemented

Next Step
Create Work Order

---

## 5. Create Work Order

Step
Create Work Order

Screen
Work Orders → New Work Order

API
POST /work-orders

DB
work_orders, work_order_materials

Status
Implemented

Next Step
Check Material Availability

---

## 6. Check Material Availability / Shortage Preview

Step
Check Material Availability

Screen
Work Order Create Page

API
GET /work-orders/material-availability

DB
BOM requirements, inventory stock, shortage preview

Status
Implemented

Next Step
Create Purchase Order if Shortage Exists

---

## 7. Create Purchase Order for Shortage (Optional)

Step
Create Purchase Order for Shortage

Screen
Procurement → Purchase Orders

API
POST /procurement/purchase-orders

DB
purchase_orders, purchase_order_lines

Status
Partial / Handoff available

Next Step
Release Work Order

---

## 8. Release Work Order

Step
Release Work Order

Screen
Work Order Detail

API
POST /work-orders/{id}/release

DB
work_orders, status transition

Status
Implemented

Next Step
Issue Materials

---

## 9. Issue Materials to Work Order

Step
Issue Materials

Screen
Inventory / Storekeeper Dashboard

API
POST /work-orders/{id}/issue-materials

DB
inventory_transactions, work_order_materials, stock movement

Status
Implemented via Storekeeper module

Next Step
Start Work Order

---

## 10. Start Work Order

Step
Start Work Order

Screen
Work Order Detail

API
POST /work-orders/{id}/start

DB
work_orders, execution_state

Status
Implemented

Next Step
Record Production

---

## 11. Record Production

Step
Record Production

Screen
Work Order Detail

API
POST /work-orders/{id}/record-production

DB
work_orders, production_results, scrap_data

Status
Implemented

Next Step
Complete Work Order

---

## 12. Complete Work Order

Step
Complete Work Order

Screen
Work Order Detail

API
POST /work-orders/{id}/complete

DB
work_orders, completed_quantity, status history

Status
Implemented

Next Step
QC Inspection

---

## 13. QC Inspection

Step
QC Inspection

Screen
Quality / QC Dashboard

API
GET /work-orders/qc/inspection-queue

DB
inspection_queue, produced_batches, quality_results

Status
Implemented

Next Step
QC Approval or Rejection

---

## 14. QC Approval / Rejection / Rework

Step
QC Approval or Rejection

Screen
Quality / QC Dashboard

API
POST /work-orders/qc/inspect or related QC actions

DB
quality_inspections, rework_queue, rejected_batches

Status
Partial / UI action wiring needs verification

Next Step
Create Delivery

---

## 15. Create Delivery

Step
Create Delivery

Screen
Sales → Deliveries

API
POST /deliveries

DB
deliveries, delivery_lines

Status
Implemented

Next Step
Ship Delivery

---

## 16. Ship Delivery

Step
Ship Delivery

Screen
Sales → Deliveries

API
POST /deliveries/{id}/ship

DB
deliveries, shipping_status

Status
Implemented

Next Step
Deliver Shipment

---

## 17. Deliver Shipment

Step
Deliver Shipment

Screen
Sales → Deliveries

API
POST /deliveries/{id}/deliver

DB
deliveries, delivery_status, delivery_completion

Status
Implemented

Next Step
Create Invoice

---

## 18. Create Invoice from Sales Order

Step
Create Invoice

Screen
Finance → Invoices → New Invoice

API
POST /finance/invoices/from-so

DB
invoices, invoice_lines, sales_order_reference

Status
Implemented

Next Step
Invoice Completion / Financial Close

---

## 19. Financial Close / Completed Flow

Step
Financial Close

Screen
Finance → Invoices / Invoice Detail

API
GET /finance/invoices/{id}

DB
invoices, financial_posting

Status
Implemented

Next Step
End of Flow

---

## Summary

The manufacturing flow is currently implemented across the following modules:
- Sales
- Work Orders
- Inventory / Storekeeper
- Procurement
- Quality / QC
- Finance

The main areas that still need stronger validation are:
- QC action execution from the dashboard
- End-to-end procurement handoff from shortage preview
- Full visibility of auto-generated invoices after delivery
