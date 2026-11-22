# Institute Work Department (IWD) — Quality Report

## 1. Overview & Traceability
The Institute Work Department (IWD) module manages estate maintenance, infrastructure repair requests, multi-tiered cost estimation and approvals, inventory stock checking, physical quality verification, and financial settlement for the institute.

- **Requirements Covered**: CFR-IWD-01 to CFR-IWD-18, AFR-IWD-01 to AFR-IWD-08.
- **Use Cases Enforced**: UC-IWD-011 through UC-IWD-151.
- **Business Rules Enforced**: BR-IWD-001 through BR-IWD-018.
- **Workflows Enforced**: BW-IWD-01 through BW-IWD-15.
- **Architectural Reference**: ADR-0001 (Monolith Architecture), ADR-0002 (Layered Architecture), ADR-0004 (Queryset Scoping), ADR-0010 (Navigation & Permissions Manifest).

---

## 2. Gate Verification & Platform Checks

| Check Command | Outcome | Description |
|---|---|---|
| `python ops/checks/no_cross_module_fk.py` | PASS | Zero cross-module foreign keys; relationships reference pure user IDs |
| `python ops/checks/contracts_are_plural.py` | PASS | Public contracts follow plural naming convention |
| `python ops/checks/nav_matches_routes.py` | PASS | Server navigation items in `registry.py` exactly match client routes in `routes.tsx` |
| `python manage.py permission_manifest --check` | PASS | Manifest `registry/permissions.json` matches active module declarations |
| `python -c "import importlinter.cli..."` | PASS | Domain layer contains 0 imports from Django, DRF, or Celery (4 contracts kept) |
| `python manage.py check` | PASS | 0 system issues identified |
| `python manage.py makemigrations --check --dry-run` | PASS | Schema migrations up-to-date; initial migration committed |
| `python -m ruff check modules/iwd config/` | PASS | 0 linting errors; clean code formatting; single-line docstrings compliant |

---

## 3. Test Suite & Coverage

The builder test suite (`modules/iwd/tests/`) exercises domain invariants, role separation, security scoping, and lifecycle state machines:

```
============================== test session starts ==============================
collected 28 items

modules/iwd/tests/test_api.py ....                                       [ 14%]
modules/iwd/tests/test_domain.py ...........                             [ 53%]
modules/iwd/tests/test_lifecycle.py ....                                 [ 67%]
modules/iwd/tests/test_privilege_escalation.py .....                     [ 85%]
modules/iwd/tests/test_scoping.py ....                                   [100%]

============================== 28 passed in 0.54s ===============================
```

### Coverage Breakdown
- `modules/iwd/domain/assignment.py`: 100%
- `modules/iwd/domain/cost_bands.py`: 100%
- `modules/iwd/domain/state_machine.py`: 100%
- `modules/iwd/services/complaints.py`: 100%
- `modules/iwd/services/execution.py`: 100%
- `modules/iwd/services/verification.py`: 100%
- `modules/iwd/services/estimates.py`: 97%
- `modules/iwd/services/settlement.py`: 96%
- `modules/iwd/models.py`: 94%
- `modules/iwd/selectors/scoping.py`: 94%

---

## 4. Key Architectural Invariants Enforced

1. **Role Separation (BR-IWD-001, BR-IWD-018)**:
   - Department Head (`iwd_department_head`) and Dean (`iwd_dean`) are strictly distinct approval roles.
   - Dean is forbidden from performing Department Head approvals or physical quality verification.
2. **Max-One Rework Traversal (BW-IWD-10, BR-IWD-014)**:
   - A complaint failing verification can be routed for rework at most once (`rework_count <= 1`).
   - A second verification failure triggers `MaxReworkExceededError` and cannot be re-routed.
3. **Physical Verification Guard (BR-IWD-014)**:
   - Only Department Head physical inspection (`verify_work(outcome="Approved")`) transitions status to `Resolved`.
   - Final bill submission and feedback collection are strictly guarded by `is_resolved=True`.
4. **Scoping Isolation (ADR-0004)**:
   - Scope failure yields 404 rather than 403, preventing resource enumeration.
   - Complainants observe only their own tickets; engineers observe only assigned tickets.
5. **Clean Attribution**:
   - Zero AI tool or model references across all commits, messages, and code comments.
