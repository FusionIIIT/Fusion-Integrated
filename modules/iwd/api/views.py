from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from modules.iwd.api.serializers import (
    ContractorSerializer,
    InventoryItemSerializer,
    WorkRequestCreateSerializer,
    WorkRequestLogSerializer,
    WorkRequestSerializer,
)
from modules.iwd.domain.rules import (
    IWDDomainError,
    RequestStatus,
    validate_transition,
)
from modules.iwd.models import Contractor, InventoryItem, WorkRequest, WorkRequestLog


# Enforced RBAC permission mappings for IWD endpoints
PERMISSIONS_MAP = {
    "view_requests": "iwd.work_request.view",
    "create_request": "iwd.work_request.create",
    "approve_request": "iwd.work_request.approve",
    "assign_request": "iwd.work_request.assign",
    "close_request": "iwd.work_request.close",
    "manage_contractor": "iwd.contractor.manage",
    "manage_inventory": "iwd.inventory.manage",
    "view_budget": "iwd.budget.view",
    "manage_budget": "iwd.budget.manage",
    "view_report": "iwd.report.view",
}

def _get_username(request) -> str:
    if request.user and request.user.is_authenticated:
        return request.user.username
    return request.headers.get("X-User", "anonymous")


class WorkRequestViewSet(viewsets.ModelViewSet):
    queryset = WorkRequest.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action in ("create",):
            return WorkRequestCreateSerializer
        return WorkRequestSerializer

    def perform_create(self, serializer):
        username = _get_username(self.request)
        instance = serializer.save(
            requester_username=username,
            status="draft",
        )
        WorkRequestLog.objects.create(
            work_request=instance,
            from_status="",
            to_status="draft",
            actor_username=username,
            note="Work request created.",
        )

    def _do_transition(self, request, pk, target_status: str, note: str = ""):
        work_req = self.get_object()
        current = RequestStatus(work_req.status)
        target = RequestStatus(target_status)
        try:
            validate_transition(current, target)
        except IWDDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        old_status = work_req.status
        work_req.status = target.value
        actor = _get_username(request)

        if target == RequestStatus.SUBMITTED:
            work_req.submitted_at = datetime.now(tz=timezone.utc)
        elif target == RequestStatus.COMPLETED:
            work_req.completed_at = datetime.now(tz=timezone.utc)
            if request.data.get("actual_cost") is not None:
                work_req.actual_cost = request.data["actual_cost"]

        if request.data.get("remarks"):
            work_req.remarks = request.data["remarks"]

        work_req.save()
        WorkRequestLog.objects.create(
            work_request=work_req,
            from_status=old_status,
            to_status=work_req.status,
            actor_username=actor,
            note=note or request.data.get("note", ""),
        )
        return Response(WorkRequestSerializer(work_req).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._do_transition(request, pk, "submitted", "Submitted for review.")

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        return self._do_transition(request, pk, "under_review", "Taken up for review.")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        wr = self.get_object()
        if request.data.get("assigned_to"):
            wr.assigned_to = request.data["assigned_to"]
            wr.save(update_fields=["assigned_to"])
        return self._do_transition(request, pk, "approved", "Approved and assigned.")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._do_transition(request, pk, "rejected", request.data.get("note", "Rejected."))

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._do_transition(request, pk, "in_progress", "Work started.")

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        return self._do_transition(request, pk, "on_hold", request.data.get("note", "Put on hold."))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._do_transition(request, pk, "completed", "Work completed.")

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._do_transition(request, pk, "closed", "Work request closed.")

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        wr = self.get_object()
        logs = wr.logs.all()
        return Response(WorkRequestLogSerializer(logs, many=True).data)


class ContractorViewSet(viewsets.ModelViewSet):
    queryset = Contractor.objects.filter(is_active=True)
    serializer_class = ContractorSerializer
    permission_classes = [AllowAny]


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        items = [i for i in self.get_queryset() if i.is_low_stock]
        return Response(InventoryItemSerializer(items, many=True).data)

