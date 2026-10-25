import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    LeaveApprovalSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    ResumptionSerializer,
    ReviewSerializer,
    SubstituteNominateSerializer,
    SubstituteResponseSerializer,
)
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveResumption, LeaveType


def _uid(request):
    return request.principal.user_id


def _error(message, http_status):
    return Response({"error": message}, status=http_status)


def _current_year():
    return datetime.date.today().year


def _is_higher_sanction(leave_type):
    return leave_type.code in {"SCL", "EL", "COL", "VL"}


def _is_director(request):
    roles = getattr(request.principal, "roles", ()) or ()
    active = getattr(request.principal, "active_role", None)
    return active == "director" or "director" in roles


class LeaveTypeListView(APIView):
    permission_classes = [HasModuleGrant("leave")]
    serializer_class = LeaveTypeSerializer

    def get(self, request):
        types = LeaveType.objects.filter(is_active=True)
        return Response(LeaveTypeSerializer(types, many=True).data)


class MyLeaveBalancesView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.view")]
    serializer_class = LeaveBalanceSerializer

    def get(self, request):
        user_id = _uid(request)
        balances = LeaveBalance.objects.filter(user_id=user_id)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveBalanceAllocateView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.manage")]
    serializer_class = LeaveBalanceSerializer

    def post(self, request):
        try:
            user_id = int(request.data["user_id"])
            leave_type_id = int(request.data["leave_type"])
            year = int(request.data.get("year", _current_year()))
            allocated = request.data["allocated_days"]
        except (KeyError, TypeError, ValueError):
            return _error("required fields missing", status.HTTP_400_BAD_REQUEST)

        leave_type = LeaveType.objects.filter(pk=leave_type_id).first()
        if leave_type is None:
            return _error("leave type not found", status.HTTP_404_NOT_FOUND)

        balance, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            leave_type=leave_type,
            year=year,
            defaults={"allocated_days": allocated, "used_days": 0},
        )
        balance.allocated_days = allocated
        balance.save(update_fields=["allocated_days", "updated_at"])
        return Response(LeaveBalanceSerializer(balance).data, status=status.HTTP_200_OK)


class MyLeaveRequestsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]
    serializer_class = LeaveRequestSerializer

    def get(self, request):
        user_id = _uid(request)
        requests = LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("leave.application.create"):
            return _error("permission denied", status.HTTP_403_FORBIDDEN)

        serializer = LeaveRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user_id = _uid(request)
        leave_type = serializer.validated_data["leave_type"]
        start = serializer.validated_data["start_date"]
        end = serializer.validated_data["end_date"]
        half_day = serializer.validated_data.get("half_day", "none")
        duration = (end - start).days + 1
        if half_day != "none":
            duration = duration - 0.5

        substitute_user_id = serializer.validated_data.get("substitute_user_id")
        if substitute_user_id is not None and substitute_user_id == user_id:
            return _error("substitute must be another employee", status.HTTP_400_BAD_REQUEST)

        balance = LeaveBalance.objects.filter(
            user_id=user_id, leave_type=leave_type, year=_current_year()
        ).first()
        if balance is not None and float(balance.remaining_days) < duration:
            return _error("Insufficient leave balance.", status.HTTP_400_BAD_REQUEST)

        leave_req = serializer.save(
            user_id=user_id,
            status="pending",
            duration_days=duration,
            substitute_user_id=substitute_user_id,
            substitute_status="pending" if substitute_user_id else "none",
        )
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


class CancelLeaveRequestView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.cancel")]
    serializer_class = LeaveRequestSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        leave = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if leave.status == "pending":
            leave.status = "cancelled"
            leave.save(update_fields=["status", "updated_at"])
            return Response(LeaveRequestSerializer(leave).data)
        if leave.status == "approved" and leave.start_date > datetime.date.today():
            # Simplified pre-start cancellation with balance restoration.
            # Full hierarchy-based cancellation is a documented limitation.
            with transaction.atomic():
                leave.status = "cancelled"
                leave.save(update_fields=["status", "updated_at"])
                balance = LeaveBalance.objects.filter(
                    user_id=leave.user_id,
                    leave_type=leave.leave_type,
                    year=leave.start_date.year,
                ).first()
                if balance is not None:
                    balance.used_days = max(
                        0.0, float(balance.used_days) - float(leave.duration_days)
                    )
                    balance.save(update_fields=["used_days", "updated_at"])
            return Response(LeaveRequestSerializer(leave).data)
        return _error(
            "Only pending or pre-start approved leaves can be cancelled.",
            status.HTTP_400_BAD_REQUEST,
        )


