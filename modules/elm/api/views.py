from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (CalendarDaySerializer, DecisionSerializer, LeaveBalanceSerializer, LeavePolicySerializer, LeaveRequestCreateSerializer, LeaveRequestSerializer, ResumptionSerializer, TaskSerializer)
from modules.elm.models import ApprovalTask, LeaveBalance, LeaveCalendarDay, LeavePolicy, LeaveRequest, ResumptionRecord

MODULE = HasModuleGrant("employee_leave_management")


def actor_id(request):
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", None)


class MyLeaveRequestsView(APIView):
    permission_classes = [MODULE, HasPermission("elm.request.view_self")]
    def get(self, request):
        rows = LeaveRequest.objects.filter(user_id=actor_id(request))
        return Response(LeaveRequestSerializer(rows, many=True).data)
    def post(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # This endpoint persists the submitted request and opens the initial review task.
        with transaction.atomic():
            leave = LeaveRequest.objects.create(user_id=actor_id(request), **data)
            if leave.substitute_user_id:
                leave.substitute_consent = "pending"
                leave.status = "awaiting_substitute"
                leave.save(update_fields=["substitute_consent", "status", "updated_at"])
            else:
                leave.status = "pending_unit_head"
                leave.save(update_fields=["status", "updated_at"])
            if leave.current_approver_user_id:
                ApprovalTask.objects.create(request=leave, stage="unit_head", approver_user_id=leave.current_approver_user_id)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission("elm.request.view_self")]
    def get(self, request, pk):
        obj = LeaveRequest.objects.filter(pk=pk, user_id=actor_id(request)).first()
        if obj is None: return Response({"detail": "Not found."}, status=404)
        return Response(LeaveRequestSerializer(obj).data)


class MyTasksView(APIView):
    permission_classes = [MODULE, HasPermission("elm.task.review")]
    def get(self, request):
        rows = ApprovalTask.objects.filter(approver_user_id=actor_id(request), status="pending").select_related("request")
        return Response(TaskSerializer(rows, many=True).data)


class TaskDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("elm.task.review")]
    def post(self, request, pk):
        serializer = DecisionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            task = ApprovalTask.objects.select_for_update().filter(pk=pk, approver_user_id=actor_id(request), status="pending").select_related("request").first()
            if task is None: return Response({"detail": "Pending task not found."}, status=404)
            task.status = "approved" if serializer.validated_data["decision"] == "approve" else "rejected"
            task.decision_note = serializer.validated_data.get("note", "")
            task.acted_at = timezone.now(); task.save(update_fields=["status", "decision_note", "acted_at", "updated_at"])
            leave = task.request
            leave.status = "approved" if task.status == "approved" else "rejected"
            leave.decided_at = timezone.now(); leave.save(update_fields=["status", "decided_at", "updated_at"])
        return Response(TaskSerializer(task).data)


class MyBalanceView(APIView):
    permission_classes = [MODULE, HasPermission("elm.balance.view_self")]
    def get(self, request):
        rows = LeaveBalance.objects.filter(user_id=actor_id(request)).order_by("-leave_year", "category")
        return Response(LeaveBalanceSerializer(rows, many=True).data)


class PolicyListView(APIView):
    permission_classes = [MODULE, HasPermission("elm.policy.manage")]
    def get(self, request): return Response(LeavePolicySerializer(LeavePolicy.objects.all(), many=True).data)
    def post(self, request):
        s = LeavePolicySerializer(data=request.data); s.is_valid(raise_exception=True); obj = s.save()
        return Response(LeavePolicySerializer(obj).data, status=201)


class CalendarView(APIView):
    permission_classes = [MODULE, HasPermission("elm.calendar.view")]
    def get(self, request):
        rows = LeaveCalendarDay.objects.filter(is_published=True)
        return Response(CalendarDaySerializer(rows, many=True).data)


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("elm.resumption.submit")]
    def post(self, request):
        s = ResumptionSerializer(data=request.data); s.is_valid(raise_exception=True)
        leave = LeaveRequest.objects.filter(pk=s.validated_data["request"].pk, user_id=actor_id(request), status="approved").first()
        if leave is None: return Response({"detail": "Approved leave request not found."}, status=404)
        obj, _ = ResumptionRecord.objects.update_or_create(request=leave, defaults={"reported_on": s.validated_data["reported_on"], "remarks": s.validated_data.get("remarks", "")})
        return Response(ResumptionSerializer(obj).data, status=201)
