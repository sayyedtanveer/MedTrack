# MedTrack Implementation Workflow

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Purpose:** Standardized process for all code changes (features, bug fixes, refactors)  
**Applies To:** All engineers, AI agents, and code review

---

## Overview

This document defines the mandatory 12-step workflow for implementing any change to MedTrack. The workflow ensures quality, correctness, security, and compliance with the DDD + CQRS architecture.

**Key Principle:** Understand before you build. Inspect before you change. Test before you claim success.

---

## 12-Step Implementation Workflow

### STEP 1: Understand the Requirement

**Goal:** Clarify exactly what needs to be done.

**Actions:**
1. Read the requirement/issue/ticket completely
2. Identify success criteria (what does "done" look like?)
3. Identify scope boundaries (what's included, what's excluded)
4. Ask clarifying questions if ambiguous
5. Document assumptions in writing

**Questions to Answer:**
- What business problem does this solve?
- Who are the users? What's their workflow?
- What data is affected?
- Are there edge cases or exceptions?
- What are the performance requirements?
- Are there compliance/audit requirements?

**Deliverable:** Written summary of requirement (one paragraph)

**Risk Flag:** If requirement is unclear after this step, STOP and clarify before proceeding.

---

### STEP 2: Inspect Existing Implementation

**Goal:** Understand what already exists to avoid duplicate work or breaking changes.

**Actions:**
1. **Check if feature already exists:**
   ```bash
   grep -r "feature_name" backend/app/ --include="*.py"
   grep -r "feature_name" frontend/src/ --include="*.tsx"
   ```

2. **Examine related models:**
   - Read ORM models in `backend/app/infrastructure/persistence/models/`
   - Check for existing data structures
   - Review database schema in migrations

3. **Examine related services:**
   - Read application handlers in `backend/app/application/*/`
   - Check for existing business logic
   - Review DDD entities in `backend/app/domain/*/`

4. **Examine related APIs:**
   - Check routes in `backend/app/interfaces/api/`
   - Review Pydantic schemas
   - Check for existing endpoints

5. **Examine related frontend:**
   - Read React components in `frontend/src/modules/*/`
   - Check for existing pages and workflows
   - Review API client services

**Deliverable:** List of existing files that touch this domain

**Risk Flag:** If you find partial implementation, determine if you're completing it or replacing it.

---

### STEP 3: Identify Impacted Modules

**Goal:** Map all layers and bounded contexts affected by this change.

**Architecture Layers:**
```
Database Layer
    ↑
ORM Models (infrastructure/persistence/models/)
    ↑
Repositories (infrastructure/persistence/repositories/)
    ↑
Domain Entities & Value Objects (domain/)
    ↑
Application Handlers & DTOs (application/)
    ↑
API Routes & Schemas (interfaces/api/)
    ↓
Frontend Components & Services (frontend/src/modules/)
```

**Actions:**
1. **Identify which layers are affected:**
   - Is database schema changing? → Database layer
   - Are models changing? → ORM layer
   - Is business logic changing? → Domain layer
   - Are endpoints changing? → API layer
   - Is UI changing? → Frontend layer

2. **Identify which bounded contexts are affected:**
   - Inventory, Manufacturing, Sales, Procurement, Quality, Finance, etc.
   - Check for cross-context dependencies

3. **Identify which roles need permissions:**
   - Does this feature require new permissions?
   - Does this feature check existing permissions?

**Deliverable:** Dependency map showing affected modules

**Risk Flag:** If change spans multiple bounded contexts, flag for architectural review.

---

### STEP 4: Trace Frontend-to-Backend-to-Database Flow

**Goal:** Understand the complete data flow end-to-end.

**Actions:**
1. **Start from frontend:**
   - What user action triggers this? (button click, form submit, etc.)
   - What React component handles it? (page, form, modal, etc.)
   - What API endpoint is called? (GET /api/v1/...?)

2. **Trace to backend:**
   - What route handler receives the request?
   - What schema validates the input (Pydantic)?
   - What service/handler processes the request?
   - What domain entity is modified?
   - What repository method is called?

3. **Trace to database:**
   - What table/model is queried or updated?
   - Are there foreign keys or constraints?
   - Is a transaction needed?
   - What about soft deletes and audit columns?

4. **Trace the response:**
   - What data is returned to frontend?
   - What API response schema is used?
   - Does frontend handle loading/error/empty states?

