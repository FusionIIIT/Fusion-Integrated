"""API views for Employee Leave Management."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory_contracts
from modules.leave.api.serializers import (
    LeaveActionResponseSerializer,
    LeaveApplicationCreateSerializer,
    LeaveBalanceSerializer,
    LeaveCancelSerializer,
    LeaveExtendSerializer,
    LeaveHealthResponseSerializer,
    LeaveRequestSerializer,
    LeaveResumeSerializer,
    LeaveReviewSerializer,
    LeaveSanctionSerializer,
    LeaveTypeSerializer,
    LeaveWithdrawSerializer,
    OfflineLeaveCreateSerializer,
    ResumptionRecordSerializer,
    ResumptionReviewSerializer,
    SubstituteNominationSerializer,
    SubstituteResponseSerializer,
)
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, LeaveType
from modules.leave.selectors import (
    get_approvals_queue,
    get_pending_substitute_requests,
    get_user_balances,
    get_user_requests,
)
from modules.leave.services import (
    apply_for_leave,
    record_offline_leave,
    request_cancellation,
    request_extension,
    respond_to_substitute,
    review_cancellation_unit_head,
    review_extension_unit_head,
    review_resumption,
    review_unit_head,
    sanction_cancellation,
    sanction_extension,
    sanction_leave,
    submit_resumption,
    withdraw_leave_request,
)

ADMIN_ROLES = frozenset({"Leave Administrator", "hr_officer"})

HOD_ROLES = frozenset({"HOD"})

HIGHER_APPROVER_ROLES = frozenset(
    {
        "Dean",
        "Dean Academic",
        "Registrar",
        "Deputy Registrar (Estt.)",
        "Director",
        "Leave Approver",
    }
)

# Authorized workflow stages per approver designation
APPROVER_ROLE_STAGES: dict[str, frozenset[str]] = {
    "HOD": frozenset(
        {
            LeaveState.AWAITING_UNIT_HEAD,
            LeaveState.CANCELLATION_PENDING_UNIT_HEAD,
            LeaveState.AWAITING_EXTENSION_UNIT_HEAD,
        }
    ),
    "Leave Approver": frozenset(
        {
            LeaveState.AWAITING_UNIT_HEAD,
            LeaveState.AWAITING_SANCTION,
            LeaveState.CANCELLATION_PENDING_UNIT_HEAD,
            LeaveState.CANCELLATION_PENDING_SANCTION,
            LeaveState.AWAITING_EXTENSION_UNIT_HEAD,
            LeaveState.EXTENSION_PENDING_SANCTION,
            LeaveState.RESUMPTION_REVIEW_PENDING,
        }
    ),
    "Dean": frozenset(
        {
            LeaveState.AWAITING_SANCTION,
            LeaveState.CANCELLATION_PENDING_SANCTION,
            LeaveState.EXTENSION_PENDING_SANCTION,
            LeaveState.RESUMPTION_REVIEW_PENDING,
        }
    ),
    "Dean Academic": frozenset(
        {
            LeaveState.AWAITING_SANCTION,
            LeaveState.CANCELLATION_PENDING_SANCTION,
            LeaveState.EXTENSION_PENDING_SANCTION,
            LeaveState.RESUMPTION_REVIEW_PENDING,
        }
    ),
    "Registrar": frozenset(
        {
            LeaveState.AWAITING_ESTABLISHMENT,
            LeaveState.AWAITING_SANCTION,
            LeaveState.CANCELLATION_PENDING_ESTABLISHMENT,
            LeaveState.CANCELLATION_PENDING_SANCTION,
            LeaveState.EXTENSION_PENDING_ESTABLISHMENT,
            LeaveState.EXTENSION_PENDING_SANCTION,
            LeaveState.RESUMPTION_REVIEW_PENDING,
        }
    ),
    "Deputy Registrar (Estt.)": frozenset(
        {
            LeaveState.AWAITING_ESTABLISHMENT,
            LeaveState.CANCELLATION_PENDING_ESTABLISHMENT,
            LeaveState.EXTENSION_PENDING_ESTABLISHMENT,
        }
    ),
    "Director": frozenset(
        {
            LeaveState.AWAITING_DIRECTOR,
            LeaveState.AWAITING_SANCTION,
            LeaveState.CANCELLATION_PENDING_SANCTION,
            LeaveState.EXTENSION_PENDING_SANCTION,
            LeaveState.RESUMPTION_REVIEW_PENDING,
        }
    ),
}


def _get_hod_department(user_id: int, roles: tuple[str, ...]) -> str | None:
    """Resolve department if user is acting with HOD authority."""
    user_roles = set(roles)
    if HOD_ROLES.intersection(user_roles) and not HIGHER_APPROVER_ROLES.intersection(user_roles):
        user_dict = directory_contracts.get_users([user_id])
        hod_user = user_dict.get(user_id)
        return hod_user.department if hod_user else None
    return None


class LeaveHealthView(APIView):
    """Health and status endpoint for Employee Leave Management."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: LeaveHealthResponseSerializer})
    def get(self, request):
        return Response({"status": "active", "module": "leave"})


