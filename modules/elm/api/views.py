from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveExtensionSerializer,
    OfflineLeaveSerializer,
    ReplaceSubstituteSerializer,
    ResumptionSerializer,
    SanctionReviewSerializer,
    SubstituteResponseSerializer,
    UnitHeadReviewSerializer,
    YearEndProcessSerializer,
)
from modules.elm.models import LeaveApplication, LeaveStatus
from modules.elm.services import (
    cancel_approved_application,
    director_self_sanction,
    execute_year_end_processing,
    extend_leave_application,
    init_employee_balances,
    process_sla_checks,
    record_offline_leave,
    replace_substitute_or_proceed,
    respond_substitute,
    sanctioning_authority_review,
    submit_and_verify_resumption,
    submit_leave_application,
    unit_head_review,
    withdraw_pending_application,
)

MODULE_GRANT = HasModuleGrant("elm")


def _actor_id(request) -> str:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "username"):
        return str(principal.username)
    if request.user and request.user.is_authenticated:
        return str(request.user.username)
    return "anonymous"


def _is_faculty(request) -> bool:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "roles"):
        return "faculty" in principal.roles or "hod" in principal.roles or "dean" in principal.roles
    return False


def _is_director(request) -> bool:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "roles"):
        return "director" in principal.roles
    return False


class MyLeaveBalancesView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    def get(self, request):
        actor_id = _actor_id(request)
        is_fac = _is_faculty(request)
        balances = init_employee_balances(actor_id, is_faculty=is_fac)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class MyLeaveApplicationsView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    def get(self, request):
        actor_id = _actor_id(request)
        qs = LeaveApplication.objects.filter(applicant_id=actor_id).prefetch_related("history")
        return Response(LeaveApplicationSerializer(qs, many=True).data)

    def post(self, request):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _actor_id(request)
        is_fac = _is_faculty(request)
        is_dir = _is_director(request)

        app = submit_leave_application(
            actor_id,
            serializer.validated_data,
            is_faculty=is_fac,
            is_director=is_dir,
        )
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    def get(self, request, pk: int):
        app = LeaveApplication.objects.prefetch_related("history").get(pk=pk)
        return Response(LeaveApplicationSerializer(app).data)


class WithdrawLeaveApplicationView(APIView):
    """WF-EL-02: Withdraw pending leave request before approval."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.withdraw")]

    def post(self, request, pk: int):
        actor_id = _actor_id(request)
        reason = request.data.get("reason", "Withdrawn by applicant")
        app = withdraw_pending_application(pk, actor_id, reason)
        return Response(LeaveApplicationSerializer(app).data)


class CancelLeaveApplicationView(APIView):
    """WF-EL-03: Cancel approved leave before start, restoring balance."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.cancel")]

    def post(self, request, pk: int):
        actor_id = _actor_id(request)
        reason = request.data.get("reason", "Cancelled by applicant")
        app = cancel_approved_application(pk, actor_id, reason)
        return Response(LeaveApplicationSerializer(app).data)


class ExtendLeaveApplicationView(APIView):
    """WF-EL-04: Extension for ongoing EL/COL/VL."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.extend")]

    def post(self, request, pk: int):
        serializer = LeaveExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _actor_id(request)

        app = extend_leave_application(
            parent_id=pk,
            applicant_id=actor_id,
            new_end_date=serializer.validated_data["new_end_date"],
            reason=serializer.validated_data["reason"],
        )
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class SubmitResumptionView(APIView):
    """WF-EL-05: Duty resumption and early return."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.resume")]

    def post(self, request, pk: int):
        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _actor_id(request)

        app = submit_and_verify_resumption(
            application_id=pk,
            applicant_id=actor_id,
            actual_resumption_date=serializer.validated_data["actual_resumption_date"],
            verifier_id=actor_id,
            remarks=serializer.validated_data.get("remarks", "Duty resumption submitted"),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteRequestsView(APIView):
    """WF-EL-01: List leave requests where current user is nominated substitute."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.substitute.respond")]

    def get(self, request):
        actor_id = _actor_id(request)
        qs = LeaveApplication.objects.filter(
            substitute_id=actor_id,
            status=LeaveStatus.AWAITING_SUBSTITUTE,
        ).prefetch_related("history")
        return Response(LeaveApplicationSerializer(qs, many=True).data)


class RespondSubstituteView(APIView):
    """WF-EL-01: Substitute accept or decline."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.substitute.respond")]

    def post(self, request, pk: int):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _actor_id(request)

        app = respond_substitute(
            application_id=pk,
            substitute_id=actor_id,
            accept=serializer.validated_data["accept"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class ReplaceSubstituteView(APIView):
    """WF-EL-01: Applicant re-nominates substitute after decline."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        serializer = ReplaceSubstituteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _actor_id(request)

        app = replace_substitute_or_proceed(
            application_id=pk,
            applicant_id=actor_id,
            new_substitute_id=serializer.validated_data.get("new_substitute_id", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class UnitHeadApprovalsQueueView(APIView):
    """WF-EL-01: Unit Head pending review queue."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.review_unit_head")]

    def get(self, request):
        qs = LeaveApplication.objects.filter(
            status=LeaveStatus.AWAITING_UNIT_HEAD
        ).prefetch_related("history")
        return Response(LeaveApplicationSerializer(qs, many=True).data)


class UnitHeadReviewView(APIView):
    """WF-EL-01: Unit Head review decision."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.review_unit_head")]

    def post(self, request, pk: int):
        serializer = UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit_head_id = _actor_id(request)

        app = unit_head_review(
            application_id=pk,
            unit_head_id=unit_head_id,
            action=serializer.validated_data["action"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SanctioningQueueView(APIView):
    """WF-EL-01: Higher sanction authority review queue (SCL/EL/COL/VL)."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.sanction_final")]

    def get(self, request):
        qs = LeaveApplication.objects.filter(
            status__in=[LeaveStatus.AWAITING_SANCTION, LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION]
        ).prefetch_related("history")
        return Response(LeaveApplicationSerializer(qs, many=True).data)


class SanctionReviewView(APIView):
    """WF-EL-01: Higher sanction authority decision."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.sanction_final")]

    def post(self, request, pk: int):
        serializer = SanctionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sanctioner_id = _actor_id(request)

        app = LeaveApplication.objects.get(pk=pk)
        if app.status == LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION:
            res_app = director_self_sanction(
                application_id=pk,
                director_id=sanctioner_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        else:
            res_app = sanctioning_authority_review(
                application_id=pk,
                sanctioner_id=sanctioner_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        return Response(LeaveApplicationSerializer(res_app).data)


class RecordOfflineLeaveView(APIView):
    """WF-EL-06: Record offline/paper sanctioned leave."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.admin.record_offline")]

    def post(self, request):
        serializer = OfflineLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin_id = _actor_id(request)

        app = record_offline_leave(admin_id, serializer.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class YearEndProcessView(APIView):
    """WF-EL-07: Year-end processing."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.admin.yearend_process")]

    def post(self, request):
        serializer = YearEndProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = execute_year_end_processing(serializer.validated_data["year"])
        return Response(res)


class TriggerSLACheckView(APIView):
    """WF-EL-08: Trigger scheduled SLA reminder and escalation check."""
    permission_classes = [MODULE_GRANT, HasPermission("elm.admin.manage")]

    def post(self, request):
        res = process_sla_checks()
        return Response(res)
