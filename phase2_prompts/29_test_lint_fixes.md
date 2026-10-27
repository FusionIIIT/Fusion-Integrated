# Task: Clean up ruff linter errors in test files

## File 1: modules/leave/tests/test_selectors.py
Put imports at the very top of the file before `pytestmark = pytest.mark.django_db`:
```python
"""Tests for leave selectors."""
import pytest

from modules.leave.models import LeaveApplication, LeaveBalance, LeaveCategory
from modules.leave.selectors.applications import applications_for, balances_for

pytestmark = pytest.mark.django_db
```

## File 2: modules/leave/tests/test_models.py
Combine nested `with` statements in:
- `test_end_before_start_rejected`:
  `with transaction.atomic(), pytest.raises(IntegrityError):`
- `test_half_day_on_multi_day_rejected`:
  `with transaction.atomic(), pytest.raises(IntegrityError):`
- `test_unique_balance_per_user_year_category`:
  `with transaction.atomic(), pytest.raises(IntegrityError):`
- `test_balance_cannot_be_negative`:
  `with transaction.atomic(), pytest.raises(IntegrityError):`

## File 3: modules/leave/tests/test_services.py
1. Put all imports at the very top before `pytestmark`:
```python
"""Tests for leave application and transition services."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.leave.domain.state_machine import (
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_SUBSTITUTE,
    AWAITING_UNIT_HEAD,
    CANCELLATION_PENDING_UNIT_HEAD,
    CANCELLED,
    REJECTED,
    WITHDRAWN,
)
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)
from modules.leave.services import applications as leave_services

pytestmark = pytest.mark.django_db
```
2. In fixtures `application_instance` and `director_app`, return directly instead of assigning `app` first:
   `return LeaveApplication.objects.create(...)`
3. In `test_apply_overlap_raises`, remove unused variable assignment:
   `LeaveApplication.objects.create(...)` (instead of `existing_app = ...`)

Output complete files only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