class LeaveTypeListView(APIView):
    """List active leave types and their basic rules."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: LeaveTypeSerializer(many=True)})
    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).order_by("code")
        return Response(LeaveTypeSerializer(types, many=True).data)


class LeaveBalancesView(APIView):
    """Retrieve leave balances for the authenticated employee."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="year", type=int, location=OpenApiParameter.QUERY, description="Calendar year"
            ),
        ],
        responses={200: LeaveBalanceSerializer(many=True)},
    )
    def get(self, request):
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else None
        balances = get_user_balances(user_id=request.principal.user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveRequestsView(APIView):
    """Retrieve leave request history for the authenticated employee."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Request status",
            ),
            OpenApiParameter(
                name="year", type=int, location=OpenApiParameter.QUERY, description="Calendar year"
            ),
        ],
        responses={200: LeaveRequestSerializer(many=True)},
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else None
        requests = get_user_requests(
            user_id=request.principal.user_id,
            status=status_filter,
            year=year,
        )
        return Response(LeaveRequestSerializer(requests, many=True).data)


class LeaveRequestDetailView(APIView):
    """Retrieve details of a single leave application with object-level isolation."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: LeaveRequestSerializer})
    def get(self, request, pk: int):
        try:
            req = LeaveRequest.objects.select_related("leave_type").get(pk=pk)
        except LeaveRequest.DoesNotExist:
            raise NotFoundError("Leave request not found.") from None

        actor_id = request.principal.user_id
        if req.user_id != actor_id:
            has_approval = request.principal.has_permission("leave.request.approve")
            has_view = request.principal.has_permission("leave.request.view")
            has_balance_update = request.principal.has_permission("leave.balance.update")
            has_type_manage = request.principal.has_permission("leave.type.manage")

            if not (has_approval or has_view or has_balance_update or has_type_manage):
                raise PermissionDeniedError(
                    "You do not have permission to view this leave request."
                )

            # Administrative and Audit roles have system-wide visibility
            is_admin = bool(ADMIN_ROLES.intersection(set(request.principal.roles)))
            if not is_admin and not has_view:
                roles = set(request.principal.roles)
                is_hod = bool(HOD_ROLES.intersection(roles))
                is_higher = bool(HIGHER_APPROVER_ROLES.intersection(roles))

                if not (is_hod or is_higher or req.current_handler_user_id == actor_id):
                    raise PermissionDeniedError(
                        "You do not hold an authorized approver role for this request."
                    )

                # Department scope enforcement for HOD
                if is_hod and not is_higher:
                    hod_dept = _get_hod_department(actor_id, request.principal.roles)
                    if not hod_dept or hod_dept != req.department:
                        raise PermissionDeniedError(
                            "You cannot view leave requests outside your department."
                        )

                # Approval stage authorization:
                # Approvers cannot inspect requests that have not reached an approval stage
                unsubmitted_stages = {
                    LeaveState.DRAFT,
                    LeaveState.AWAITING_SUBSTITUTE,
                    LeaveState.APPLICANT_ACTION_REQUIRED,
                }
                if req.status in unsubmitted_stages:
                    raise PermissionDeniedError("Request is not yet submitted for approver review.")

        return Response(LeaveRequestSerializer(req).data)


class LeaveApplicationCreateView(APIView):
    """Submit a leave application or withdraw (CFR-EL-002, EL-UC-001)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(
        request=LeaveApplicationCreateSerializer, responses={201: LeaveRequestSerializer}
    )
    def post(self, request):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = apply_for_leave(
            actor_user_id=request.principal.user_id,
            actor_roles=request.principal.roles,
            **serializer.validated_data,
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="ID of the leave request to withdraw",
                required=False,
            ),
        ],
        responses={200: LeaveRequestSerializer},
    )
    def delete(self, request, pk=None):
        if not request.principal.has_permission("leave.request.delete"):
            raise PermissionDeniedError("You do not have permission to withdraw leave requests.")

        data = request.data if isinstance(request.data, dict) else {}
        target_id = pk or request.query_params.get("id") or data.get("id")
        if not target_id:
            raise BadRequestError("A valid request ID must be provided to withdraw an application.")

        req = withdraw_leave_request(
            actor_user_id=request.principal.user_id,
            request_id=int(target_id),
            remarks=data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(req).data)


class LeaveWithdrawView(APIView):
    """Request withdrawal of an eligible pending application (BR-EL-022, EL-UC-007)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.delete")]

    @extend_schema(request=LeaveWithdrawSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        serializer = LeaveWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = withdraw_leave_request(
            actor_user_id=request.principal.user_id,
            request_id=pk,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(req).data)


class LeaveCancelView(APIView):
    """Request cancellation of approved leave before its start date (CW-EL-02)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=LeaveCancelSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        serializer = LeaveCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = request_cancellation(
            actor_user_id=request.principal.user_id,
            request_id=pk,
            reason=serializer.validated_data["reason"],
        )
        return Response(LeaveRequestSerializer(req).data)


class LeaveExtendView(APIView):
    """Request an eligible extension of ongoing leave (CW-EL-03)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=LeaveExtendSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        serializer = LeaveExtendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = request_extension(
            actor_user_id=request.principal.user_id,
            request_id=pk,
            extension_end_date=serializer.validated_data["extension_end_date"],
            reason=serializer.validated_data["reason"],
            substitute_user_id=serializer.validated_data.get("substitute_user_id"),
        )
        return Response(LeaveRequestSerializer(req).data)


class LeaveResumeView(APIView):
    """Submit duty resumption details (CW-EL-04)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=LeaveResumeSerializer, responses={200: ResumptionRecordSerializer})
    def post(self, request, pk: int):
        serializer = LeaveResumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = submit_resumption(
            actor_user_id=request.principal.user_id,
            request_id=pk,
            actual_resumption_date=serializer.validated_data["actual_resumption_date"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(ResumptionRecordSerializer(record).data)


class SubstituteNominationsListView(APIView):
    """Retrieve pending substitute nominations for the authenticated user."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: SubstituteNominationSerializer(many=True)})
    def get(self, request):
        nominations = get_pending_substitute_requests(substitute_user_id=request.principal.user_id)
        return Response(SubstituteNominationSerializer(nominations, many=True).data)


class SubstituteRespondView(APIView):
    """Accept or decline a substitute nomination (BR-EL-014, EL-UC-002)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(
        request=SubstituteResponseSerializer, responses={200: SubstituteNominationSerializer}
    )
    def post(self, request, pk: int):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nomination = respond_to_substitute(
            nomination_id=pk,
            actor_user_id=request.principal.user_id,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(SubstituteNominationSerializer(nomination).data)


class ApprovalsQueueView(APIView):
    """Retrieve pending leave approvals assigned to or authorized for the actor."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Request status",
            ),
        ],
        responses={200: LeaveRequestSerializer(many=True)},
    )
    def get(self, request):
        user_id = request.principal.user_id
        roles = request.principal.roles
        hod_dept = _get_hod_department(user_id, roles)
        status_filter = request.query_params.get("status")

        qs = LeaveRequest.objects.none()
        for role in roles:
            if role in APPROVER_ROLE_STAGES:
                role_qs = get_approvals_queue(approver_user_id=user_id, approver_role=role)
                role_qs = role_qs.filter(status__in=APPROVER_ROLE_STAGES[role])
                if role == "HOD" and hod_dept:
                    role_qs = role_qs.filter(department=hod_dept)
                qs = qs | role_qs

        # Direct assignment by user ID
        user_qs = get_approvals_queue(approver_user_id=user_id, approver_role=None)
        qs = (qs | user_qs).distinct()

        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response(LeaveRequestSerializer(qs.order_by("created_at", "id"), many=True).data)

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def post(self, request):
        return Response({"status": "stub_decided"})


