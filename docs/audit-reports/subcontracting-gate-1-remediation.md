# Subcontracting Gate 1 remediation

## Durable stock operation identity proposed for approval

The activity audit records what happened. It does not enforce a unique stock operation identity or retain the original response in the posting transaction. The existing workflow retry mechanism also does not provide this contract for the active subcontract HTTP routes.

The proposed SQLAlchemy model is SubcontractStockOperationModel. It maps to the following PostgreSQL schema. The SQL here documents the proposed Alembic upgrade. There is no executable migration in this change.

```sql
ALTER TABLE subcontract_orders
    ADD CONSTRAINT uq_subcontract_orders_tenant_id_id UNIQUE (tenant_id, id);

CREATE TABLE subcontract_stock_operations (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    subcontract_order_id UUID NOT NULL,
    action VARCHAR(16) NOT NULL,
    operation_id UUID NOT NULL,
    payload_sha256 BYTEA NOT NULL,
    response_status SMALLINT NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_subcontract_stock_operations
        PRIMARY KEY (tenant_id, subcontract_order_id, action, operation_id),
    CONSTRAINT fk_subcontract_stock_operations_order
        FOREIGN KEY (tenant_id, subcontract_order_id)
        REFERENCES subcontract_orders (tenant_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_subcontract_stock_operations_action
        CHECK (action IN ('issue', 'receive', 'return')),
    CONSTRAINT ck_subcontract_stock_operations_payload_hash
        CHECK (octet_length(payload_sha256) = 32),
    CONSTRAINT ck_subcontract_stock_operations_status
        CHECK (response_status BETWEEN 200 AND 299)
);
```

- Accept an operation UUID through an Idempotency-Key header for each issue, receipt, or return. The client creates it once per user action, saves it across retries, and generates a fresh key for each intentional partial posting.
- Hash validated request fields using SHA-256 over sorted UTF-8 JSON keys. Serialize UUIDs in lowercase canonical form and Decimal quantities as normalized decimal strings with no exponent. Resolve request aliases and defaults first. Omitted and null optional values are equivalent when the handler treats them identically. Preserve text exactly where it affects validation or posting. Hold these field semantics stable for existing keys through a deployment.
- Authenticate and authorize on every request. Lock the tenant-owned order row. Look up the operation before status eligibility so retries after fulfillment can replay. Return the saved status and body on an exact match and HTTP 409 for the same identity with a different hash.
- For a new identity, perform the existing stock posting under the order and inventory locks. Save the successful response and operation in the same transaction as that posting. Both roll back on failure. A concurrent retry waits on the same order lock and then reads the committed response. The primary key is a database-level guard.
- Upgrade by adding the composite order constraint and creating the operation table, with no historical backfill. Verify the unique constraint creation and table lock impact in the disposable environment before deployment. Roll out supporting clients before requiring the header on every mutation. Decide how long to retain replay records before any purge is enabled.
- Before the first recorded operation, the Alembic downgrade can drop the operation table and then remove the composite constraint. After use, dropping replay records would reopen the duplicate-posting window. Keep the table and guarded write path until writers have been stopped and replay obligations have been retired under an approved rollback plan.

## Completion and manual orders proposed for approval

- Output fulfilled means accepted output has reached the order quantity. Materials reconciled means every order-specific issue balance is zero after posted consumption and returns. Commercial charges confirmed is a separate condition.
- Keep the existing status contract during transition. Once the policy is approved, production completion should require both output fulfillment and material reconciliation. Charge confirmation should remain independent.
- Leave historical completed orders untouched. Flag completed orders with outstanding materials for review. Surface the order, issued quantity, posted consumption, returns, and open balance. Reconcile only through approved stock operations after confirming physical custody.
- Preserve BOM-optional manual orders. An output receipt on a manual order does not imply material consumption. Material issued to a manual order stays open until it is returned or a future authorized explicit consumption operation reconciles it. Approval is needed for that operation and for how manual orders may be closed when material was physically used.
- Existing legacy output mappings need reviewed correction if their stored type points to the wrong entity. The posting path rejects mismatched mappings. Approved BOM snapshots are used after approval even if the BOM is subsequently superseded.
- Input lot identities are validated and recorded on movements. The current schema does not allocate snapshot consumption to issue lots or represent split custody for a single Batch row. Batch-specific returns after consumption are rejected where allocation cannot be established. End-to-end input lot balances and physical lot transfer need a separate decision.

## Changed files

| File | Change |
| --- | --- |
| backend/app/interfaces/api/v1/routes/supply_chain.py | Tenant-scoped write locks, reference validation, receipt cap, BOM snapshot validation, and atomic posting on the active HTTP path |
| backend/app/interfaces/api/v1/schemas/supply_chain_schemas.py | Positive quantities within stored precision and batch reference bounds |
| backend/app/application/manufacturing/services/inventory_service.py | Order stock allocation checks, conserved returns, Decimal movement quantities, cumulative consumption, and output batch checks |
| frontend/src/modules/procurement/pages/SubcontractListPage.tsx | Sends the explicit material type for the existing semi-finished material selector |
| tests/integration/test_subcontract_stock_integrity.py | Isolated handler, rollback, and PostgreSQL concurrency tests |

Receipt limits reject overposting. Two same-sized valid partial requests are still interpreted as separate actions while durable operation identity is pending. The proposed completion policy and legacy data decisions have not been applied.


## Verification

- Disposable PostgreSQL 17 — 13 passed, including three concurrent posting cases, a rollback after attempted consumption, wrong BOM rejection, and approved snapshot use after BOM deactivation.
- Isolated onboarding, semi-finished BOM costing and reporting regressions — 92 passed.
- Frontend TypeScript — passed with the frontend project configuration.
- Durable replay and changed-payload conflicts remain pending migration approval. Tests invoke the route handlers with real database sessions. They do not exercise browser or HTTP middleware.
