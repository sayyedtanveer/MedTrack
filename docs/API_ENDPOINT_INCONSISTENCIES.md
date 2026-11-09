# API Endpoint URL Inconsistencies Report

## Overview
Analysis of all service files in `frontend/src/services` for URL trailing slash inconsistencies in apiClient calls.

---

## Key Findings

### Pattern 1: Manufacturing Endpoints (WITH Trailing Slashes)
**Files affected:**
- `operation.service.ts` 
- `operations.service.ts`
- `workstations.service.ts`

**Characteristic:** ALL endpoints consistently use trailing slashes across get, post, put, and delete operations.

**Example pattern:**
```
GET    /manufacturing/operations/
GET    /manufacturing/operations/${id}/
POST   /manufacturing/operations/
PUT    /manufacturing/operations/${id}/
DELETE /manufacturing/operations/${id}/
```

---

### Pattern 2: All Other Endpoints (NO Trailing Slashes)
**Files affected:**
- `bom.service.ts`
- `material.service.ts`
- `product.service.ts`
- `inventory.service.ts`
- `users.service.ts`
- `delivery.service.ts`
- `sales.service.ts`
- `storekeeper.service.ts`
- `work-order.service.ts`
- `finance.service.ts`

**Characteristic:** ALL endpoints consistently use NO trailing slashes.

**Example pattern:**
```
GET    /inventory/materials
GET    /inventory/materials/${id}
POST   /inventory/materials
PUT    /inventory/materials/${id}
DELETE /inventory/materials/${id}
```

---

## Detailed File Analysis

### ✅ CONSISTENT (No Issues)

#### 1. **operation.service.ts** - ALL WITH TRAILING SLASHES
- Line 59: `GET /manufacturing/operations/`
- Line 67: `GET /manufacturing/operations/for-bom/`
- Line 75: `GET /manufacturing/operations/${id}/`
- Line 83: `POST /manufacturing/operations/`
- Line 91: `PUT /manufacturing/operations/${id}/`
- Line 99: `DELETE /manufacturing/operations/${id}/`
- Line 106: `POST /manufacturing/operations/${id}/deactivate/`
- Line 114: `POST /manufacturing/operations/${id}/reactivate/`

#### 2. **operations.service.ts** - ALL WITH TRAILING SLASHES
- Line 44: `GET /manufacturing/operations/`
- Line 52: `POST /manufacturing/operations/`
- Line 60: `PUT /manufacturing/operations/${id}/`
- Line 68: `DELETE /manufacturing/operations/${id}/`

#### 3. **workstations.service.ts** - ALL WITH TRAILING SLASHES
- Line 38: `GET /workstations/`
- Line 46: `GET /workstations/${id}/`
- Line 54: `POST /workstations/`
- Line 62: `PUT /workstations/${id}/`
- Line 70: `DELETE /workstations/${id}/`

#### 4. **bom.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 26: `GET /products/${productId}/boms` (no slash)
- Line 33: `GET /boms/${bomId}` (no slash)
- Line 42: `PUT /boms/${bomId}` (no slash)
- Line 57: `DELETE /boms/${bomId}` (no slash)
- Line 63: `GET /boms/${bomId}/tree` (no slash)
- Line 72: `GET /boms/${bomId}/cost` (no slash)

#### 5. **material.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 32: `GET /inventory/materials` (no slash)
- Line 37: `GET /inventory/materials/${id}` (no slash)
- Line 42: `POST /inventory/materials` (no slash)
- Line 47: `PUT /inventory/materials/${id}` (no slash)
- Line 52: `DELETE /inventory/materials/${id}` (no slash)

#### 6. **product.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 81: `GET /products/templates` (no slash)
- Line 86: `GET /products/templates/${id}` (no slash)
- Line 91: `POST /products/templates` (no slash)
- Line 96: `PUT /products/templates/${id}` (no slash)
- Line 116: `GET /products/variants/${id}` (no slash)
- Line 126: `PUT /products/variants/${id}` (no slash)