class WithdrawLeaveRequestView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.cancel")]
    serializer_class = LeaveRequestSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        leave = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if leave.status != "pending":
            return _error("Only pending requests can be withdrawn.", status.HTTP_400_BAD_REQUEST)
        leave.status = "withdrawn"
        leave.save(update_fields=["status", "updated_at"])
        return Response(LeaveRequestSerializer(leave).data)


class PendingApprovalsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]
    serializer_class = LeaveRequestSerializer

    def get(self, request):
        pending = LeaveRequest.objects.filter(status="pending").order_by("created_at")
        return Response(LeaveRequestSerializer(pending, many=True).data)


class SubstituteNominateView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.create")]
    serializer_class = SubstituteNominateSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        leave = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if leave.status != "pending":
            return _error("request not pending", status.HTTP_400_BAD_REQUEST)

        ser = SubstituteNominateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sub_id = ser.validated_data["substitute_user_id"]
        if sub_id == user_id:
            return _error("substitute must be another employee", status.HTTP_400_BAD_REQUEST)

        # Overlap check for the substitute.
        overlap = LeaveRequest.objects.filter(
            user_id=sub_id,
            status__in=["pending", "approved"],
            start_date__lte=leave.end_date,
            end_date__gte=leave.start_date,
        )
        if overlap.exists():
            return _error("substitute has overlapping leave", status.HTTP_400_BAD_REQUEST)

        leave.substitute_user_id = sub_id
        leave.substitute_status = "pending"
        leave.save(update_fields=["substitute_user_id", "substitute_status", "updated_at"])
        return Response(LeaveRequestSerializer(leave).data)


class SubstituteResponseView(APIView):
    permission_classes = [HasModuleGrant("leave")]
    serializer_class = SubstituteResponseSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        leave = LeaveRequest.objects.filter(pk=pk).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if leave.substitute_user_id != user_id:
            return _error("not the nominated substitute", status.HTTP_403_FORBIDDEN)
        if leave.substitute_status != "pending":
            return _error("substitute response already recorded", status.HTTP_400_BAD_REQUEST)

        ser = SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]
        if action == "accept":
            leave.substitute_status = "accepted"
        else:
            leave.substitute_status = "declined"
        leave.save(update_fields=["substitute_status", "updated_at"])
        return Response(LeaveRequestSerializer(leave).data)


class ReviewView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]
    serializer_class = ReviewSerializer

    def post(self, request, pk):
        leave = LeaveRequest.objects.filter(pk=pk).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if not _is_higher_sanction(leave.leave_type):
            return _error(
                "review applies to higher-sanction leave only", status.HTTP_400_BAD_REQUEST
            )

        ser = ReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]

        with transaction.atomic():
            leave = LeaveRequest.objects.select_for_update().filter(pk=pk).first()
            if not leave:
                return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
            if leave.status != "pending":
                return _error("request already decided", status.HTTP_409_CONFLICT)
            if leave.current_stage != "unit_head":
                return _error("not at unit-head stage", status.HTTP_400_BAD_REQUEST)
            if leave.substitute_user_id and leave.substitute_status != "accepted":
                return _error("substitute consent required", status.HTTP_400_BAD_REQUEST)

            leave.unit_head_recommendation = (
                "recommended" if action == "recommend" else "not_recommended"
            )
            leave.current_stage = "higher_sanction"
            leave.save(
                update_fields=[
                    "unit_head_recommendation",
                    "current_stage",
                    "updated_at",
                ]
            )
        return Response(LeaveRequestSerializer(leave).data)


