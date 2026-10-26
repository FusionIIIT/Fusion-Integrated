"""Views for ELM API."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from rest_framework import exceptions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..domain.rules import calculate_leave_days, validate_substitute
from ..models import (
    LeaveAction,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
)
from .serializers import (
    ApprovalActionSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveCancelRequestSerializer,
    ReplacementSubstituteSerializer,
    SubstituteActionSerializer,
)
from .utils import get_caller_id


class LeaveBalanceListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        if user_id is None:
            return LeaveBalance.objects.none()
        return LeaveBalance.objects.filter(user_id=user_id)


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("elm"), HasPermission("elm.leave.create")]
        return [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        if user_id is None:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(applicant_id=user_id).order_by("-created_at")

    def perform_create(self, serializer):
        user_id = get_caller_id(self.request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        substitute_id = serializer.validated_data.get("substitute_id")
        initial_status = (
            LeaveStatus.PENDING_SUBSTITUTE
            if substitute_id
            else LeaveStatus.PENDING_UNIT_HEAD
        )
        sub_status = (
            SubstituteStatus.PENDING
            if substitute_id
            else SubstituteStatus.ACCEPTED
        )

        app = serializer.save(
            applicant_id=user_id,
            status=initial_status,
            substitute_status=sub_status,
        )
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="submitted",
            comments=serializer.validated_data.get("reason", ""),
        )


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        if user_id is None:
            return LeaveApplication.objects.none()

        # Admin or Approver can view all applications
        perms = getattr(getattr(self.request, "principal", None), "permissions", set())
        if "elm.leave.manage" in perms or "elm.leave.approve" in perms:
            return LeaveApplication.objects.all()

        # Normal users can only view applications where they are applicant or substitute
        return LeaveApplication.objects.filter(
            applicant_id=user_id
        ) | LeaveApplication.objects.filter(
            substitute_id=user_id
        )


class LeaveWithdrawView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request, pk: int):
        user_id = get_caller_id(request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        try:
            app = LeaveApplication.objects.get(pk=pk, applicant_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        non_withdrawable = [
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
            LeaveStatus.WITHDRAWN,
            LeaveStatus.CANCELLED,
            LeaveStatus.CANCELLATION_REQUESTED,
        ]
        if app.status in non_withdrawable:
            return Response(
                {"error": f"Cannot withdraw leave with status {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.status = LeaveStatus.WITHDRAWN
        app.save(update_fields=["status", "updated_at"])
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="withdrawn",
            comments="Withdrawn by applicant.",
        )
        return Response(LeaveApplicationSerializer(app).data)


class LeaveCancelRequestView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.create")]
    serializer_class = LeaveCancelRequestSerializer

    def post(self, request, pk: int):
        user_id = get_caller_id(request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        serializer = LeaveCancelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        try:
            app = LeaveApplication.objects.get(pk=pk, applicant_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.status != LeaveStatus.APPROVED:
            return Response(
                {"error": f"Only approved leave can be cancelled (current status: {app.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pre-start check (BR-EL-023)
        if date.today() >= app.start_date:
            return Response(
                {"error": "Cannot cancel leave that has already started or passed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.status = LeaveStatus.CANCELLATION_REQUESTED
        app.save(update_fields=["status", "updated_at"])
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="cancellation_requested",
            comments=reason or "Cancellation requested by applicant.",
        )
        return Response(LeaveApplicationSerializer(app).data)


class ReplacementSubstituteView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.create")]
    serializer_class = ReplacementSubstituteSerializer

    def post(self, request, pk: int):
        user_id = get_caller_id(request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        serializer = ReplacementSubstituteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_substitute_id = serializer.validated_data["substitute_id"]

        try:
            app = LeaveApplication.objects.get(pk=pk, applicant_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.substitute_status != SubstituteStatus.DECLINED:
            return Response(
                {"error": "Replacement substitute can only be nominated after a decline."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_substitute(user_id, new_substitute_id)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Check replacement substitute overlap
        sub_leaves = LeaveApplication.objects.filter(
            applicant_id=new_substitute_id,
            status__in=[
                LeaveStatus.SUBMITTED,
                LeaveStatus.PENDING_SUBSTITUTE,
                LeaveStatus.PENDING_UNIT_HEAD,
                LeaveStatus.PENDING_SANCTION,
                LeaveStatus.APPROVED,
            ],
        )
        for sex in sub_leaves:
            if sex.start_date <= app.end_date and sex.end_date >= app.start_date:
                return Response(
                    {"error": "Nominated substitute has active leave during the requested period."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        app.substitute_id = new_substitute_id
        app.substitute_status = SubstituteStatus.PENDING
        app.status = LeaveStatus.PENDING_SUBSTITUTE
        app.save(update_fields=["substitute_id", "substitute_status", "status", "updated_at"])

        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="substitute_replaced",
            comments=f"Nominated replacement substitute #{new_substitute_id}",
        )
        return Response(LeaveApplicationSerializer(app).data)


class ApprovalQueueListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.approve")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        qs = LeaveApplication.objects.filter(
            status__in=[
                LeaveStatus.PENDING_UNIT_HEAD,
                LeaveStatus.PENDING_SANCTION,
                LeaveStatus.CANCELLATION_REQUESTED,
            ]
        )
        if user_id:
            qs = qs.exclude(applicant_id=user_id)
        return qs.order_by("-created_at")


class ApprovalActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.approve")]
    serializer_class = ApprovalActionSerializer

    @transaction.atomic
    def post(self, request, pk: int):
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_caller_id(request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        try:
            app = LeaveApplication.objects.select_for_update().get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Self-approval check (approvers cannot approve own applications)
        if app.applicant_id == user_id:
            return Response(
                {"error": "Self-approval is forbidden."},
                status=status.HTTP_403_FORBIDDEN,
            )

        act = serializer.validated_data["action"]
        comments = serializer.validated_data.get("comments", "")

        # State 1: Unit Head review
        if app.status == LeaveStatus.PENDING_UNIT_HEAD:
            if app.leave_type in [LeaveCategory.CL, LeaveCategory.RH]:
                # Unit Head has final authority (BR-EL-016)
                if act == "approve":
                    app.status = LeaveStatus.APPROVED
                    self._deduct_balance(app)
                elif act == "reject":
                    app.status = LeaveStatus.REJECTED
                    app.rejection_reason = comments
                else:
                    return Response(
                        {"error": "Action must be 'approve' or 'reject' for CL/RH."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # SCL, EL, COL, VL require recommendation (BR-EL-017)
                if act == "recommend":
                    app.status = LeaveStatus.PENDING_SANCTION
                    app.unit_head_recommendation = "recommended"
                elif act == "not_recommend":
                    app.status = LeaveStatus.PENDING_SANCTION
                    app.unit_head_recommendation = "not_recommended"
                else:
                    return Response(
                        {
                            "error": (
                                "Unit Head cannot give final approval/rejection for SCL/EL/COL/VL. "
                                "Please select 'recommend' or 'not_recommend'."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # State 2: Sanctioning authority review
        elif app.status == LeaveStatus.PENDING_SANCTION:
            if act == "approve":
                app.status = LeaveStatus.APPROVED
                self._deduct_balance(app)
            elif act == "reject":
                app.status = LeaveStatus.REJECTED
                app.rejection_reason = comments
            else:
                return Response(
                    {"error": "Action must be 'approve' or 'reject' at sanction stage."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # State 3: Cancellation request review (BR-EL-023)
        elif app.status == LeaveStatus.CANCELLATION_REQUESTED:
            if act == "approve":
                app.status = LeaveStatus.CANCELLED
                self._restore_balance(app)
            elif act == "reject":
                app.status = LeaveStatus.APPROVED
            else:
                return Response(
                    {"error": "Action must be 'approve' or 'reject' for cancellation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": f"Application is not awaiting approval (status: {app.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.save()
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action=act,
            comments=comments,
        )
        return Response(LeaveApplicationSerializer(app).data)

    def _deduct_balance(self, app: LeaveApplication):
        days = calculate_leave_days(app.leave_type, app.start_date, app.end_date, app.half_day)
        dec_days = Decimal(str(days))
        bal = LeaveBalance.objects.select_for_update().filter(
            user_id=app.applicant_id,
            year=app.start_date.year,
            leave_type=app.leave_type,
        ).first()
        if bal:
            bal.balance -= dec_days
            bal.used += dec_days
            bal.save()

    def _restore_balance(self, app: LeaveApplication):
        days = calculate_leave_days(app.leave_type, app.start_date, app.end_date, app.half_day)
        dec_days = Decimal(str(days))
        bal = LeaveBalance.objects.select_for_update().filter(
            user_id=app.applicant_id,
            year=app.start_date.year,
            leave_type=app.leave_type,
        ).first()
        if bal:
            bal.balance += dec_days
            bal.used -= dec_days
            bal.save()


class SubstituteQueueListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        if user_id is None:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(
            substitute_id=user_id,
            substitute_status=SubstituteStatus.PENDING,
        ).order_by("-created_at")


class SubstituteActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]
    serializer_class = SubstituteActionSerializer

    def post(self, request, pk: int):
        serializer = SubstituteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_caller_id(request)
        if user_id is None:
            raise exceptions.NotAuthenticated("Authentication required.")

        try:
            app = LeaveApplication.objects.get(pk=pk, substitute_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Substitute request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.substitute_status != SubstituteStatus.PENDING:
            return Response(
                {"error": f"Substitute request is already {app.substitute_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        act = serializer.validated_data["action"]
        comments = serializer.validated_data.get("comments", "")

        if act == "accept":
            app.substitute_status = SubstituteStatus.ACCEPTED
            app.status = LeaveStatus.PENDING_UNIT_HEAD
        else:
            app.substitute_status = SubstituteStatus.DECLINED

        app.save()
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action=f"substitute_{act}ed",
            comments=comments,
        )
        return Response(LeaveApplicationSerializer(app).data)


class LeaveAdminListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.manage")]
    serializer_class = LeaveApplicationSerializer
    queryset = LeaveApplication.objects.all().order_by("-created_at")