#### 7. **inventory.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 80: `GET /inventory/materials` (no slash)
- Line 94: `GET /inventory/materials/${id}` (no slash)
- Line 99: `POST /inventory/materials` (no slash)
- Line 104: `PUT /inventory/materials/${id}` (no slash)

#### 8. **users.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 26: `GET /users` (no slash)
- Line 31: `GET /users/${id}` (no slash)
- Line 36: `POST /users` (no slash)
- Line 49: `PUT /users/${id}` (no slash)
- Line 54: `POST /users/${id}/temporary-password` (no slash)

#### 9. **delivery.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 39: `GET /deliveries` (no slash)
- Line 51: `POST /deliveries` (no slash)
- Line 62: `POST /deliveries/${deliveryId}/ship` (no slash)
- Line 67: `POST /deliveries/${deliveryId}/deliver` (no slash)

#### 10. **sales.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 129: `POST /sales/clients` (no slash)
- Line 136: `GET /sales/clients/${clientId}` (no slash)
- Line 172: `DELETE /sales/clients/${clientId}` (no slash)
- Line 194: `POST /sales/orders` (no slash)
- Line 201: `GET /sales/orders/${orderId}` (no slash)
- Line 268: `DELETE /sales/orders/${orderId}/lines/${lineId}` (no slash)

#### 11. **storekeeper.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 101: `GET /storekeeper/issue-queue` (no slash)
- Line 102: `GET /storekeeper/shortage-queue` (no slash)
- Line 103: `GET /storekeeper/partially-issued-wo` (no slash)
- Line 115: `POST /storekeeper/issue-material` (no slash)
- Line 122: `POST /storekeeper/partial-issue` (no slash)
- Line 129: `POST /storekeeper/return-material` (no slash)

#### 12. **work-order.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 121: `GET /work-orders` (no slash)
- Line 128: `GET /work-orders/${id}` (no slash)
- Line 131: `POST /work-orders` (no slash)
- Line 134: `POST /work-orders/${id}/release` (no slash)
- Line 152: `GET /work-orders/${woId}/job-cards` (no slash)

#### 13. **finance.service.ts** - ALL WITHOUT TRAILING SLASHES
- Line 256: `POST /finance/invoices/from-so` (no slash)
- Line 267: `GET /finance/invoices` (no slash)
- Line 272: `GET /finance/invoices/${id}` (no slash)

---

## Inconsistency Summary

### NO INCONSISTENCIES WITHIN INDIVIDUAL FILES ✅

All 13 service files analyzed are internally consistent. Each file follows ONE of two patterns:
1. **Pattern A:** All endpoints have trailing slashes (3 files - manufacturing/workstations)
2. **Pattern B:** No trailing slashes (10 files - everything else)

### BUT: INCONSISTENCY ACROSS THE CODEBASE ⚠️

**The main issue:** Different API modules use different conventions:
- Manufacturing module (`/manufacturing/operations/`, `/workstations/`) = Trailing slashes
- All other modules (inventory, sales, products, users, etc.) = No trailing slashes

---

## Recommendation

**Action needed:** Standardize API endpoint conventions across the entire codebase. Choose ONE approach:

**Option 1: Remove all trailing slashes (RECOMMENDED)**
- Aligns with REST conventions (trailing slashes typically indicate collections)
- Requires changes to: `operation.service.ts`, `operations.service.ts`, `workstations.service.ts`

**Option 2: Add trailing slashes everywhere**
- Requires changes to 10 files
- Less common in REST APIs

**Option 3: Document the pattern**
- If the backend API requires this distinction, document why manufacturing endpoints differ

---

## Files to Fix (if standardizing to no trailing slashes)

| File | Issue | Lines |
|------|-------|-------|
| `operation.service.ts` | Remove trailing slashes from all endpoints | 59, 67, 75, 83, 91, 99, 106, 114 |
| `operations.service.ts` | Remove trailing slashes from all endpoints | 44, 52, 60, 68 |
| `workstations.service.ts` | Remove trailing slashes from all endpoints | 38, 46, 54, 62, 70 |