class LeaveApprovalView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]
    serializer_class = LeaveApprovalSerializer

    def post(self, request, pk):
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approver_id = _uid(request)
        action = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")

        with transaction.atomic():
            leave = LeaveRequest.objects.select_for_update().filter(pk=pk).first()
            if not leave:
                return _error("Pending leave request not found.", status.HTTP_404_NOT_FOUND)
            if leave.status != "pending":
                return _error("request already decided", status.HTTP_409_CONFLICT)

            # Substitute consent gate.
            if leave.substitute_user_id and leave.substitute_status != "accepted":
                return _error("substitute consent required", status.HTTP_400_BAD_REQUEST)

            higher = _is_higher_sanction(leave.leave_type)

            # Stage gating.
            if higher:
                if leave.current_stage != "higher_sanction" and not _is_director(request):
                    return _error("not at final sanction stage", status.HTTP_400_BAD_REQUEST)
            else:
                # CL/RH: unit head is final authority.
                if leave.current_stage != "unit_head" and not _is_director(request):
                    return _error("not at final sanction stage", status.HTTP_400_BAD_REQUEST)

            # Self-approval only for Director self-sanction.
            if leave.user_id == approver_id and not _is_director(request):
                return _error("cannot approve your own request", status.HTTP_403_FORBIDDEN)

            if action == "approve":
                balance = (
                    LeaveBalance.objects.select_for_update()
                    .filter(
                        user_id=leave.user_id,
                        leave_type=leave.leave_type,
                        year=leave.start_date.year,
                    )
                    .first()
                )
                days = float(leave.duration_days)
                if balance is not None and float(balance.remaining_days) < days:
                    return _error("Insufficient leave balance.", status.HTTP_400_BAD_REQUEST)

                leave.status = "approved"
                leave.approver_user_id = approver_id
                leave.approved_at = timezone.now()
                leave.save(
                    update_fields=["status", "approver_user_id", "approved_at", "updated_at"]
                )

                if balance is not None:
                    balance.used_days = float(balance.used_days) + days
                    balance.save(update_fields=["used_days", "updated_at"])
            else:
                if action == "reject" and not remarks:
                    # rejection reason required for higher-sanction? keep optional but recorded
                    pass
                leave.status = "rejected"
                leave.approver_user_id = approver_id
                leave.rejection_reason = remarks
                leave.save(
                    update_fields=["status", "approver_user_id", "rejection_reason", "updated_at"]
                )

        return Response(LeaveRequestSerializer(leave).data)