**Deliverable:** Sequence diagram or written trace (what calls what in order)

**Example Trace:**
```
User Action: Click "Release Work Order"
  ↓
Frontend: SalesOrderActionPanel.onRelease()
  ↓
API Call: PUT /api/v1/work-orders/{id}/release
  ↓
Backend: WorkOrderHandler.handle_release()
  ↓
Service: WorkflowOrchestrationService.on_work_order_released()
  ↓
Database: Update work_orders SET status='MATERIAL_PENDING'
  ↓
Event: Emit WorkOrderReleased domain event
  ↓
Response: { success: true, message: "..." }
```

**Risk Flag:** If flow is unclear or has gaps, investigate further before proceeding.

---

### STEP 5: Identify Dependencies and Side Effects

**Goal:** Understand what breaks if this changes.

**Actions:**
1. **Direct dependencies:**
   - What code imports or uses this code?
   - What tests import this code?
   - What APIs call this service?

2. **Indirect dependencies:**
   - What domain events are emitted?
   - What other services subscribe to these events?
   - What workflows are triggered?
   - What reports consume this data?

3. **Data dependencies:**
   - What queries rely on the current schema?
   - Are there stored procedures or views?
   - Are there ETL jobs that depend on this?

4. **UI dependencies:**
   - What pages display this data?
   - What tables or lists show this?
   - What dashboards depend on this?

5. **Authorization dependencies:**
   - What permissions are required?
   - What roles have these permissions?
   - Are there permission cascades?

**Deliverable:** Impact analysis (what breaks if this changes)

**Risk Flag:** If many dependents exist, coordinate changes carefully and flag for review.

---

### STEP 6: Check Existing Tests

**Goal:** Understand what's already tested and what you need to add.

**Actions:**
1. **Find existing tests:**
   ```bash
   find tests/ -name "*.py" | xargs grep -l "feature_name"
   find frontend/src/modules/ -name "*.test.tsx" | xargs grep -l "feature_name"
   ```

2. **Examine test patterns:**
   - Are unit tests present?
   - Are integration tests present?
   - Are E2E tests present?
   - What's the naming convention?
   - What fixtures/factories are used?

3. **Check test coverage:**
   - Is there 75%+ coverage for this module?
   - Are error cases tested?
   - Are edge cases tested?
   - Are authorization checks tested?

4. **Review test organization:**
   - Backend: `tests/unit/`, `tests/integration/`, `tests/e2e/`
   - Frontend: `**/__tests__/` alongside components

**Deliverable:** List of existing tests and gaps

**Risk Flag:** If coverage is low, commit to adding tests.

---

### STEP 7: Present Implementation Plan

**Goal:** Get approval before building.

**For Small Changes (low-risk bug fixes, UI tweaks):**
- Send plan to code reviewer
- Proceed if approved or if no feedback in 2 hours

**For Medium Changes (new API endpoint, database migration):**
- Present plan in meeting or document
- Get explicit approval from tech lead
- Document any assumptions or trade-offs

**For Large Changes (new bounded context, architecture change):**
- Present design document
- Get approval from architect and tech lead
- Plan for code review with multiple reviewers

**Plan Must Include:**
1. **Problem Statement** (1-2 sentences)
2. **Proposed Solution** (high-level approach)
3. **Files to Create** (new files)
4. **Files to Modify** (existing files)
5. **Database Changes** (migrations, schema)
6. **API Changes** (new endpoints, changed schemas)
7. **Business Logic Changes** (new rules, modifications)
8. **Security Impact** (auth, multi-tenancy, data isolation)
9. **Tests to Add** (unit, integration, E2E)
10. **Risks** (what could go wrong?)
11. **Estimated Effort** (hours)

**Deliverable:** Written implementation plan with approval

**Risk Flag:** Do not proceed without approval on high-risk changes.

---

### STEP 8: Obtain Approval for High-Risk Changes

**Goal:** Mitigate risk through expert review.

**High-Risk Indicators:**
- 🔴 Modifies multi-tenancy or data isolation logic
- 🔴 Modifies authentication or authorization
- 🔴 Changes database schema (migrations)
- 🔴 Affects inventory or financial calculations
- 🔴 Modifies work order status machine
- 🔴 Changes BOM or production workflow
- 🔴 Performance-sensitive code (N+1 queries, loops)
- 🟠 New external service integrations (payment, shipping, etc.)
- 🟠 Large data migrations
- 🟠 Backward compatibility breaking changes

