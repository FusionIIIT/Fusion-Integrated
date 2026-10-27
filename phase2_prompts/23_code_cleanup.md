# Task: Format modules/leave/api/urls.py and modules/leave/domain/rules.py for ruff

## File 1: modules/leave/api/urls.py
Format url patterns so no line exceeds 100 characters.
```python
"""Leave API URLs."""
from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    path("categories", v.CategoryListView.as_view(), name="leave-category-list"),
    path("balances", v.BalanceListView.as_view(), name="leave-balance-list"),
    path("applications", v.ApplicationListView.as_view(), name="leave-application-list"),
    path("applications/apply", v.ApplicationCreateView.as_view(), name="leave-apply"),
    path(
        "applications/<int:pk>",
        v.ApplicationDetailView.as_view(),
        name="leave-application-detail",
    ),
    path(
        "applications/<int:pk>/transition",
        v.ApplicationTransitionView.as_view(),
        name="leave-application-transition",
    ),
    path(
        "applications/<int:pk>/history",
        v.ApplicationHistoryView.as_view(),
        name="leave-application-history",
    ),
]
```

## File 2: modules/leave/domain/rules.py
1. Clean imports:
   from collections.abc import Iterable
   from datetime import date, timedelta
   from decimal import Decimal
2. Replace `Optional[str]` with `str | None`, and `Tuple` with `tuple`.
3. Remove unnecessary `pass` inside docstring-documented class:
```python
class RuleViolation(ValueError):
    """Raised when a leave rule is violated."""
```
4. In `check_overlap`, combine nested `if`:
```python
            if (
                is_same_single_day
                and new_half is not None
                and existing_half is not None
                and new_half != existing_half
            ):
                continue
```
5. Ensure all lines <= 100 characters.

Output complete files only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