class ExtensionCreateView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.create")]
    serializer_class = LeaveRequestSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        parent = LeaveRequest.objects.filter(pk=pk).first()
        if not parent:
            return _error("parent request not found", status.HTTP_404_NOT_FOUND)
        if parent.status != "approved":
            return _error("parent request must be approved", status.HTTP_400_BAD_REQUEST)
        today = datetime.date.today()
        if not (parent.start_date <= today <= parent.end_date):
            return _error("parent request is not currently ongoing", status.HTTP_400_BAD_REQUEST)
        if parent.user_id != user_id:
            return _error("not your request", status.HTTP_403_FORBIDDEN)

        try:
            start = datetime.date.fromisoformat(str(request.data["start_date"]))
            end = datetime.date.fromisoformat(str(request.data["end_date"]))
        except (KeyError, TypeError, ValueError):
            return _error("start_date and end_date are required", status.HTTP_400_BAD_REQUEST)
        if start > end:
            return _error("end_date must not be before start_date", status.HTTP_400_BAD_REQUEST)
        half_day = request.data.get("half_day", "none")
        duration = (end - start).days + 1
        if half_day != "none":
            duration = duration - 0.5

        substitute_user_id = request.data.get("substitute_user_id")
        if substitute_user_id is not None:
            try:
                substitute_user_id = int(substitute_user_id)
            except (TypeError, ValueError):
                return _error("invalid substitute_user_id", status.HTTP_400_BAD_REQUEST)
        if substitute_user_id is not None and substitute_user_id == user_id:
            return _error("substitute must be another employee", status.HTTP_400_BAD_REQUEST)
        if substitute_user_id is not None:
            overlap = LeaveRequest.objects.filter(
                user_id=substitute_user_id,
                status__in=["pending", "approved"],
                start_date__lte=end,
                end_date__gte=start,
            )
            if overlap.exists():
                return _error("substitute has overlapping leave", status.HTTP_400_BAD_REQUEST)

        leave_type = parent.leave_type
        balance = LeaveBalance.objects.filter(
            user_id=user_id, leave_type=leave_type, year=_current_year()
        ).first()
        if balance is not None and float(balance.remaining_days) < duration:
            return _error("Insufficient leave balance.", status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            ext = LeaveRequest.objects.create(
                user_id=user_id,
                leave_type=leave_type,
                start_date=start,
                end_date=end,
                duration_days=duration,
                reason=request.data.get("reason", ""),
                status="pending",
                is_extension=True,
                parent_request_id=parent.id,
                substitute_user_id=substitute_user_id,
                substitute_status="pending" if substitute_user_id else "none",
                half_day=half_day,
            )
        return Response(LeaveRequestSerializer(ext).data, status=status.HTTP_201_CREATED)


class ResumptionSubmitView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]
    serializer_class = ResumptionSerializer

    def post(self, request, pk):
        user_id = _uid(request)
        leave = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave:
            return _error("Leave request not found.", status.HTTP_404_NOT_FOUND)
        if leave.status != "approved":
            return _error("resumption applies to approved leave", status.HTTP_400_BAD_REQUEST)
        try:
            actual = datetime.date.fromisoformat(str(request.data.get("actual_resumption_date")))
        except (TypeError, ValueError):
            return _error("invalid actual_resumption_date", status.HTTP_400_BAD_REQUEST)
        res = LeaveResumption.objects.create(
            user_id=user_id,
            leave_request=leave,
            actual_resumption_date=actual,
            details=request.data.get("details", ""),
        )
        return Response(ResumptionSerializer(res).data, status=status.HTTP_201_CREATED)


class ResumptionReviewView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]
    serializer_class = ResumptionSerializer

    def post(self, request, pk):
        res = LeaveResumption.objects.filter(pk=pk).first()
        if not res:
            return _error("Resumption not found.", status.HTTP_404_NOT_FOUND)
        leave = res.leave_request
        approver_id = _uid(request)
        if res.status != "pending":
            return _error("already reviewed", status.HTTP_409_CONFLICT)

        approved_end = leave.end_date
        actual = res.actual_resumption_date
        if actual == approved_end:
            adjustment = 0.0
        elif actual < approved_end:
            adjustment = -float((approved_end - actual).days)
        else:
            adjustment = float((actual - approved_end).days)

        override = request.data.get("adjustment_days")
        if override is not None:
            try:
                adjustment = float(override)
            except (TypeError, ValueError):
                return _error("invalid adjustment_days", status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            res = LeaveResumption.objects.select_for_update().filter(pk=pk).first()
            leave = LeaveRequest.objects.select_for_update().filter(pk=res.leave_request_id).first()
            balance = (
                LeaveBalance.objects.select_for_update()
                .filter(
                    user_id=leave.user_id,
                    leave_type=leave.leave_type,
                    year=leave.start_date.year,
                )
                .first()
            )
            if balance is not None and adjustment != 0:
                balance.used_days = max(0.0, float(balance.used_days) + adjustment)
                balance.save(update_fields=["used_days", "updated_at"])
            if adjustment != 0:
                leave.end_date = actual
                leave.duration_days = (actual - leave.start_date).days + 1
                leave.save(update_fields=["end_date", "duration_days", "updated_at"])
            res.adjustment_days = adjustment
            res.reviewed_by_user_id = approver_id
            res.reviewed_at = timezone.now()
            res.status = "reviewed"
            res.save(
                update_fields=[
                    "adjustment_days",
                    "reviewed_by_user_id",
                    "reviewed_at",
                    "status",
                    "updated_at",
                ]
            )
        return Response(ResumptionSerializer(res).data)
