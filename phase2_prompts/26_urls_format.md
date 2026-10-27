# Task: Format modules/leave/api/urls.py for ruff (output the COMPLETE file)

Keep the exact same names:
```python
"""Leave API routing."""
from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    path("categories", v.CategoryListView.as_view(), name="leave-categories"),
    path("balances", v.BalanceListView.as_view(), name="leave-balances"),
    path("applications", v.ApplicationListView.as_view(), name="leave-applications"),
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

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
