Review findings: the Phase-1 views list every user's applications, let anyone holding "leave.application.approve" decide any request, reference serializers that do not exist (LeaveBalanceSerializer, LeaveActionHistorySerializer), and build their own {"error": ...} responses instead of letting the platform exception handler render errors.

Replace the whole content of modules/leave/api/views.py with DRF APIView classes (from rest_framework.views import APIView). Every view sets permission_classes = [HasModuleGrant("leave"), HasPermission("<code>")] using fusion_auth.permissions (read-only). The caller is request.principal; use request.principal.user_id and request.principal.kind. Call only the selectors and service functions shown (read-only). Do not catch LeaveError or NotFound and do not build error responses: they subclass core.api.exceptions.BadRequestError / NotFoundError, and the platform exception handler turns them into 400 / 404 with the standard envelope. For invalid input use serializer.is_valid(raise_exception=True).

Views (permission code in brackets):
- ApplicationListCreateView: GET [leave.application.view_own] returns my_applications; POST [leave.application.apply] validates ApplySerializer and calls apply_leave(user_id, kind, data), returns 201. Because the two methods need different permissions, implement get_permissions() to return the right HasPermission per method.
- ApplicationDetailView: GET [leave.application.view_own] -> visible_application
- WithdrawView: POST [leave.application.apply] -> withdraw
- CancelView: POST [leave.application.apply] -> request_cancellation(user_id, pk, timezone.localdate())
- SubstituteResponseView: POST [leave.substitute.respond] -> respond_to_substitute
- ReplaceSubstituteView: POST [leave.application.apply] -> replace_substitute
- InboxView: GET [leave.application.review or leave.substitute.respond] -> inbox. HasPermission accepts several codes and passes when the principal has any of them: HasPermission("leave.application.review", "leave.substitute.respond"). Substitutes use the same inbox to see the requests waiting for their consent.
- DecideView: POST [leave.application.review] -> decide(user_id, pk, decision, remark). Before deciding, load the application with visible_application and require leave.application.verify when its stage is "establishment" and leave.application.sanction when its stage is "sanction" (raise core.api.exceptions.NotFoundError if request.principal.has_permission(code) is False).
- BalanceView: GET [leave.application.view_own] -> ensure_balances(user_id, kind, year from ?year= or the current year)
- ReportingLineView: GET and PUT [leave.admin.manage] -> get_reporting_line / set_reporting_line for the user_id in the URL

Successful writes return the updated application with LeaveApplicationSerializer. Write the whole file. Do not ask for more files.

Use exactly these imports at the top of views.py. They are the only names you need, and every one of them exists; do not import anything else (task 003 failed because it imported functions that do not exist). Call services as applications.apply_leave(...), lifecycle.decide(...), admin.set_reporting_line(...) and selectors as selectors.inbox(...):

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
