from django.urls import path

from modules.dept.api.views import DeptView

RESOURCES = (
    "announcements",
    "inventory",
    "stock-requests",
    "feedback",
    "profiles",
    "timetable",
    "resources",
    "details",
    "academic-info",
    "notifications",
)

urlpatterns = []
for resource in RESOURCES:
    defaults = {"resource": resource}
    urlpatterns.extend(
        (
            path(f"{resource}/", DeptView.as_view(), defaults, name=f"dept-{resource}"),
            path(
                f"{resource}/<int:pk>/",
                DeptView.as_view(),
                defaults,
                name=f"dept-{resource}-detail",
            ),
            path(
                f"{resource}/<int:pk>/<str:action>/",
                DeptView.as_view(),
                defaults,
                name=f"dept-{resource}-action",
            ),
        )
    )
