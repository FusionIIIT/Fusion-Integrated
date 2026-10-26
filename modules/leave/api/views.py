"""
modules/leave/api/views.py
DRF API views for the Employee Leave Management module.
"""
import datetime

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    SubstituteRequest,
    ApprovalStep,
    LeavePolicy,
    HolidayCalendar,
    ApplicationStatus,
    ApprovalDecision,
    SubstituteStatus,
)
from modules.leave.api.serializers import (
    LeaveBalanceSerializer,
    LeaveApplicationListSerializer,
    LeaveApplicationDetailSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationWithdrawSerializer,
    LeaveApplicationCancelSerializer,
    LeaveApplicationExtendSerializer,
    SubstituteRespondSerializer,
    UnitHeadDecideSerializer,
    ResumptionSerializer,
    AdminOfflineRecordSerializer,
    LeavePolicySerializer,
    HolidayCalendarSerializer,
)
from modules.leave.domain.rules import requires_substitute, get_unit_head_scope


def _get_user_id(request):
    """Extract user_id from request.user (IamSessionAuthentication principal)."""
    return getattr(request.user, "user_id", None) or request.user.id


# ---------------------------------------------------------------------------
# Employee-facing views
# ---------------------------------------------------------------------------

class LeaveBalanceView(APIView):
    """GET /leave/balance/ - return current user's leave balances."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = _get_user_id(request)
        year    = request.query_params.get("year", str(datetime.date.today().year))
        qs      = LeaveBalance.objects.filter(user_id=user_id, year=year)
        return Response(LeaveBalanceSerializer(qs, many=True).data)


class LeaveApplicationListCreateView(APIView):
    """
    GET  /leave/applications/  - list my applications
    POST /leave/applications/  - submit a new application
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = _get_user_id(request)
        qs = LeaveApplication.objects.filter(user_id=user_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(LeaveApplicationListSerializer(qs, many=True).data)

    def post(self, request):
        user_id = _get_user_id(request)
        serializer = LeaveApplicationCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        category  = validated["category"]
        start_date = validated["start_date"]
        end_date = validated["end_date"]
        half_day = validated.get("half_day", False)
        half = validated.get("half")

        # BR-EL-012: Check applicant non-overlap with active pending or approved leave
        active_statuses = [
            ApplicationStatus.PENDING,
            ApplicationStatus.AWAITING_SUBSTITUTE,
            ApplicationStatus.UNIT_HEAD_REVIEW,
            ApplicationStatus.PROCESSING,
            ApplicationStatus.SANCTIONED,
            ApplicationStatus.EXTENSION_PENDING,
        ]
        overlap_qs = LeaveApplication.objects.filter(
            user_id=user_id,
            status__in=active_statuses,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        for existing in overlap_qs:
            # Different half-day CL on the same date is allowed
            if (
                half_day
                and existing.half_day
                and start_date == end_date == existing.start_date == existing.end_date
                and half
                and existing.half
                and half != existing.half
            ):
                continue
            return Response(
                {"detail": "Leave dates impermissibly overlap an existing pending or approved leave."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # BR-EL-020: Director self-sanction path
        user_roles = getattr(request.user, "roles", []) if hasattr(request, "user") else []
        is_director = "director" in user_roles

        now = datetime.datetime.now(datetime.timezone.utc)
        if is_director:
            initial_status = ApplicationStatus.SANCTIONED
            decided_at = now
            decided_by = user_id
        elif requires_substitute(category) and validated.get("substitute_user_id"):
            initial_status = ApplicationStatus.AWAITING_SUBSTITUTE
            decided_at = None
            decided_by = None
        else:
            initial_status = ApplicationStatus.PENDING
            decided_at = None
            decided_by = None

        application = LeaveApplication.objects.create(
            user_id=user_id,
            status=initial_status,
            submitted_at=now,
            decided_at=decided_at,
            decided_by_user_id=decided_by,
            **validated,
        )

        # Create substitute request if needed
        if initial_status == ApplicationStatus.AWAITING_SUBSTITUTE:
            SubstituteRequest.objects.create(
                application=application,
                nominee_user_id=validated["substitute_user_id"],
            )

        # Create first approval step (if not self-sanctioned)
        if not is_director:
            scope = get_unit_head_scope(category)
            ApprovalStep.objects.create(
                application=application,
                step_order=1,
                authority_role="unit_head",
            )

        return Response(
            LeaveApplicationDetailSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )
            LeaveApplicationDetailSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationDetailView(APIView):
    """GET /leave/applications/<pk>/"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user_id):
        try:
            return LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            return None

    def get(self, request, pk):
        user_id = _get_user_id(request)
        application = self.get_object(pk, user_id)
        if not application:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeaveApplicationDetailSerializer(application).data)


class LeaveApplicationWithdrawView(APIView):
    """POST /leave/applications/<pk>/withdraw/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            application = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        withdrawable = [
            ApplicationStatus.DRAFT,
            ApplicationStatus.PENDING,
            ApplicationStatus.AWAITING_SUBSTITUTE,
            ApplicationStatus.UNIT_HEAD_REVIEW,
        ]
        if application.status not in withdrawable:
            return Response(
                {"detail": f"Cannot withdraw an application in status '{application.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApplicationWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application.status           = ApplicationStatus.WITHDRAWN
        application.withdrawal_reason = serializer.validated_data.get("withdrawal_reason", "")
        application.save(update_fields=["status", "withdrawal_reason", "updated_at"])
        return Response({"detail": "Application withdrawn."})


class LeaveApplicationCancelView(APIView):
    """POST /leave/applications/<pk>/cancel/ - request cancellation of sanctioned leave."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            application = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if application.status != ApplicationStatus.SANCTIONED:
            return Response(
                {"detail": "Only sanctioned leave can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only allow cancellation before leave starts
        if application.start_date <= datetime.date.today():
            return Response(
                {"detail": "Cannot cancel leave that has already started."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApplicationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application.status          = ApplicationStatus.CANCELLATION_PENDING
        application.withdrawal_reason = serializer.validated_data["cancellation_reason"]
        application.save(update_fields=["status", "withdrawal_reason", "updated_at"])
        return Response({"detail": "Cancellation request submitted."})


class LeaveApplicationExtendView(APIView):
    """POST /leave/applications/<pk>/extend/ - request extension."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            application = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if application.status != ApplicationStatus.SANCTIONED:
            return Response(
                {"detail": "Only sanctioned leave can be extended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extendable_categories = ["EL", "COL", "VL"]
        if application.category not in extendable_categories:
            return Response(
                {"detail": f"Extension is only allowed for {extendable_categories}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApplicationExtendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_end = serializer.validated_data["new_end_date"]
        if new_end <= application.end_date:
            return Response(
                {"detail": "New end date must be after the current end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create extension application
        extension = LeaveApplication.objects.create(
            user_id=user_id,
            category=application.category,
            start_date=application.end_date + datetime.timedelta(days=1),
            end_date=new_end,
            reason=serializer.validated_data["reason"],
            status=ApplicationStatus.EXTENSION_PENDING,
            is_extension=True,
            parent_application=application,
            submitted_at=datetime.datetime.now(datetime.timezone.utc),
        )
        return Response(
            LeaveApplicationDetailSerializer(extension).data,
            status=status.HTTP_201_CREATED,
        )


class SubstituteRespondView(APIView):
    """POST /leave/substitute/<pk>/respond/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            sub_req = SubstituteRequest.objects.select_related("application").get(
                pk=pk, nominee_user_id=user_id
            )
        except SubstituteRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if sub_req.status != SubstituteStatus.PENDING:
            return Response(
                {"detail": "This substitute request has already been responded to."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubstituteRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision      = serializer.validated_data["status"]
        now           = datetime.datetime.now(datetime.timezone.utc)
        sub_req.status       = decision
        sub_req.responded_at = now
        sub_req.save(update_fields=["status", "responded_at", "updated_at"])

        application = sub_req.application
        if decision == SubstituteStatus.ACCEPTED:
            application.status = ApplicationStatus.UNIT_HEAD_REVIEW
        else:
            # declined - move back to pending so employee can reassign
            application.status = ApplicationStatus.PENDING
        application.save(update_fields=["status", "updated_at"])

        return Response({"detail": f"Substitute request {decision}."})


# ---------------------------------------------------------------------------
# Unit-head views
# ---------------------------------------------------------------------------

class UnitHeadQueueView(APIView):
    """GET /leave/unit-head/queue/ - pending applications for unit head."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LeaveApplication.objects.filter(
            status__in=[
                ApplicationStatus.UNIT_HEAD_REVIEW,
                ApplicationStatus.PENDING,
            ]
        )
        return Response(LeaveApplicationListSerializer(qs, many=True).data)


class UnitHeadDecideView(APIView):
    """POST /leave/unit-head/<pk>/decide/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            application = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UnitHeadDecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        comment  = serializer.validated_data.get("comment", "")
        now      = datetime.datetime.now(datetime.timezone.utc)

        from modules.leave.domain.rules import get_unit_head_scope
        scope = get_unit_head_scope(application.category)

        application.unit_head_status     = decision
        application.unit_head_decided_at = now

        if scope == "final":
            # Unit head is the final authority
            if decision in [ApprovalDecision.APPROVED]:
                application.status         = ApplicationStatus.SANCTIONED
                application.decided_at     = now
                application.decided_by_user_id = user_id
            elif decision == ApprovalDecision.REJECTED:
                application.status         = ApplicationStatus.REJECTED
                application.decided_at     = now
                application.decided_by_user_id = user_id
        else:
            # BR-EL-017: Unit Head records Recommended or Not Recommended.
            # Not Recommended is not a final rejection; both outcomes continue through higher-sanction path.
            if decision in [ApprovalDecision.RECOMMENDED, ApprovalDecision.NOT_RECOMMENDED, ApprovalDecision.APPROVED]:
                application.status = ApplicationStatus.PROCESSING
            elif decision == ApprovalDecision.REJECTED:
                application.status = ApplicationStatus.REJECTED
                application.decided_at         = now
                application.decided_by_user_id = user_id

        application.save()

        # Update approval step
        ApprovalStep.objects.filter(
            application=application, step_order=1, authority_role="unit_head"
        ).update(
            authority_user_id=user_id,
            decision=decision,
            decided_at=now,
            comment=comment,
        )

        return Response({"detail": f"Decision recorded: {decision}."})


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------

class AdminApplicationsView(APIView):
    """GET /leave/admin/applications/ - all applications."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LeaveApplication.objects.all()
        status_filter = request.query_params.get("status")
        user_filter   = request.query_params.get("user_id")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if user_filter:
            qs = qs.filter(user_id=user_filter)
        return Response(LeaveApplicationListSerializer(qs, many=True).data)


class AdminOfflineRecordView(APIView):
    """POST /leave/admin/offline/ - record an offline-sanctioned leave."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        admin_user_id = _get_user_id(request)
        serializer = AdminOfflineRecordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        now = datetime.datetime.now(datetime.timezone.utc)
        application = LeaveApplication.objects.create(
            status=ApplicationStatus.SANCTIONED,
            submitted_at=now,
            decided_at=now,
            decided_by_user_id=admin_user_id,
            **serializer.validated_data,
        )
        return Response(
            LeaveApplicationDetailSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class PolicyView(APIView):
    """GET/POST /leave/admin/policy/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LeavePolicy.objects.all().order_by("-year_label")
        return Response(LeavePolicySerializer(qs, many=True).data)

    def post(self, request):
        serializer = LeavePolicySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        policy = serializer.save()
        return Response(LeavePolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class HolidayCalendarView(APIView):
    """GET/POST/PATCH /leave/admin/calendar/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = HolidayCalendar.objects.all().order_by("date")
        return Response(HolidayCalendarSerializer(qs, many=True).data)

    def post(self, request):
        serializer = HolidayCalendarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        entry = serializer.save()
        return Response(HolidayCalendarSerializer(entry).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None):
        if not pk:
            return Response({"detail": "pk required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            entry = HolidayCalendar.objects.get(pk=pk)
        except HolidayCalendar.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = HolidayCalendarSerializer(entry, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        entry = serializer.save()
        return Response(HolidayCalendarSerializer(entry).data)


class ResumptionView(APIView):
    """POST /leave/applications/<pk>/resumption/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user_id = _get_user_id(request)
        try:
            application = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if application.status != ApplicationStatus.SANCTIONED:
            return Response(
                {"detail": "Can only record resumption for sanctioned leave."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resume_date = serializer.validated_data["actual_resume_date"]
        application.actual_resume_date = resume_date
        application.save(update_fields=["actual_resume_date", "updated_at"])
        return Response({"detail": "Resumption date recorded.", "actual_resume_date": str(resume_date)})
