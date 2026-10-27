TITLE: Rewrite URLs and registry again after review of 008 found missing routes and Phase-1 permissions
FORMAT: whole
EDIT: modules/leave/api/urls.py modules/leave/registry.py
READ: kit:phase2/DESIGN.md modules/leave/api/views.py
LIMIT: 1200
POST: makemigrations permissions
---
Review of task 008: urls.py has no route for ReportingLineView, routes balances at balances/<int:year>/ instead of balances/?year=, and imports include and DefaultRouter for nothing; registry.py still declares the Phase-1 permission codes (leave.application.create, leave.application.approve, leave.balance.view ...) that no view checks, so every nav link and grant points at a permission nobody enforces. Replace both files completely.

modules/leave/api/urls.py, exactly this shape:

from django.urls import path

from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    path("applications/", views.ApplicationListCreateView.as_view(), name="applications"),
    path("applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application-detail"),
    ... one path each for withdraw/, cancel/, substitute-response/, replace-substitute/ and decide/ under applications/<int:pk>/ ...
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("balances/", views.BalanceView.as_view(), name="balances"),
    path("reporting-lines/<int:user_id>/", views.ReportingLineView.as_view(), name="reporting-line"),
]

modules/leave/registry.py keeps the module docstring and this MODULE dict:
MODULE = {"code": "leave", "label": "Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Leave", "sort_order": 20, "status": "active"}

NAV_ITEMS, a list of four dicts with keys code, label, icon, to, required_permission, sort_order:
- leave.apply, "Apply for Leave", icon "PlusCircle", to "/leave/apply", required_permission "leave.application.apply", sort_order 5
- leave.mine, "My Leaves", icon "ListChecks", to "/leave/mine", required_permission "leave.application.view_own", sort_order 10
- leave.substitute, "Substitute Requests", icon "Users", to "/leave/substitute", required_permission "leave.substitute.respond", sort_order 15
- leave.approvals, "Leave Approvals", icon "CheckCircle", to "/leave/approvals", required_permission "leave.application.review", sort_order 20

PERMISSIONS, a list of (code, label) tuples with exactly these seven codes and no others:
leave.application.apply "Apply for leave and withdraw or cancel one's own requests"
leave.application.view_own "See one's own requests and balances"
leave.substitute.respond "Accept or decline being nominated as a substitute"
leave.application.review "Decide requests assigned to oneself at the Unit Head stage"
leave.application.verify "Verify requests at the Establishment stage"
leave.application.sanction "Sanction or refuse requests at the Sanctioning Authority stage"
leave.admin.manage "Maintain reporting lines"

SYSTEM_PERMISSIONS = []

ROLE_GRANTS, exactly:
"Employee": apply, view_own, substitute.respond
"Unit Head": review
"Deputy Registrar (Estt.)": review, verify
"Dean": review, sanction
"Registrar": review, sanction
"Director": review, sanction
"Leave Administrator": admin.manage
(write the full codes, for example "leave.application.apply").

Write both files in full. Do not ask for more files.