class ApprovalReviewView(APIView):
    """Record Unit Head recommendation or decision."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    @extend_schema(request=LeaveReviewSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target = LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:
            raise NotFoundError("Leave request not found.") from None

        decision = serializer.validated_data["decision"]
        remarks = serializer.validated_data.get("remarks", "")

        if target.status == LeaveState.CANCELLATION_PENDING_UNIT_HEAD:
            req = review_cancellation_unit_head(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        elif target.status == LeaveState.AWAITING_EXTENSION_UNIT_HEAD:
            req = review_extension_unit_head(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        else:
            req = review_unit_head(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        return Response(LeaveRequestSerializer(req).data)


class ApprovalSanctionView(APIView):
    """Record final sanction decision by Sanctioning Authority."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    @extend_schema(request=LeaveSanctionSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, pk: int):
        serializer = LeaveSanctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target = LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:
            raise NotFoundError("Leave request not found.") from None

        decision = serializer.validated_data["decision"]
        remarks = serializer.validated_data.get("remarks", "")

        if target.status == LeaveState.CANCELLATION_PENDING_SANCTION:
            req = sanction_cancellation(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        elif target.status == LeaveState.EXTENSION_PENDING_SANCTION:
            req = sanction_extension(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        else:
            req = sanction_leave(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                request_id=pk,
                decision=decision,
                remarks=remarks,
            )
        return Response(LeaveRequestSerializer(req).data)


class ApprovalResumptionReviewView(APIView):
    """Review duty resumption records where authorized."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    @extend_schema(request=ResumptionReviewSerializer, responses={200: ResumptionRecordSerializer})
    def post(self, request, pk: int):
        serializer = ResumptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = review_resumption(
            actor_user_id=request.principal.user_id,
            actor_roles=request.principal.roles,
            request_id=pk,
            decision=serializer.validated_data.get("decision", "approved"),
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(ResumptionRecordSerializer(record).data)


class AdminOfflineLeaveView(APIView):
    """Record authorized offline-sanctioned leave (BR-EL-029)."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.update")]

    @extend_schema(request=OfflineLeaveCreateSerializer, responses={201: LeaveRequestSerializer})
    def post(self, request):
        user_roles = set(request.principal.roles)
        if not ADMIN_ROLES.intersection(user_roles):
            raise PermissionDeniedError(
                "Only authorized Leave Administrators or HR Officers may record offline leave."
            )

        serializer = OfflineLeaveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = record_offline_leave(
            actor_user_id=request.principal.user_id,
            actor_roles=request.principal.roles,
            **serializer.validated_data,
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveAdminView(APIView):
    """Administrative endpoints for leave balance updates and policy management."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.update")]

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def post(self, request):
        user_roles = set(request.principal.roles)
        if not ADMIN_ROLES.intersection(user_roles):
            raise PermissionDeniedError(
                "Only authorized Leave Administrators or HR Officers may perform "
                "administrative operations."
            )

        # Offline leave recording
        data = request.data if isinstance(request.data, dict) else {}
        if "offline_sanction_reference" in data:
            serializer = OfflineLeaveCreateSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            req = record_offline_leave(
                actor_user_id=request.principal.user_id,
                actor_roles=request.principal.roles,
                **serializer.validated_data,
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)

        # Policy & quota management operations
        if not request.principal.has_permission("leave.type.manage"):
            raise PermissionDeniedError(
                "You do not have permission to manage leave types or policies."
            )

        action = data.get("action")
        if action == "update_policy":
            return Response({"status": "policy_updated"})

        raise BadRequestError("Unsupported administrative operation.")
