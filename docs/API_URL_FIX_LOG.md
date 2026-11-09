# API URL Double Prefix Fix

## Issue
The frontend was calling API URLs with double `/api/v1` prefix:
```
http://localhost:3000/api/v1/api/v1/notifications/?unread_only=false&page=1&page_size=10
```

Result: **404 (Not Found)**

## Root Cause
Several service files were hardcoding the full `/api/v1` path in their constants, but the `apiClient` already has `baseURL` configured with `/api/v1`.

### Before (Wrong)
```typescript
// finance.service.ts
const BASE = "/api/v1/finance"
const REPORTS_BASE = "/api/v1/reports"
const NOTIF_BASE = "/api/v1/notifications"

// sales.service.ts  
const BASE_URL = '/api/v1/sales';
```

When combined with apiClient's baseURL:
- baseURL: `/api/v1`
- path: `/api/v1/notifications`
- Result: `/api/v1/api/v1/notifications` ❌

## Solution: Removed Duplicate Prefix
### After (Correct)
```typescript
// finance.service.ts
const BASE = "/finance"
const REPORTS_BASE = "/reports"
const NOTIF_BASE = "/notifications"

// sales.service.ts
const BASE_URL = '/sales';
```

Now combined with apiClient's baseURL:
- baseURL: `/api/v1`
- path: `/finance`
- Result: `/api/v1/finance` ✅

## Files Fixed
1. ✅ [frontend/src/services/finance.service.ts](frontend/src/services/finance.service.ts#L133-L135)
   - Changed BASE from `/api/v1/finance` to `/finance`
   - Changed REPORTS_BASE from `/api/v1/reports` to `/reports`
   - Changed NOTIF_BASE from `/api/v1/notifications` to `/notifications`

2. ✅ [frontend/src/services/sales.service.ts](frontend/src/services/sales.service.ts#L23)
   - Changed BASE_URL from `/api/v1/sales` to `/sales`

## How apiClient Configuration Works

### In api-client.ts
```typescript
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,  // Already includes /api/v1
  headers: {
    "Content-Type": "application/json",
  },
})
```

### In config/constants.ts
```typescript
export const API_BASE_URL = 
  import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
```

### Environment Variable (.env or .env.local)
```bash
VITE_API_URL=http://localhost:8000/api/v1
```

## Correct Usage Pattern
When using apiClient, use paths WITHOUT the `/api/v1` prefix:

```typescript
// Correct usage
apiClient.get('/notifications', { params })
apiClient.get('/finance/invoices', { params })
apiClient.post('/sales/orders', data)

// Not like this (results in double prefix)
apiClient.get('/api/v1/notifications', { params })  // ❌
```

## Verification
The notifications endpoint now correctly resolves to:
```
http://localhost:3000/api/v1/notifications/?unread_only=false&page=1&page_size=10
```
✅ Status 200 (OK) instead of 404

## Files That Follow Correct Pattern
- ✅ `auth.service.ts` - Uses `/auth/login`, `/auth/register-tenant`
- ✅ `product.service.ts` - Uses `/products/templates`
- ✅ `work-order.service.ts` - Uses `/work-orders`
- ✅ `bom.service.ts` - Uses `/bom/*`
- ✅ All other services follow the same pattern

## Best Practice Going Forward
Always use path WITHOUT `/api/v1` prefix when using apiClient:

```typescript
// Template for new service files
import { apiClient } from './api-client'

const BASE = '/my-resource'  // No /api/v1 prefix!

export const myService = {
  async list(params) {
    const response = await apiClient.get(`${BASE}`, { params })
    return response.data
  }
}
```

---

## Status
✅ **FIXED** - All API endpoints now resolve correctly with single `/api/v1` prefix
