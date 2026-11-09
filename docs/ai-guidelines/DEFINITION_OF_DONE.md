# MedTrack Definition of Done

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Purpose:** Mandatory quality checklist for all code changes  
**Applies To:** All engineers, AI agents, and code review  
**Minimum Passing Score:** 100% (all items checked)

---

## Overview

**Definition of Done** is a mandatory quality gate. Every change—bug fix, feature, refactor—must satisfy **ALL** items in this checklist before:
- Merging to develop or main branches
- Deploying to staging or production
- Claiming task completion

**Key Principle:** "Done" means production-ready, tested, auditable, and maintainable.

---

## 13-Point Checklist

### 1. REQUIREMENT MET

**Requirement:** The implemented solution addresses the original requirement completely, with no missing acceptance criteria or partially satisfied features.

**Verification:**
- [ ] Original requirement is documented (ticket, issue, spec)
- [ ] All acceptance criteria are satisfied
- [ ] No acceptance criteria were removed or modified
- [ ] Solution works end-to-end (user can complete their workflow)
- [ ] Edge cases and error paths work correctly
- [ ] Performance targets met (if specified)

**Evidence:** Provide the original requirement + screenshot/video demonstrating all criteria passing

**Examples:**
- ✅ User Story: "As a planner, I can create a work order from an approved sales order"
  - Acceptance Criteria: (1) Select SO from list, (2) Confirm BOM, (3) Set quantities, (4) Assign priority, (5) WO appears in work order list
  - Evidence: Video showing all 5 steps working
- ❌ Feature: "Add low-stock alerts"
  - Only implemented in UI, backend doesn't trigger alerts
  - Missing: Email notifications to planners

---

### 2. ARCHITECTURE VALIDATED

**Requirement:** Changes follow DDD layer boundaries and don't introduce architectural violations (tight coupling, cross-layer dependencies, or broken CQRS separation).

**Verification:**
- [ ] Domain logic is in `domain/` (business rules, entities, exceptions)
- [ ] Use cases are in `application/` (commands, queries, handlers)
- [ ] Persistence is in `infrastructure/` (repositories, models, ORM)
- [ ] HTTP layer is in `interfaces/` (routes, schemas, middleware)
- [ ] No business logic in routes or views
- [ ] No database access in domain layer
- [ ] CQRS separation maintained (commands = write, queries = read)
- [ ] Dependency flow is downward only (routes → handlers → repos → domain)
- [ ] No circular dependencies

**Evidence:** Provide file structure diagram or list of affected files with layer classification

**Examples:**
- ✅ Change adds low-stock alert logic
  - Domain: `domain/inventory/events/low_stock_alert_event.py` (event definition)
  - Application: `application/inventory/handlers/inventory_handlers.py` (trigger logic)
  - Infrastructure: `infrastructure/persistence/repositories/inventory_repository.py` (query stock levels)
  - Interfaces: `interfaces/api/v1/routes/inventory_routes.py` (endpoint to configure alert threshold)
- ❌ Change adds business logic directly in route handler
  ```python
  @router.post("/work-orders")
  async def create_work_order(request):
      # ❌ Business logic here — should be in application/ handler
      if quantity > available_stock:
          raise Exception("Not enough stock")
      return {"id": wo_id}
  ```

---

### 3. BUSINESS RULES ENFORCED

**Requirement:** All relevant business rules are enforced, and the implementation respects manufacturing workflows, inventory constraints, and financial calculations.

**Verification:**
- [ ] Bill of Materials are versioned correctly (new version = new BOM, active version = only one active)
- [ ] Work order status transitions follow the state machine (DRAFT → RELEASED → STARTED → COMPLETED → CLOSED, no backtracking)
- [ ] Inventory reservations prevent double-booking and lock materials until WO completion
- [ ] Materials consumed on WO completion (inventory decreased), not on release
- [ ] GRN quantities cannot exceed PO quantities (ExcessiveGRNError if violated)
- [ ] Sales orders cannot move to manufacturing without approval
- [ ] Quality inspections required for incoming materials
- [ ] Low-stock alerts triggered at reorder point
- [ ] Soft deletes respected (no hard deletes)
- [ ] Scrap quantities accounted for in BOM explosions
- [ ] Subcontracting workflows correct (issued → consumed → returned, with separate counts)
- [ ] Multi-warehouse transfers tracked correctly

**Evidence:** List which business rules apply + proof (unit test, integration test, or screenshot showing rule enforcement)

