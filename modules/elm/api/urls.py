from django.urls import path

from modules.elm.api import views as v

A = v.ACTION_VIEWS

urlpatterns = [
    path("requests", v.RequestsView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/print", v.PrintView.as_view(), name="elm-print"),
    *[path(f"requests/<int:pk>/{name}", view.as_view(), name=f"elm-{name}")
      for name, view in A.items()],
    path("tasks", v.TasksView.as_view(), name="elm-tasks"),
    path("balances", v.BalancesView.as_view(), name="elm-balances"),
    path("admin/policy", v.PolicyView.as_view(), name="elm-policy"),
    path("admin/calendar", v.CalendarView.as_view(), name="elm-calendar"),
    path("admin/hierarchy", v.HierarchyView.as_view(), name="elm-hierarchy"),
    path("admin/offline", v.OfflineView.as_view(), name="elm-offline"),
]
