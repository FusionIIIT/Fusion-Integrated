TITLE: Document every leave endpoint in the OpenAPI schema (drf-spectacular)
FORMAT: diff
EDIT: modules/leave/api/views.py
READ: modules/leave/api/serializers.py
LIMIT: 900
POST: none
---
Fusion's CI regenerates the OpenAPI schema with `manage.py spectacular --fail-on-warn` and `manage.py check --deploy --fail-level WARNING`. Both fail on views.py because every APIView triggers drf_spectacular.W002 ("unable to guess serializer"), and the two GET methods on applications/ and applications/<pk>/ collide on the operationId "v1_leave_applications_retrieve" (W001). The placement module solves this with @extend_schema. Fix only this, with SEARCH/REPLACE edits:

1. Add the import line `from drf_spectacular.utils import OpenApiParameter, extend_schema` directly below `from django.utils import timezone`.
2. Put these decorators directly above the class lines (or, where it says method, directly above that method's def line, indented like the def):
   - ApplicationListCreateView.get (method): @extend_schema(operation_id="v1_leave_applications_list", responses=LeaveApplicationSerializer(many=True))
   - ApplicationListCreateView.post (method): @extend_schema(request=ApplySerializer, responses={201: LeaveApplicationSerializer})
   - class ApplicationDetailView: @extend_schema(responses=LeaveApplicationSerializer)
   - class WithdrawView: @extend_schema(request=None, responses=LeaveApplicationSerializer)
   - class CancelView: @extend_schema(request=None, responses=LeaveApplicationSerializer)
   - class SubstituteResponseView: @extend_schema(request=SubstituteResponseSerializer, responses=LeaveApplicationSerializer)
   - class ReplaceSubstituteView: @extend_schema(request=ReplaceSubstituteSerializer, responses=LeaveApplicationSerializer)
   - class InboxView: @extend_schema(responses=LeaveApplicationSerializer(many=True))
   - class DecideView: @extend_schema(request=DecisionSerializer, responses=LeaveApplicationSerializer)
   - class BalanceView: @extend_schema(parameters=[OpenApiParameter("year", int, required=False)], responses=LeaveBalanceSerializer(many=True))
   - class ReportingLineView: @extend_schema(request=ReportingLineSerializer, responses=ReportingLineSerializer)

Do not change anything else.
