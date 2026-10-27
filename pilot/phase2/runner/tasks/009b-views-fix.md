TITLE: Rewrite the API views again after review of 007 found crashes and wrong service calls
FORMAT: whole
EDIT: modules/leave/api/views.py
READ: kit:phase2/DESIGN.md fusion_auth/permissions.py modules/leave/api/serializers.py modules/leave/selectors.py modules/leave/services/applications.py modules/leave/services/lifecycle.py modules/leave/services/admin.py
LIMIT: 1500
POST: none
---
Review of modules/leave/api/views.py from task 007. Keep the same ten view classes and their permission codes, but rewrite the whole file fixing all of these:

1. It imports date, action and AllowAny, which are unused (ruff F401). Use exactly the imports listed at the end.
2. ApplicationListCreateView.get_permissions() returns permission CLASSES and leaves out the module gate. DRF needs instances: return [HasModuleGrant("leave")(), HasPermission("leave.application.view_own")()] for GET and [HasModuleGrant("leave")(), HasPermission("leave.application.apply")()] for POST. Remove `permission_classes = []`.
3. ApplicationListCreateView.post reads data["kind"], which the serializer does not have (KeyError, HTTP 500). The applicant's kind is request.principal.kind: applications.apply_leave(request.principal.user_id, request.principal.kind, serializer.validated_data).
4. respond_to_substitute and replace_substitute are in modules.leave.services.applications, not lifecycle (AttributeError). Call applications.respond_to_substitute(...) and applications.replace_substitute(...).
5. Request bodies are not validated. SubstituteResponseView must use SubstituteResponseSerializer, ReplaceSubstituteView ReplaceSubstituteSerializer, and DecideView DecisionSerializer, each with is_valid(raise_exception=True), then read serializer.validated_data.
6. Every write view must return the object the service returns, not reload it: app = applications.withdraw(...); app = lifecycle.request_cancellation(...) (this returns the NEW cancellation request, which the client needs); app = applications.respond_to_substitute(...); app = applications.replace_substitute(...); app = lifecycle.decide(...). DecideView currently returns the object loaded before the decision, so the response shows the old status. Return Response(LeaveApplicationSerializer(app).data).
7. DecideView: permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]. Keep the extra checks: when the application's stage is "establishment" the principal must have "leave.application.verify", and when it is "sanction" it must have "leave.application.sanction"; otherwise raise NotFoundError().
8. BalanceView takes kind from a query parameter, so a staff member could ask for faculty balances. Use request.principal.kind. year = int(request.query_params.get("year", timezone.localdate().year)).
9. ReportingLineView: get_reporting_line is selectors.get_reporting_line, not admin (AttributeError). GET: raise NotFoundError() when it returns None. PUT: validate with ReportingLineSerializer(data=request.data), then line = admin.set_reporting_line(user_id, v["unit_head_id"], v.get("establishment_id"), v.get("sanctioning_authority_id")) and return ReportingLineSerializer(line).data.
10. The URL keyword for an application id is pk, so every application view method is `def get(self, request, pk)` / `def post(self, request, pk)` and passes pk to the service. ReportingLineView methods take user_id.
11. Do not catch exceptions and do not build error responses; the platform exception handler does that.

Use exactly these imports at the top of views.py and nothing else:

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import selectors
from modules.leave.api.serializers import (
    ApplySerializer, DecisionSerializer, LeaveApplicationSerializer, LeaveBalanceSerializer,
    ReplaceSubstituteSerializer, ReportingLineSerializer, SubstituteResponseSerializer,
)
from modules.leave.services import admin, applications, lifecycle

Write the whole file. Do not ask for more files.
