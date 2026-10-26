import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave_elm.api import serializers as s
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveStatus, LeaveType

MODULE = HasModuleGrant("leave_elm")

P_VIEW_SELF = "leave_elm.application.view_self"
P_APPLY = "leave_elm.application.apply"
P_WITHDRAW = "leave_elm.application.withdraw"
P_REVIEW = "leave_elm.application.review"
P_SUB_RESPOND = "leave_elm.substitute.respond"


def _actor(request):
    return getattr(request, "principal", None)


def calculate_leave_days(leave_type: str, start_date, end_date, is_half_day: bool) -> Decimal:
    """Calculate consumed leave days according to BR-EL-010 and BR-EL-011."""
    if is_half_day:
        return Decimal("0.5")

    # Continuous-day counting for EL, COL, VL (weekends count)
    if leave_type in [LeaveType.EL, LeaveType.COL, LeaveType.VL]:
        delta_days = (end_date - start_date).days + 1
        return Decimal(str(delta_days))

    # Working-day counting for CL, SCL, RH (excluding weekends)
    cur = start_date
    working_days = 0
    one_day = datetime.timedelta(days=1)
    while cur <= end_date:
        if cur.weekday() < 5:  # Mon-Fri
            working_days += 1
        cur += one_day
    return Decimal(str(working_days))


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get_queryset(self):
        actor = _actor(self.request)
        year = self.request.query_params.get("year", timezone.now().year)
        return LeaveBalance.objects.filter(user_id=actor.user_id, year=year)


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.LeaveApplicationCreateSerializer
        return s.LeaveApplicationSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        return LeaveApplication.objects.filter(user_id=actor.user_id).order_by("-created_at")

    def perform_create(self, serializer):
        actor = _actor(self.request)
        data = serializer.validated_data
        leave_type = data["leave_type"]
        start_date = data["start_date"]
        end_date = data["end_date"]
        is_half_day = data.get("is_half_day", False)
        sub_id = data.get("substitute_user_id")

        # BR-EL-012: Overlap check against active requests
        active_statuses = [
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.PENDING_APPROVAL,
            LeaveStatus.PENDING_HIGHER_APPROVAL,
            LeaveStatus.APPROVED,
        ]
        overlap_qs = LeaveApplication.objects.filter(
            user_id=actor.user_id,
            status__in=active_statuses,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if overlap_qs.exists():
            # Exception for CL half-day on same date
            is_valid_half_day_pair = (
                is_half_day
                and start_date == end_date
                and overlap_qs.filter(is_half_day=True, start_date=start_date).count() < 2
                and not overlap_qs.filter(is_half_day=False).exists()
            )
            if not is_valid_half_day_pair:
                raise serializers.ValidationError(
                    {"detail": "An overlapping pending or approved leave request already exists."}
                )

        # Balance sufficiency check
        req_days = calculate_leave_days(leave_type, start_date, end_date, is_half_day)
        year = start_date.year
        balance_obj = LeaveBalance.objects.filter(
            user_id=actor.user_id, year=year, leave_type=leave_type
        ).first()
        if balance_obj and balance_obj.balance < req_days:
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Insufficient {leave_type} balance. Available: {balance_obj.balance}, "
                        f"Requested: {req_days}"
                    )
                }
            )

        # BR-EL-015: Initial status
        initial_status = (
            LeaveStatus.PENDING_SUBSTITUTE if sub_id else LeaveStatus.PENDING_APPROVAL
        )
        serializer.save(user_id=actor.user_id, status=initial_status)


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE]
    lookup_field = "pk"
    queryset = LeaveApplication.objects.all()


class LeaveWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        actor = _actor(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=actor.user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.status not in [
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.PENDING_APPROVAL,
            LeaveStatus.PENDING_HIGHER_APPROVAL,
        ]:
            return Response(
                {"error": "Only pending leave requests can be withdrawn."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        app.status = LeaveStatus.WITHDRAWN
        app.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveCancelView(APIView):
    """BR-EL-023: Cancellation of approved leave before start date."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        actor = _actor(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=actor.user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.status != LeaveStatus.APPROVED:
            return Response(
                {"error": "Only approved leaves can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        today = timezone.now().date()
        if app.start_date <= today:
            return Response(
                {"error": "Cannot cancel leave that has already started."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.status = LeaveStatus.CANCELLED
        app.save(update_fields=["status", "updated_at"])

        # Restore deducted balance
        days = calculate_leave_days(
            app.leave_type, app.start_date, app.end_date, app.is_half_day
        )
        bal = LeaveBalance.objects.filter(
            user_id=app.user_id, year=app.start_date.year, leave_type=app.leave_type
        ).first()
        if bal:
            bal.balance += days
            bal.save(update_fields=["balance", "updated_at"])

        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUB_RESPOND)]

    def post(self, request, pk: int):
        actor = _actor(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, substitute_user_id=actor.user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        accepted = request.data.get("accepted", True)
        app.substitute_accepted = accepted
        # BR-EL-015: Decline leaves gate closed; accept releases routing gate
        app.status = LeaveStatus.PENDING_APPROVAL if accepted else LeaveStatus.PENDING_SUBSTITUTE
        app.save(update_fields=["substitute_accepted", "status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveReviewActionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, pk: int):
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        decision = request.data.get("decision", "APPROVED").upper()

        if decision == "REJECTED":
            app.status = LeaveStatus.REJECTED
        elif decision == "RECOMMENDED":
            # BR-EL-017: Higher-sanction leave recommendation moves to higher approval
            app.status = LeaveStatus.PENDING_HIGHER_APPROVAL
        elif decision == "APPROVED":
            app.status = LeaveStatus.APPROVED
            # Deduct balance on approval
            days = calculate_leave_days(
                app.leave_type, app.start_date, app.end_date, app.is_half_day
            )
            bal = LeaveBalance.objects.filter(
                user_id=app.user_id, year=app.start_date.year, leave_type=app.leave_type
            ).first()
            if bal:
                bal.balance = max(Decimal("0.00"), bal.balance - days)
                bal.save(update_fields=["balance", "updated_at"])
        else:
            return Response(
                {"error": f"Unknown decision '{decision}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)
