# Phase-1 AI Interaction & Prompt Log: Employee Leave Management (ELM)

**Student Name:** Sumit Kumar  
**Roll Number:** 24BCS245 (Batch B)  
**Course:** Fusion ERP Lab Assignment 6B  
**Target Module:** Employee Leave Management (`modules/elm`)  
**LLM Used:** Local Code LLM (Qwen2.5-Coder / CodeLlama)  
**Commit Reference:** `30c7079` (`phase-1-elm-original`)  

---

## 1. Context & Specification Setup

### Prompt 0 (System Initialization)
```text
You are an expert Python/Django software engineer working on Fusion ERP, a modular academic and administrative platform.
We need to generate the initial Phase-1 implementation of the Employee Leave Management (ELM) module (`modules/elm`).

Follow these architectural constraints:
1. Pure Python domain logic under `modules/elm/domain/`.
2. Module registration via `modules/elm/registry.py` and `modules/elm/apps.py`.
3. Register the module in `config/settings/base.py` under `DOMAIN_MODULES`.
4. Implement leave policy rules according to the ELM specifications:
   - Leave categories: Casual Leave (CL), Restricted Holiday (RH), Special Casual Leave (SCL), Earned Leave (EL), Commuted Leave (COL), Vacation Leave (VL).
   - Staff (non-faculty) receive 30 days EL per calendar year.
   - Faculty receive 60 days VL (tied to vacation periods) and no direct EL.
   - At year-end, unused faculty VL converts to EL at a 2:1 ratio (2 VL -> 1 EL).
   - Commuted Leave (COL) is 20 days per year on medical grounds.
   - Continuous leave calculation (EL, COL, VL count intervening weekends and closed holidays).
   - Non-continuous leave calculation (CL, SCL, RH exclude weekends and closed holidays).
   - Prevent date overlaps with existing approved leaves.
5. Provide unit tests under `modules/elm/tests/test_leave_policy.py`.
```

### AI Response Summary
> Acknowledged. I will structure the Phase-1 ELM module with:
> 1. `apps.py` and `registry.py` for module metadata, navigation items, and RBAC permissions.
> 2. `domain/holidays.py` for weekend and closed holiday checking.
> 3. `domain/leave_policy.py` for leave allowance, category limits, continuous vs non-continuous business day calculations, and VL-to-EL conversion.
> 4. `tests/test_leave_policy.py` verifying each rule.

---

## 2. Module Registration & Architecture Integration

### Prompt 1 (Module Structure & Registration)
```text
Generate the module configuration and registry for ELM:
1. `modules/elm/apps.py`: Define ElmConfig with `name = "modules.elm"` and `label = "elm"`.
2. `modules/elm/registry.py`: Define `MODULE`, `NAV_ITEMS`, `PERMISSIONS`, and `ROLE_GRANTS` for roles:
   - employee (apply, view own leaves, cancel)
   - unit_head (approve, review, view leaves)
   - sanction_authority (final sanction)
   - elm_admin (manage calendar, offline sanction)
3. Register `"modules.elm"` in `DOMAIN_MODULES` in `config/settings/base.py`.
```

### AI Response Output
```python
# modules/elm/apps.py
from django.apps import AppConfig

class ElmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.elm"
    label = "elm"
```

```python
# modules/elm/registry.py
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply Leave", "icon": "Plus", "to": "/elm/apply", "required_permission": "elm.leave.apply", "sort_order": 10},
    {"code": "elm.my_leaves", "label": "My Leaves", "icon": "List", "to": "/elm/my-leaves", "required_permission": "elm.leave.view_self", "sort_order": 20},
    {"code": "elm.approvals", "label": "Pending Approvals", "icon": "CheckSquare", "to": "/elm/pending", "required_permission": "elm.leave.approve", "sort_order": 30},
]

PERMISSIONS = [
    ("elm.leave.apply", "Submit leave request"),
    ("elm.leave.view_self", "View own leave history"),
    ("elm.leave.approve", "Approve leave request"),
    ("elm.leave.cancel", "Cancel leave"),
]

ROLE_GRANTS = {
    "employee": ["elm.leave.apply", "elm.leave.view_self", "elm.leave.cancel"],
    "unit_head": ["elm.leave.apply", "elm.leave.view_self", "elm.leave.approve"],
    "sanction_authority": ["elm.leave.apply", "elm.leave.view_self", "elm.leave.approve"],
}
```