**Examples:**
- ✅ Work order status transition change
  - Business Rule: "WO status DRAFT → RELEASED → STARTED → COMPLETED → CLOSED (no backtracking, no skipping)"
  - Evidence: 
    ```python
    @pytest.mark.unit
    def test_work_order_cannot_transition_backward():
        wo = WorkOrder(status=WorkOrderStatus.STARTED)
        with pytest.raises(InvalidStateTransitionError):
            wo.set_status(WorkOrderStatus.RELEASED)  # Can't go backward
    ```
- ❌ Inventory reservation change missing verification
  - Business Rule: "Materials reserved on WO release cannot be used by other WOs"
  - Missing Evidence: No test showing two WOs cannot reserve same material

---

### 4. MULTI-TENANT ISOLATION PRESERVED

**Requirement:** Changes maintain complete data isolation. One tenant's data is never visible to another tenant, and tenant context comes from JWT only.

**Verification:**
- [ ] Tenant extracted from JWT "tid" claim only (never from request parameters or headers)
- [ ] Every SELECT query includes `WHERE tenant_id = ...` filter
- [ ] Every INSERT/UPDATE sets `tenant_id` from context (not from input)
- [ ] All DELETE operations mark soft deletes with `is_deleted = true`
- [ ] Soft delete queries include `WHERE is_deleted = false`
- [ ] Logs include `tenant_id` in structured log context
- [ ] Tests verify tenant isolation (tenant1 cannot see tenant2's data)
- [ ] Repository methods accept `tenant_id` parameter explicitly

**Evidence:** 
- Provide code snippet showing tenant extraction from JWT
- Provide query showing tenant filter
- Provide integration test showing isolation verification

**Examples:**
- ✅ Material list endpoint with tenant isolation
  ```python
  # Route handler (routes/material_routes.py)
  @router.get("/materials")
  async def list_materials(handler: MaterialHandler = Depends()):
      query = ListMaterialsQuery()
      return await handler.handle_list_materials(query)
  
  # Handler (handlers/material_handlers.py)
  async def handle_list_materials(self, query: ListMaterialsQuery) -> List[MaterialResponse]:
      tenant_id = get_tenant_id()  # From JWT, not request
      materials = await self.repo.list_by_tenant(tenant_id)
      return [MaterialResponse.from_entity(m) for m in materials]
  
  # Repository (repositories/material_repository.py)
  async def list_by_tenant(self, tenant_id: UUID) -> List[Material]:
      stmt = select(MaterialModel).where(
          MaterialModel.tenant_id == tenant_id,  # ← Filter by tenant
          MaterialModel.is_deleted == False      # ← Soft delete check
      )
      results = await session.execute(stmt)
      return [Material.from_model(m) for m in results.scalars()]
  
  # Test (tests/integration/test_material_isolation.py)
  @pytest.mark.asyncio
  async def test_material_list_tenant_isolation(db_session):
      tenant1_id = uuid.uuid4()
      tenant2_id = uuid.uuid4()
      
      repo = MaterialRepository(db_session)
      mat1 = Material(id=uuid.uuid4(), code="MAT-001", tenant_id=tenant1_id)
      mat2 = Material(id=uuid.uuid4(), code="MAT-002", tenant_id=tenant2_id)
      
      await repo.save(mat1)
      await repo.save(mat2)
      
      # Tenant1 queries
      results = await repo.list_by_tenant(tenant1_id)
      assert len(results) == 1
      assert results[0].code == "MAT-001"
      # ← Tenant2's material is NOT visible
  ```
- ❌ Query missing tenant filter
  ```python
  # ❌ Wrong: No tenant_id filter
  stmt = select(MaterialModel).where(MaterialModel.status == "ACTIVE")
  # Could return materials from other tenants
  ```

---

### 5. AUTHORIZATION & RBAC ENFORCED

**Requirement:** Role-based access control is enforced. Users can only perform actions their role permits.

**Verification:**
- [ ] RBAC check exists on endpoint (or middleware for cross-cutting)
- [ ] Permission error returns 403 Forbidden (not 500 or 401)
- [ ] Permission denial is logged with user + resource
- [ ] Role has permission documented in PERMISSIONS constant
- [ ] Tests verify both allowed and denied scenarios

**Evidence:** 
- List roles with permissions for this feature
- Provide code showing RBAC check
- Provide test showing denied access

**Examples:**
- ✅ Work order release endpoint with RBAC
  ```python
  PERMISSIONS = {
      "work_order:release": ["ADMIN", "MANAGER", "PLANNER"],
      # ← Only these roles can release
  }
  
  @router.post("/work-orders/{id}/release", dependencies=[Depends(rbac("work_order:release"))])
  async def release_work_order(id: UUID, handler: WorkOrderHandler = Depends()):
      return await handler.handle_release_work_order(id)
  
  @pytest.mark.asyncio
  async def test_work_order_release_rbac():
      # Allowed: ADMIN, MANAGER, PLANNER
      # Denied: OPERATOR, STOREKEEPER, SALES, WORKER, etc.
      pass
  ```
- ❌ No RBAC check
  ```python
  @router.post("/work-orders/{id}/release")
  async def release_work_order(id: UUID):
      # ❌ Any authenticated user can release
      # Missing RBAC check
      pass
  ```

---

### 6. DATABASE SCHEMA & MIGRATIONS

**Requirement:** If database schema changed, migrations are created and tested.

**Verification:**
- [ ] Schema change requires Alembic migration (if adding/modifying columns or tables)
- [ ] Migration file exists in `alembic/versions/`
- [ ] Migration tested locally (`alembic upgrade head`, then queries work)
- [ ] Migration can be reverted (`alembic downgrade -1`, tables restored)
- [ ] Migration includes new indexes (on tenant_id, status, foreign keys)
- [ ] Migration includes soft delete columns if new table
- [ ] Migration includes audit columns (created_at, created_by, updated_at, updated_by)
- [ ] No hard deletes—only soft deletes with `is_deleted` and `deleted_at`
- [ ] Schema follows naming conventions (snake_case, plural table names)
- [ ] No circular foreign keys

**Evidence:** 
- Provide migration file name
- Provide before/after schema
- Provide upgrade + downgrade test output

**Examples:**
- ✅ Migration for new table
  ```python
  # alembic/versions/20261109_add_quality_inspection_table.py
  def upgrade():
      op.create_table(
          'quality_inspections',
          sa.Column('id', sa.UUID(), primary_key=True),
          sa.Column('tenant_id', sa.UUID(), nullable=False),
          sa.Column('is_deleted', sa.Boolean(), default=False),
          sa.Column('deleted_at', sa.DateTime(), nullable=True),
          sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
          sa.Column('created_by', sa.UUID(), nullable=False),
          sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
          sa.Column('updated_by', sa.UUID(), nullable=False),
          
          sa.Column('material_id', sa.UUID(), nullable=False),
          sa.Column('status', sa.Enum(InspectionStatus), default='PENDING'),
          
          sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
          sa.ForeignKeyConstraint(['material_id'], ['materials.id']),
          sa.ForeignKeyConstraint(['created_by'], ['users.id']),
          sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
      )
      op.create_index('idx_quality_inspections_tenant_status', 'quality_inspections', ['tenant_id', 'status'])
  
  def downgrade():
      op.drop_table('quality_inspections')
  ```
  - Evidence: `alembic upgrade head && psql -c "SELECT * FROM quality_inspections LIMIT 1"` (works)
             `alembic downgrade -1 && psql -c "SELECT * FROM quality_inspections"` (table gone)

- ❌ Schema change without migration
  - Added column to `work_orders` table manually
  - No Alembic migration file
  - Other developers' local copies out of sync

---

### 7. AUTOMATED TESTS PASSING

**Requirement:** New and modified code has tests. All tests pass locally and in CI.

**Verification:**
- [ ] Unit tests exist for domain logic (75%+ coverage target)
- [ ] Integration tests exist for repositories and use cases
- [ ] E2E tests exist for new API endpoints
- [ ] All tests passing locally: `pytest tests/ --cov=backend/app --cov-report=term-missing`
- [ ] All tests passing in CI (GitHub Actions or similar)
- [ ] No test skips or xfail without justification (`@pytest.mark.skip`, `@pytest.mark.xfail`)
- [ ] Coverage metrics reported (≥75% for new code)
- [ ] Frontend component tests pass: `npm run test --run`
- [ ] No console.log or debug.print left in code
- [ ] Flaky tests identified and fixed (tests pass 10 runs in a row)

**Evidence:** 
- Provide test file names
- Provide pytest output (PASSED count, coverage %)
- Provide CI build log showing green status

**Examples:**
- ✅ New feature with complete test coverage
  ```bash
  $ pytest tests/unit/domain/inventory/test_reservation.py -v
  test_reservation_blocks_other_reservations PASSED
  test_reservation_released_on_wo_completion PASSED
  test_insufficient_stock_raises_error PASSED
  
  $ pytest tests/ --cov=backend/app --cov-report=term-missing
  ======================== test session starts =========================
  collected 342 items
  PASSED: 334, FAILED: 0
  
  ----------- coverage: platform win32, python 3.11.0 -----------
  backend/app/domain/inventory/services/reservation_service.py    95%
  backend/app/application/inventory/handlers/reservation_handlers.py    88%
  
  ======================== 334 passed in 12.34s =========================
  ```
  - Evidence: Coverage report shows ≥75%

- ❌ Feature without tests
  - New endpoint added to `interfaces/api/v1/routes/procurement_routes.py`
  - No test file created
  - Coverage dropped from 76% to 71%

---

### 8. FRONTEND COMPONENTS & PAGES

**Requirement:** React components are fully typed, accessible, and tested (if new or significantly modified).

**Verification:**
- [ ] Components are functional (no class components)
- [ ] All props fully typed with TypeScript (no `any`)
- [ ] Return type is explicit (React.ReactElement or JSX.Element)
- [ ] Error boundaries implemented for risky components
- [ ] Loading states handled (show spinner while fetching)
- [ ] Error states handled (show error message, not crash)
- [ ] Empty state handled (show message when no data)
- [ ] Keyboard navigation works (tab order, Enter to submit)
- [ ] ARIA labels present for screen readers
- [ ] Mobile responsive (tested at 375px width)
- [ ] Component tests written (Vitest + React Testing Library)
- [ ] Snapshot tests NOT used (brittle, hard to maintain)

**Evidence:**
- Provide component file with TypeScript types
- Provide test file
- Provide screenshot at mobile width

**Examples:**
- ✅ Fully typed React component
  ```typescript
  // modules/inventory/components/MaterialTable.tsx
  interface Material {
    id: string;
    code: string;
    name: string;
    quantity: number;
  }
  
  interface MaterialTableProps {
    materials: Material[];
    loading: boolean;
    error: Error | null;
    onSelect?: (material: Material) => void;
  }
  
  export const MaterialTable: React.FC<MaterialTableProps> = ({
    materials,
    loading,
    error,
    onSelect
  }) => {
    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorMessage error={error} />;
    if (!materials.length) return <EmptyState message="No materials found" />;
    
    return (
      <table role="table" aria-label="Materials">
        {/* Table content */}
      </table>
    );
  };
  
  // modules/inventory/components/__tests__/MaterialTable.test.tsx
  describe('MaterialTable', () => {
    it('shows loading spinner while loading', () => {
      const { getByRole } = render(
        <MaterialTable materials={[]} loading={true} error={null} />
      );
      expect(getByRole('status')).toBeInTheDocument();
    });
  });
  ```
- ❌ Component missing types and error handling
  ```typescript
  export const MaterialTable = ({ materials, loading, error, onSelect }) => {
    // ❌ No TypeScript types
    // ❌ No error boundary
    // ❌ No error/loading state handling
    return <table>{/* */}</table>;
  };
  ```

---

### 9. BACKEND CODE QUALITY

**Requirement:** Python code follows project standards: async-first, DDD boundaries, type hints, structured logging, error handling.

**Verification:**
- [ ] All functions have type hints (parameters + return type)
- [ ] All async I/O operations use `await` (no blocking calls)
- [ ] No hardcoded values (use config, environment variables)
- [ ] No debug print statements (use structured logging)
- [ ] No silent exception swallowing (log before re-raising or handle explicitly)
- [ ] Docstrings on public methods and classes
- [ ] Error messages are clear and actionable
- [ ] Complex logic has inline comments explaining "why"
- [ ] No TODO comments without issue references (e.g., `# TODO: TASK-123`)
- [ ] No unused imports
- [ ] Linting passes: `ruff check backend/app` (no violations)
- [ ] Type checking passes: `pyright backend/app` (no errors)
- [ ] Code review checklist followed

**Evidence:**
- Provide code snippet showing type hints
- Provide linting + type-check output (0 violations, 0 errors)
- Provide sample log output

**Examples:**
- ✅ Well-typed, logged, error-handled function
  ```python
  async def handle_release_work_order(
      self,
      cmd: ReleaseWorkOrderCommand,
      tenant_id: UUID
  ) -> ReleaseWorkOrderResponse:
      """Release a work order, reserving materials and updating status.
      
      Args:
          cmd: Release command with WO ID and quantities
          tenant_id: Current tenant context
      
      Returns:
          Response with updated WO ID and status
      
      Raises:
          WorkOrderNotFoundError: If WO doesn't exist
          InsufficientStockError: If materials insufficient
          InvalidStateTransitionError: If WO in wrong state
      """
      logger.info(
          "Releasing work order",
          extra={"work_order_id": str(cmd.work_order_id), "tenant_id": str(tenant_id)}
      )
      
      try:
          wo = await self.repo.get_by_id(tenant_id, cmd.work_order_id)
          if not wo:
              raise WorkOrderNotFoundError(cmd.work_order_id)
          
          # Business rule: Reserve materials before release
          await self.inventory_service.reserve_materials(
              tenant_id=tenant_id,
              materials=wo.bom.lines
          )
          
          wo.set_status(WorkOrderStatus.RELEASED)
          await self.uow.save(wo)
          
          logger.info("Work order released", extra={"work_order_id": str(wo.id)})
          return ReleaseWorkOrderResponse(id=wo.id, status=wo.status)
      
      except DomainException as e:
          logger.warning("Release failed", extra={"error": str(e)})
          raise
  ```
  - Evidence: `ruff check` (0 violations), `pyright` (0 errors), structured log output

- ❌ Code missing types and logging
  ```python
  def release_work_order(cmd):
      # ❌ No type hints
      wo = get_work_order(cmd.id)
      # ❌ No error handling
      reserve_materials(wo.materials)
      print(f"Released {wo.id}")  # ❌ Debug print, not structured log
      return wo
  ```

---

### 10. NO UNRELATED CHANGES

**Requirement:** Commits contain ONLY changes necessary to address the requirement. No refactoring, formatting, or scope creep.

**Verification:**
- [ ] Git diff contains only files needed for this feature/fix
- [ ] No whitespace-only changes or reformatting
- [ ] No renaming unrelated functions or variables
- [ ] No adding "nice-to-have" features
- [ ] No removing unrelated dead code
- [ ] If refactoring needed, create separate issue/PR
- [ ] Commit messages are clear and reference issue
- [ ] PR description explains what and why

**Evidence:**
- Provide `git log --oneline` showing commit message
- Provide `git diff --stat` showing files changed

**Examples:**
- ✅ Focused commit
  ```
  $ git log --oneline -1
  TASK-456: Add low-stock alert threshold to material API
  
  $ git diff --stat
   backend/app/domain/inventory/entities/material_entity.py         |  5 +++++
   backend/app/application/inventory/handlers/inventory_handlers.py | 12 ++++++++++++
   backend/app/interfaces/api/v1/routes/inventory_routes.py         |  8 ++++++++
   backend/app/interfaces/api/v1/schemas/material_schemas.py        |  3 +++
   backend/app/tests/integration/test_inventory_handlers.py         | 15 +++++++++++++++
   4 files changed, 43 insertions(+), 0 deletions(-)
  ```
  - All changes related to low-stock alert threshold

- ❌ Scope creep
  ```
  $ git diff --stat
   backend/app/domain/inventory/entities/material_entity.py         |  5 +++++
   backend/app/domain/manufacturing/entities/work_order_entity.py   | 25 +++++++++++++++++++++++++
   backend/app/interfaces/api/v1/routes/inventory_routes.py         | 50 ++++++++++++++++++++++++++++++++++++++++++++++++++
   frontend/src/modules/inventory/components/MaterialTable.tsx      | 100 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
   frontend/src/modules/sales/pages/SalesOrderListPage.tsx          |  20 ++++++++++++++++++++
   9 files changed, 250 insertions(+), 35 deletions(-)
  ```
  - Task: "Add low-stock alert threshold"
  - But also: Modified work orders, sales orders, UI components
  - ❌ Scope creep; should be separate PRs

---

### 11. GIT COMMIT REVIEW

**Requirement:** Changes are committed with clear messages and follow branching strategy.

**Verification:**
- [ ] Branching strategy followed (feature/TASK-ID, bugfix/ISSUE-ID, never direct to main/develop)
- [ ] Commits are atomic (one logical change per commit, not "work in progress")
- [ ] Commit messages are clear: "TASK-ID: What changed and why"
- [ ] No merge commits into feature branch (rebase if needed)
- [ ] No force-push to shared branches (main, develop)
- [ ] PR/MR links issue tracker
- [ ] PR/MR description explains context and testing

**Evidence:**
- Provide branch name
- Provide commit messages
- Provide PR description

**Examples:**
- ✅ Clean commit history
  ```
  $ git log --oneline feature/TASK-456-low-stock-alerts...develop
  abc1234 TASK-456: Add low-stock alert threshold to material entity
  def5678 TASK-456: Implement alert trigger in inventory service
  ghi9012 TASK-456: Add low-stock alert API endpoint with RBAC
  jkl3456 TASK-456: Add integration tests for alert workflow
  ```
  - Branch: `feature/TASK-456-low-stock-alerts`
  - Each commit is atomic and clear

- ❌ Messy commit history
  ```
  $ git log --oneline
  abc1234 work in progress
  def5678 fixing stuff
  ghi9012 more fixes
  jkl3456 final version???
  ```
  - Commits don't explain intent
  - No issue references
  - Not atomic

---

### 12. DOCUMENTED LIMITATIONS & KNOWN ISSUES

**Requirement:** If a known limitation, partial implementation, or tech debt exists, it's documented.

**Verification:**
- [ ] No known bugs silently shipped
- [ ] Temporary workarounds are commented with issue reference
- [ ] Performance optimizations deferred are noted (with TASK-ID)
- [ ] Incomplete features flagged with migration plan
- [ ] Client-side validation matches server-side validation (or noted why)
- [ ] CHANGELOG.md updated with breaking changes (if any)

**Evidence:**
- Provide code comments with issue references
- Provide CHANGELOG entry

**Examples:**
- ✅ Documented limitation
  ```python
  # LIMITATION: Low-stock alerts currently polled every 5 minutes
  # TODO: TASK-789 - Implement event-driven alerts for real-time notification
  # Workaround: Operators manually check inventory dashboard
  async def check_low_stock(self, tenant_id: UUID):
      """Check materials below reorder point and trigger alerts."""
      materials = await self.repo.list_below_reorder_point(tenant_id)
      for material in materials:
          await self.event_dispatcher.publish(LowStockAlertEvent(material.id))
  ```
  - CHANGELOG.md:
    ```
    ## [1.0.0] - 2026-11-09
    ### Added
    - Low-stock alerts (polled every 5 minutes)
    
    ### Known Issues
    - Alerts not real-time; consider event-driven implementation (TASK-789)
    ```

- ❌ Silent bug
  - Low-stock alerts don't trigger for vendors in China
  - No comment, no issue, just a silent bug
  - Discovered in production

---

### 13. SECURITY & COMPLIANCE VERIFIED

**Requirement:** Changes don't introduce security vulnerabilities or compliance gaps.

**Verification:**
- [ ] No hardcoded secrets (API keys, tokens, passwords)
- [ ] No sensitive data in logs (passwords, credit cards, PII)
- [ ] Input validation via Pydantic schemas (SQLi prevention)
- [ ] SQL queries parameterized (no string concatenation)
- [ ] CORS properly configured (never `allow_origins=["*"]`)
- [ ] HTTPS enforced in production
- [ ] Passwords hashed with bcrypt (12+ rounds)
- [ ] JWT tokens have expiration
- [ ] Multi-tenant isolation enforced
- [ ] Audit logging captures all mutations
- [ ] No authentication/authorization bypasses
- [ ] Third-party dependencies checked for vulnerabilities (`pip audit`)

**Evidence:**
- Provide security checklist items
- Provide `pip audit` output (0 vulnerabilities)
- Provide code snippet showing input validation

**Examples:**
- ✅ Secure implementation
  ```python
  # ✅ Input validated with Pydantic
  class CreateMaterialRequest(BaseModel):
      code: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z0-9-]+$")
      # Pattern prevents injection
  
  # ✅ SQL parameterized
  stmt = select(Material).where(Material.code == code)  # SQLAlchemy handles escaping
  
  # ✅ Password hashed
  hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
  
  # ✅ JWT with expiration
  token = jwt.encode(
      {"sub": user_id, "exp": datetime.utcnow() + timedelta(hours=24)},
      secret_key
  )
  
  # ✅ Audit logged
  logger.info("Material created", extra={"material_id": str(id), "created_by": str(user_id)})
  ```
  - Evidence: `pip audit` output showing 0 vulnerabilities

- ❌ Security gap
  ```python
  # ❌ No input validation
  stmt = select(Material).where(Material.code == code)  # Code could be SQL injection
  
  # ❌ Secret in code
  API_KEY = "sk-12345abcde"  # ❌ Hardcoded
  
  # ❌ Password not hashed
  user.password = password  # ❌ Plaintext
  ```

---

## Implementation Report Template

Use this template after completing a task to summarize for code review:

```markdown
## Implementation Report: [TASK-ID] - [Feature Name]

### Requirement Summary
[One paragraph explaining what was implemented]

### Changes Made
- **File 1:** Description of changes
- **File 2:** Description of changes
- **File 3:** Description of changes

### Business Logic Verified
- ✓ [Business rule 1] — verified via [test name or screenshot]
- ✓ [Business rule 2] — verified via [test name or screenshot]

### Checklist Status (Definition of Done)
- ✓ Requirement met (acceptance criteria verified)
- ✓ Architecture validated (DDD layers correct)
- ✓ Business rules enforced (all workflows verified)
- ✓ Multi-tenant isolation preserved (test proves isolation)
- ✓ Authorization enforced (RBAC check present)
- ✓ Database migrations applied (alembic upgrade head successful)
- ✓ Tests passing (pytest coverage 82%)
- ✓ Frontend components typed (TypeScript strict mode)
- ✓ Backend code quality (ruff 0 violations, pyright 0 errors)
- ✓ No unrelated changes (only feature files modified)
- ✓ Git commits clean (3 atomic commits with clear messages)
- ✓ Limitations documented (TASK-789 referenced for future optimization)
- ✓ Security verified (pip audit 0 vulnerabilities, no secrets in logs)

### Test Evidence
- Unit tests: 24 passing
- Integration tests: 8 passing
- E2E tests: 3 passing
- Coverage: 82% (target 75%)

### Deployment Notes
- Breaking changes: None
- Database migration: 1 (alembic/versions/20261109_add_low_stock_alerts.py)
- Feature flags: None
- Estimated deployment time: 5 minutes

### Sign-Off
✅ Ready for: Code Review → Testing → Production Deploy
```

---

## Examples: Definition of Done in Action

### Example 1: Feature (New Low-Stock Alert System)

**Task:** TASK-456 - Implement low-stock alerts

**Requirement Met?**
- ✓ Alert triggers when stock < reorder_point
- ✓ Alert sent to PLANNER and MANAGER roles
- ✓ Alert includes material code, current stock, reorder point
- ✓ Alerts configurable per material

**Architecture Valid?**
- ✓ Event defined in `domain/inventory/events/`
- ✓ Trigger logic in `application/inventory/handlers/`
- ✓ Persistence in `infrastructure/persistence/repositories/`
- ✓ CQRS separation maintained

**Business Rules Enforced?**
- ✓ Soft deletes respected (deleted materials don't trigger alerts)
- ✓ Multi-warehouse logic correct (alert = total < reorder point)
- ✓ Scrap accounted for (alert considers scrap % from BOM)

**Multi-Tenant Isolated?**
- ✓ Test proves Tenant A alerts don't appear in Tenant B UI
- ✓ Reorder point per-tenant configurable
- ✓ Logs include tenant_id

**Authorized?**
- ✓ RBAC check: only ADMIN, MANAGER, PLANNER can configure threshold
- ✓ RBAC check: all roles can VIEW alerts (but only receive if assigned)
- ✓ Test: OPERATOR cannot configure, receives 403 Forbidden

**Database Schema?**
- ✓ Migration: `alembic/versions/20261109_add_reorder_point.py`
- ✓ Adds `reorder_point` column to `materials` table
- ✓ Adds `low_stock_alerts_config` table
- ✓ Tested: `alembic upgrade head && alembic downgrade -1` ✓

**Tests Passing?**
- ✓ Unit: `test_low_stock_alert_trigger_at_threshold` ✓
- ✓ Integration: `test_low_stock_alert_multiwarehouse_aggregation` ✓
- ✓ E2E: `test_alert_api_endpoint_rbac` ✓
- ✓ Coverage: 88% (exceeds 75% target)

**Frontend Components?**
- ✓ `LowStockAlertBanner.tsx` fully typed, error-handled, accessible
- ✓ `AlertConfigurationModal.tsx` tested with Vitest
- ✓ Mobile responsive at 375px width
- ✓ ARIA labels for screen readers

**Backend Code Quality?**
- ✓ Ruff: 0 violations
- ✓ Pyright: 0 errors
- ✓ All functions typed
- ✓ Structured logging with context
- ✓ Error handling explicit

**No Unrelated Changes?**
- ✓ Git diff shows only inventory, notification, API changes
- ✓ No refactoring of unrelated work_orders module
- ✓ No whitespace changes

**Clean Commits?**
- ✓ Branch: `feature/TASK-456-low-stock-alerts`
- ✓ Commits: 4 atomic commits with clear messages
- ✓ No force-push to develop

**Limitations Documented?**
- ✓ Alerts polled every 5 minutes (not real-time)
- ✓ Comment: `# TODO: TASK-789 - event-driven alerts`

**Security Verified?**
- ✓ `pip audit`: 0 vulnerabilities
- ✓ No API keys or secrets in code
- ✓ No PII in logs
- ✓ Input validated with Pydantic

**PASSED:** 13/13 ✓ Ready for production deploy

---

### Example 2: Bug Fix (Work Order Status Validation)

**Task:** ISSUE-789 - Work orders can skip status states (e.g., DRAFT → COMPLETED)

**Requirement Met?**
- ✓ Work order status transitions enforced (DRAFT → RELEASED → STARTED → COMPLETED → CLOSED)
- ✓ Cannot skip steps (DRAFT → COMPLETED rejected)
- ✓ Cannot go backward (STARTED → RELEASED rejected)
- ✓ Can cancel from DRAFT, RELEASED, or STARTED

**Architecture Valid?**
- ✓ State machine logic in `domain/manufacturing/entities/work_order_entity.py`
- ✓ Validation before persistence in repository
- ✓ Exception `InvalidStateTransitionError` raised appropriately

**Business Rules Enforced?**
- ✓ Status transitions follow manufacturing workflow
- ✓ State machine validated with state diagram

**Multi-Tenant Isolated?**
- ✓ Tenant context preserved in queries
- ✓ Logs include tenant_id
- ✓ Test verifies Tenant A WO status changes don't affect Tenant B

**Authorized?**
- ✓ RBAC enforced on each status transition endpoint
- ✓ Only PLANNER can RELEASE
- ✓ Only OPERATOR can START/COMPLETE
- ✓ Only MANAGER can CANCEL

**Database Schema?**
- ✓ No schema changes needed
- ✓ Existing status enum already contains all valid states

**Tests Passing?**
- ✓ Unit: `test_work_order_status_transition_validation` ✓
- ✓ Integration: `test_invalid_transition_rejected_with_error` ✓
- ✓ Coverage: 91% for WO module

**Frontend Components?**
- ✓ Buttons grayed out for invalid transitions
- ✓ Error message shown when attempting invalid transition
- ✓ No component changes needed (backend fixed)

**Backend Code Quality?**
- ✓ Ruff: 0 violations
- ✓ Pyright: 0 errors
- ✓ Clear error messages for debugging

**No Unrelated Changes?**
- ✓ Only modified work_order_entity.py validation logic
- ✓ No refactoring of other modules

**Clean Commits?**
- ✓ Branch: `bugfix/ISSUE-789-work-order-status-validation`
- ✓ Commit: 1 focused commit

**Limitations Documented?**
- ✓ No limitations; straightforward fix

**Security Verified?**
- ✓ No security impact; status validation only

**PASSED:** 13/13 ✓ Ready for production deploy

---

## Appendix: Common Failure Modes

### ❌ Incomplete Requirement
- **Sign:** "Done" but acceptance criteria not all satisfied
- **Fix:** Review checklist item #1 (Requirement Met)
- **Example:** "Add low-stock alerts" but alerts only email, no UI

### ❌ Broken Tenant Isolation
- **Sign:** Code compiles, tests pass, but one tenant sees another's data
- **Review:** Checklist item #4 (Multi-Tenant Isolation)
- **Example:** Forgot `WHERE tenant_id = ...` in one query

### ❌ RBAC Bypass
- **Sign:** User with OPERATOR role can release work orders (only PLANNER should)
- **Review:** Checklist item #5 (Authorization)
- **Example:** No RBAC check on the endpoint

### ❌ No Tests for New Code
- **Sign:** Coverage dropped after "new feature" commit
- **Review:** Checklist item #7 (Tests Passing)
- **Example:** Added 50 lines of code with 0 tests

### ❌ Silent Exception
- **Sign:** Feature doesn't work, but no error logged
- **Review:** Backend code quality checklist item #9
- **Example:** `try: ... except: pass`  (silently swallows error)

### ❌ Scope Creep
- **Sign:** PR touches 10 files when task was "fix typo"
- **Review:** Checklist item #10 (No Unrelated Changes)
- **Example:** Fixed typo, then refactored inventory service, then updated sales order API...

### ❌ Hardcoded Secrets
- **Sign:** API key or database password in source code
- **Review:** Security checklist item #13
- **Example:** `api_key = "sk-abc123xyz"`

### ❌ Database Schema Mismatch
- **Sign:** Local migrations applied, but CI database doesn't match
- **Review:** Checklist item #6 (Database Migrations)
- **Example:** Added column manually but forgot Alembic migration

---

## Sign-Off Criteria

**A change is "Done" when:**
1. ✅ It solves the stated problem
2. ✅ It follows the architecture
3. ✅ It enforces business rules
4. ✅ It isolates multi-tenant data
5. ✅ It checks permissions
6. ✅ It migrates the database (if needed)
7. ✅ It has passing tests
8. ✅ It has typed components and clean code
9. ✅ It makes only needed changes
10. ✅ It's committed cleanly
11. ✅ It documents limitations
12. ✅ It's secure

**All 13 items checked = Ready for production.**

---

**Last Updated:** November 9, 2026  
**Version:** 1.0.0  
**Status:** Production Ready

For questions, refer to `IMPLEMENTATION_WORKFLOW.md` (process) or `AGENTS.md` (principles).
