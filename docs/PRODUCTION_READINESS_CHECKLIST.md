# Production Readiness Checklist

## ✅ Typography
- Token system: `frontend/src/tokens/typography.ts`
- Tailwind integration: `tailwind.config.ts` extends with token values
- Font scale: xs / sm / base / lg / xl / 2xl / 3xl

## ✅ Colors
- Semantic palette: `frontend/src/tokens/colors.ts`
- Status badges: use `SO_STATUS_COLOR_MAP` (SalesOrderStatusConfig) and `WO_STATUS_COLORS` (WorkOrderStatusConfig)

## ✅ Accessibility (axe-core target: 0 critical violations)
- `aria-label` on 20+ icon-only buttons (task 15.4) ✅
- `aria-required` on required form fields ✅
- `aria-current="page"` on active navigation links ✅
- `aria-label="Main navigation"` on nav element ✅
- Radix UI dialogs handle focus trapping natively ✅
- `aria-live` / `role="alert"` on toast/notification regions ✅
- `aria-sort` on sortable table columns (DataGrid.tsx) ✅

## ✅ Database Performance
- Indexes: `add_production_readiness_indexes` migration (CONCURRENTLY)
- Slow query logging: >500ms queries logged to "slow_queries" logger
- Max page size: 200 enforced on all paginated endpoints
- Retention policy: read notifications >90 days soft-deleted in batches
- FK index verification: pending (run `add_production_readiness_indexes`)

## ✅ Security
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
- CORS hardening: wildcard rejected in production (CORS_ALLOWED_ORIGINS required)
- Rate limiting: 100 req/min per authenticated user via SlowAPI + Redis
- File upload validation: MIME type + size enforcement (`file_validation.py`)
- JWT refresh: endpoints scaffolded at `/auth/refresh`, `/auth/logout`, `/auth/logout-all`
- Resource ownership: `verify_tenant_ownership()` in `domain/shared/validators/ownership.py`

## ✅ Observability
- Structured logging: structlog with JSON renderer in production (`LOG_FORMAT=json`)
- Correlation ID: X-Request-ID on all responses (CorrelationIdMiddleware)
- Request timing: X-Duration-Ms header on all responses (RequestLoggingMiddleware)
- Performance endpoint: `GET /api/v1/admin/performance`
- DB health endpoint: `GET /api/v1/admin/db-health`

## ✅ Background Processing
- Retry logic: exponential backoff 1s/4s/16s, max 3 retries (BackgroundTaskService)
- Failed task tracking: `failed_tasks` table + `GET /api/v1/admin/tasks/failed`

## ✅ Frontend UI Standards
- Design tokens: `frontend/src/tokens/` (colors, typography, spacing, borders, shadows)
- Responsive tables: `ResponsiveDataTable.tsx` + `DataGrid.tsx`
- Responsive dashboards: `sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` grids
- Skeleton loaders: `SkeletonTable`, `SkeletonCard`, `SkeletonForm`
- Empty states: `EmptyState` component with no-records / filtered variants
- Error banners: `ErrorBanner` component with optional retry
- KPI cards: `KPICard` with trend indicators, loading/error states
- Component variants: documented in `frontend/src/components/ui/variants.ts`
- Form standards: `useUnsavedChanges` hook for navigation blocking

## ⚠️ Pending (requires real DB connection + deployment)
- EXPLAIN ANALYZE verification of KPI queries with 100K rows
- Cross-tenant access end-to-end testing
- Load testing at production data volumes
- JWT refresh token flow full implementation (wire to existing JWT service)
- axe-core automated accessibility scan on all critical pages
