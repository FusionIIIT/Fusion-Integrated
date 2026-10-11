"""The approver's side: the task queue, its decisions, and resumption review.

An approver never picks a request out of the whole table. They are handed the
tasks their office was routed (BR-EL-019), and the decision endpoints take a
*task* id rather than a request id — which is what keeps "may I decide this?"
a question with one answer instead of one per view.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.selectors import leave as sel
from modules.leave.services import applications as app_service
from modules.leave.services import resumption as resumption_service

MODULE = HasModuleGrant("leave")
P_APPROVE = "leave.request.approve"
P_VIEW = "leave.request.view"


def _actor(request):
    return getattr(request, "principal", None)


@extend_schema(responses=s.WorkflowTaskSerializer(many=True))
class TaskListView(APIView):
    """EL-UC-003/004/005 — what is waiting on the caller's office."""

    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def get(self, request):
        status_filter = request.query_params.get("status", "pending")
        if status_filter not in ("pending", "completed", "cancelled", "all"):
            from core.api.exceptions import BadRequestError

            raise BadRequestError("Unknown task status filter.",
                                  code="invalid_filter")
        tasks = sel.tasks_for(_actor(request),
                              status=None if status_filter == "all"
                              else status_filter)
        return Response({"results": s.WorkflowTaskSerializer(
            tasks.order_by("assigned_at")[:200], many=True).data})


@extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
class TaskDecisionView(APIView):
    """One routed step: recommend, verify, approve or reject."""

    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk: int):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = app_service.decide(actor=_actor(request), task_id=pk, **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.LeaveResumptionSerializer(many=True))
class ResumptionQueueView(APIView):
    """EL-UC-011 — resumption submissions awaiting review."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request):
        rows = (sel.resumptions_for(_actor(request))
                .filter(outcome="pending").order_by("actual_date")[:200])
        return Response({"results": s.LeaveResumptionSerializer(rows, many=True).data})


@extend_schema(request=s.ResumptionReviewSerializer,
               responses=s.LeaveResumptionSerializer)
class ResumptionReviewView(APIView):
    """EL-UC-011 — review the actual return and synchronise what it requires."""

    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk: int):
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = resumption_service.review(actor=_actor(request), resumption_id=pk,
                                        note=payload.validated_data.get("note", ""))
        return Response(s.LeaveResumptionSerializer(row).data)


@extend_schema(responses=s.LeaveResumptionSerializer)
class ResumptionDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk: int):
        row = sel.resumption_for(_actor(request), pk)
        if row is None:
            raise NotFoundError("No such resumption submission.")
        return Response(s.LeaveResumptionSerializer(row).data)