---

## 3. Core Leave Policy Engine

### Prompt 2 (Leave Calculation & Validation Logic)
```text
Implement `modules/elm/domain/leave_policy.py` with pure-Python functions:
1. `business_days_between(start, end, include_weekends, holidays)`
2. `is_leave_allowed(employee_role, leave_type, start, end, existing_leaves, holidays)`
3. `convert_unused_vl_to_el(vl_unused)`
4. Entitlement constants:
   - EL_PER_YEAR_NON_FACULTY = 30
   - FACULTY_VL_PER_YEAR = 60
   - COL_PER_YEAR = 20
Include overlap detection against approved leaves and role-based eligibility (EL for staff only, VL for faculty only).
```

### AI Response Output
```python
# modules/elm/domain/leave_policy.py
import datetime
from typing import List, Tuple

def is_weekend(date: datetime.date) -> bool:
    return date.weekday() >= 5

def is_holiday(date: datetime.date, holidays: List[datetime.date]) -> bool:
    return date in holidays

def business_days_between(start: datetime.date, end: datetime.date, include_weekends: bool, holidays: List[datetime.date]) -> int:
    total = 0
    cur = start
    while cur <= end:
        if (include_weekends or not is_weekend(cur)) and not is_holiday(cur, holidays):
            total += 1
        cur += datetime.timedelta(days=1)
    return total

EL_PER_YEAR_NON_FACULTY = 30
FACULTY_VL_PER_YEAR = 60
COL_PER_YEAR = 20

def max_el_days(is_faculty: bool) -> int:
    return 0 if is_faculty else EL_PER_YEAR_NON_FACULTY

def max_vl_days(is_faculty: bool) -> int:
    return FACULTY_VL_PER_YEAR if is_faculty else 0

def max_col_days() -> int:
    return COL_PER_YEAR

def convert_unused_vl_to_el(vl_unused: float) -> float:
    return vl_unused / 2.0

def is_leave_allowed(
    employee_role: str,
    leave_type: str,
    start: datetime.date,
    end: datetime.date,
    existing_leaves: List[Tuple[datetime.date, datetime.date, str]],
    holidays: List[datetime.date],
) -> Tuple[bool, str]:
    if end < start:
        return False, "End date is before start date"

    for s, e, _ in existing_leaves:
        if not (end < s or start > e):
            return False, "Overlapping with an existing approved leave"

    include_weekends = leave_type in {"EL", "COL", "VL"}
    days_requested = business_days_between(start, end, include_weekends, holidays)

    if leave_type == "EL":
        if employee_role == "faculty":
            return False, "Faculty do not have EL entitlement"
    elif leave_type == "VL":
        if employee_role != "faculty":
            return False, "Only faculty have VL entitlement"
    elif leave_type == "COL":
        pass
    elif leave_type in {"CL", "RH", "SCL"}:
        pass
    else:
        return False, f"Unknown leave type {leave_type}"

    return True, f"Leave of type {leave_type} for {days_requested} day(s) is allowed"
```

---

## 4. Test Suite Generation

### Prompt 3 (Unit Tests)
```text
Write comprehensive unit tests in `modules/elm/tests/test_leave_policy.py` using `pytest`.
Test cases should cover:
1. Weekend and holiday exclusion for CL/RH/SCL.
2. Continuous counting including weekends for EL/COL/VL.
3. Faculty vs non-faculty EL and VL eligibility.
4. Overlap rejection when date ranges intersect.
5. End date preceding start date validation error.
6. VL to EL conversion at 2:1 ratio.
```

### AI Response Output
Generated `modules/elm/tests/test_leave_policy.py` containing complete test coverage for all leave categories, conversion ratios, and validation boundaries.

---

## 5. Verification & Git Preservation

### Execution Commands
```bash
# Verify unit tests pass
pytest modules/elm/tests/test_leave_policy.py

# Commit Phase-1 baseline
git add config/settings/base.py modules/elm/
git commit -m "Add Employee Leave Management (ELM) module skeleton: registry, apps, domain logic, tests, and register in DOMAIN_MODULES"
git tag phase-1-elm-original
git push origin assignment-6-elm --tags
```
Result: All tests passed, commit `30c7079` created and tagged `phase-1-elm-original`.