**Approval Process:**
1. **Identify stakeholders** (tech lead, architect, domain expert)
2. **Present plan** with risk analysis
3. **Get written approval** (email, PR comment, meeting notes)
4. **Document approval** in commit message

**Deliverable:** Approval from stakeholder

**Risk Flag:** If approval is denied, understand the feedback and revise plan.

---

### STEP 9: Implement Minimum Necessary Changes

**Goal:** Make only the changes needed, nothing more.

**Implementation Rules:**
1. ✅ **DO:**
   - Follow existing code patterns
   - Reuse existing services and repositories
   - Use existing error handling conventions
   - Apply existing logging patterns
   - Use existing test fixtures and factories

2. ❌ **DON'T:**
   - Refactor unrelated code
   - "Clean up" files not touched by this change
   - Add new dependencies without justification
   - Introduce new abstractions not needed now
   - Remove old code you think is unused (search first!)

3. **Code Review Checklist:**
   - ✅ DDD layer separation (domain, application, infrastructure, interfaces)
   - ✅ CQRS separation (commands vs. queries)
   - ✅ Type safety (full type hints in Python and TypeScript)
   - ✅ Multi-tenancy (every query filters by tenant_id)
   - ✅ Async-first (all I/O is async, await used correctly)
   - ✅ Error handling (specific exceptions, no silent failures)
   - ✅ Soft deletes (no hard deletes, is_deleted checked)
   - ✅ Audit trail (created_by, updated_at, timestamps)
   - ✅ No sensitive data in logs
   - ✅ Security (authorization checks, input validation)

**Deliverable:** Code changes

**Risk Flag:** Review the diff carefully before committing.

---

### STEP 10: Run Tests and Validation

**Goal:** Verify the change works correctly.

**Backend Validation:**

```bash
# Type checking
pyright backend/app/

# Linting
ruff check backend/app/

# Unit tests
pytest tests/unit/ -v --cov=backend/app --cov-report=term-missing

# Integration tests
pytest tests/integration/ -v

# E2E tests (if applicable)
pytest tests/e2e/ -v -k "feature_name"

# Check for SQL injection, security issues
bandit -r backend/app/

# Database migration check
alembic current
alembic heads
```

**Frontend Validation:**

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Tests
npm run test -- --run

# Build
npm run build

# Check for console errors
npm run test -- --env=jsdom
```

**Manual Testing:**

```
For UI changes:
  [ ] Load page in browser
  [ ] Check desktop (1920x1080)
  [ ] Check mobile (375x667)
  [ ] Check dark mode (if applicable)
  [ ] Test all user interactions
  [ ] Check error states
  [ ] Check loading states
  [ ] Check empty states

For API changes:
  [ ] Test happy path (valid input)
  [ ] Test error cases (invalid input, missing fields)
  [ ] Test edge cases (zero, negative, very large numbers)
  [ ] Test authorization (unpermitted user)
  [ ] Test multi-tenancy (user sees only own data)
  [ ] Test concurrency (parallel requests)
```

**Deliverable:** Test results showing all pass

**Risk Flag:** If any test fails, fix the issue before proceeding.

---

### STEP 11: Review the Final Diff

**Goal:** Ensure the change is correct and complete.

**Diff Review Checklist:**
- [ ] No unrelated changes (whitespace cleanup, formatting)
- [ ] No debug code (console.log, print statements)
- [ ] No TODOs or FIXMEs
- [ ] No hardcoded values (use config, environment variables)
- [ ] No commented-out code
- [ ] Git commit message is clear and references ticket
- [ ] Migrations are included if schema changed
- [ ] Tests are included and passing
- [ ] No secrets (API keys, passwords) in code
- [ ] File permissions are correct (not executable if text)

**Git Commit Message Format:**
```
TICKET-ID: Type: Short description (≤70 chars)

Longer description explaining what and why (if needed).

- Changed X to Y
- Added feature Z
- Fixed bug in ABC

Tests:
- ✓ Unit tests passing
- ✓ Integration tests passing
- ✓ Manual testing: [describe]

Risks:
- [None identified] OR [list specific risks]

