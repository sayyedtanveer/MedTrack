# Subcontracting Gate 1 final implementation

## Release state

- Repository head is `20261117_subcontract_stock_ops` after `20261109_1145_add_is_default`. The revision adds the order composite unique constraint and the stock operation table. The operation key is tenant, order, action and operation UUID. The table stores the validated payload fingerprint, successful response code, response body and record creation timestamp.
- The configured PostgreSQL database was inspected in a read-only transaction. Alembic records `c84cb0239a28`. The operation table, composite order constraint, and some objects from the two intervening revisions already exist. The operation table was empty at the time of inspection. Reconcile those intervening Alembic revisions against the full deployed schema before rollout. Running an unqualified upgrade can try to recreate those objects. No upgrade, stamp or stock write ran on the configured database.
- The new revision provisions a fresh schema or adopts the exact existing table and constraints. It rejects a partially installed or incompatible operation schema. Downgrade protects both pre-existing tables and migration-created tables with committed replay records.

The handoff script is `db_scripts/subcontract_gate1_stock_operations.sql`. It creates the same schema or validates the exact existing objects and exits without changing them. It does not stamp Alembic. The operator runs the script manually. The handoff script itself was reviewed but not executed.

## Posting and completion

- Keyed issue, receipt and return requests run authorization and take the tenant-scoped order lock before reading the operation record. Canonical UUIDs and equivalent Decimal representations produce the same fingerprint. A matching operation replays the stored successful response, including after order completion. A changed payload for the same key returns HTTP 409. A new key allows another intentional partial posting. The operation and stock changes commit together.
- The web client supplies the key and reuses it for the same unresolved request in the current page session. Legacy requests without the header retain their API behavior and do not receive durable retry protection. Making the header mandatory needs an API rollout decision.
- Output fulfillment with open materials uses the existing `partially_received` state. The detail screen displays material reconciliation separately and hides the receive action when output is fulfilled. Receipt or return completes a new order only when the order has fulfilled output and every order-specific material balance reconciles. Historical completed orders remain completed. Their order details flag outstanding materials, unexplained stock records, or missing BOM snapshots. Commercial confirmation stays independent.
- BOM-optional orders continue to accept issues, receipts and returns. Returning outstanding issued material can close a fulfilled manual order. Receipts do not infer manual usage.

## Manual consumption proposal for approval

Add `POST /api/v1/subcontract/orders/{order_id}/consume-material` with `procurement:write` and a required `Idempotency-Key`. The body would contain `material_id`, a positive Decimal `quantity` at the existing stock posting precision, a required reason, and an optional work or document reference. Limit the action to active BOM-optional orders with issued material. Allow partial usage before or after output fulfillment while reconciliation is open.

Take the existing tenant order, supplier and inventory locks. Validate the order-specific available balance and protect every other order's vendor allocation. In the same transaction, debit the vendor bucket, create an outbound inventory transaction with an explicit manual consumption source, capture actor, reason and reference in persistent audit history, and store the committed response. Include explicitly posted manual consumption in subsequent stock allocation, returns, reconciliation and completion. Keep lot selection out of this version pending the lot custody model.

This proposal requires the new endpoint and an additive Alembic revision extending the operation action constraint with `consume`. Keep the existing RBAC scope and use the inventory transaction ledger for manual usage. No endpoint or action constraint change was implemented.

## Files

| File | Change |
| --- | --- |
| db_scripts/subcontract_gate1_stock_operations.sql | Manual installation or exact-schema validation script |
| alembic/versions/20261117_subcontract_stock_ops.py | Add or validate the operation schema and guard destructive downgrade |
| backend/app/infrastructure/persistence/models/subcontract_model.py | Register composite order constraint and stock operation ORM model |
| backend/app/interfaces/api/v1/routes/supply_chain.py | Read and record operation identities under the order lock, apply completion gating, expose reconciliation exceptions |
| frontend/src/services/supply-chain.service.ts | Send and reuse stock operation keys |
| frontend/src/modules/procurement/pages/SubcontractOrderDetailPage.tsx | Surface open materials and legacy completion exceptions |
| tests/integration/test_subcontract_stock_integrity.py | Exercise the real FastAPI middleware stack and transactional replay against disposable PostgreSQL |

## Verification

- Disposable PostgreSQL 17 and Alembic CLI — fresh upgrade, empty downgrade and re-upgrade passed. Adoption of an exact pre-existing schema passed. The pre-existing schema downgrade was blocked as designed.
- Disposable PostgreSQL 17 stock suite — 16 passed, including three requests-through-middleware tests covering authorization, cross-tenant denial, same-key concurrency and replay, changed payload, distinct partial receipts, rollback, manual reconciliation and historical exceptions. The application used signed test JWTs and an isolated session factory. The full deployed startup and browser were outside this run.
- Existing BOM costing, onboarding and reporting suites — 92 passed.