Breaking Changes:
- [None] OR [API change: X deprecated in favor of Y]
```

**Deliverable:** Clean diff ready for merge

**Risk Flag:** If diff contains unrelated changes, revert and commit separately.

---

### STEP 12: Provide Completion Report

**Goal:** Document what was done for audit and knowledge transfer.

**See DEFINITION_OF_DONE.md for complete report template.**

**Minimum Report Must Include:**
1. Summary (1-2 sentences)
2. Root cause or requirement
3. Files changed (created, modified, deleted)
4. Database changes (schema, migrations)
5. API changes (new endpoints, changed schemas)
6. Business logic changes
7. Security impact
8. Tests executed and results
9. Known limitations
10. Risks remaining

**Deliverable:** Written completion report

**Risk Flag:** If any "Definition of Done" item is incomplete, do not claim success.

---

## Special Workflow: Bug Fixes

For bug fixes, follow the 12-step workflow with these modifications:

### Bug Fix Workflow (Steps 1-12 with modifications):

**Step 1: Understand the Bug**
- Reproduce the bug (write failing test first)
- Understand what's expected vs. actual behavior
- Check if this is a symptom or root cause

**Step 2: Find Root Cause**
- Add debug logging
- Trace execution path
- Check for off-by-one errors, null checks, async issues
- Review recent changes that might have broken this

**Step 3: Check for Related Issues**
- Are there similar bugs elsewhere?
- Does this bug affect other workflows?
- Is there a pattern?

**Step 6: Check Existing Tests**
- Why didn't tests catch this?
- Add regression test that catches the bug

**Step 9: Implement Minimal Fix**
- Fix only the root cause, not symptoms
- Don't refactor surrounding code
- Add comments explaining the fix if non-obvious

**Step 10: Regression Testing**
- Verify the bug is fixed
- Run all existing tests (don't break anything else)
- Add new test case to prevent regression

---

## Special Workflow: New Features

For new features, follow the 12-step workflow with these modifications:

**Step 3: Architecture Check**
- Will this reuse existing services?
- Do we need new repositories?
- Do we need new domain entities?
- Can we leverage existing events?

**Step 5: Impact Analysis**
- What new permissions are needed?
- What existing workflows are affected?
- What reports might use this data?

**Step 6: Test Coverage**
- Write unit tests for domain logic
- Write integration tests for API layer
- Write E2E tests for complete workflow
- Aim for 75%+ coverage

**Step 9: UI Implementation**
- Include loading state while fetching
- Include error state with retry button
- Include empty state if applicable
- Include success feedback (toast, notification)
- Accessible to keyboard and screen readers
- Mobile responsive design

**Step 12: Documentation**
- Document the feature in README
- Document API changes
- Update user guide if applicable
- Add troubleshooting guide if complex

---

## Risk Assessment Matrix

| Risk Level | Indicators | Approval Required | Review Depth | Testing |
|-----------|-----------|-------------------|--------------|---------|
| 🟢 Low | UI change, documentation, config | Tech Lead | Standard | Unit + Manual |
| 🟡 Medium | New API endpoint, new service, data flow | Architect | Detailed | Unit + Integration |
| 🔴 High | Multi-tenancy, auth, schema, payments | Senior Lead | Extensive | Unit + Integration + E2E |
| 🛑 Critical | Breaking API change, data migration, security | Team Lead + Architect | Full review | All tests + Security audit |

---

## Troubleshooting Common Issues

### "Tests are failing"
1. Check test output for specific error
2. Run test locally with `pytest -vv --tb=short`
3. Check if this is a real failure or environment issue
4. If test is wrong, fix test
5. If code is wrong, fix code

### "I broke something unrelated"
1. Run full test suite: `pytest tests/ -x`
2. Identify which test is failing
3. Check what you changed that affects that module
4. Revert that change or fix it

### "I don't know how to test this"
1. Ask for help, don't skip tests
2. Look at similar tests in the codebase
3. Check if there are existing test utilities/factories
4. Write a simple test first, improve later

### "My change took longer than expected"
1. Document why in the report
2. Check if scope crept (added things not in plan)
3. Revert extras and scope to original plan
4. Create new ticket for extra work

---

## Summary

**The 12-step workflow ensures:**
- ✅ Requirements are understood before building
- ✅ Existing code is reviewed before modifying
- ✅ Impacts are identified before proceeding
- ✅ Risks are assessed before implementation
- ✅ Minimum changes are made
- ✅ All tests pass before claiming success
- ✅ Changes are reviewed and auditable
- ✅ Completion is documented for compliance

**Remember:** Slow down to go fast. Time spent understanding and planning prevents costly mistakes during implementation.
