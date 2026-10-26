"""REST API Views for Employee Leave Management (ELM).

Implements endpoints adhering to:
- Use Cases: EL-UC-001..021
- Business Rules: BR-EL-001..038
- Workflows: BW-EL-01..17, CW-EL-01..04
- Role-based authorization & non-director self-approval prohibition (BR-EL-036)
"""
from __future__ import annotations

import datetime
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .domain import state_machine as sm
from .models import HolidayCalendar, LeaveBalance, LeaveRequest
from .permissions import (
    CanReviewUnitHead,
    CanSanctionLeave,
    IsLeaveAdmin,
    IsLeaveRequestOwner,
    IsNominatedSubstitute,
    get_actor_id,
    get_actor_roles,
)
from .selectors import (
    get_leave_request_by_id,
    get_pending_approvals_for_user,
    get_published_holidays_for_year,
    get_user_leave_balances,
    list_leave_requests_for_user,
)
from .serializers import (
    CancellationRequestSerializer,
    CancellationReviewSerializer,
    HolidayCalendarSerializer,
    LeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    OfflineSanctionSerializer,
    ReplacementSubstituteSerializer,
    SanctionDecisionSerializer,
    SubstituteResponseSerializer,
    UnitHeadReviewSerializer,
    YearEndRolloverSerializer,
)
from . import services


def _handle_service_call(func, *args, **kwargs):
    """Safely execute a domain service function and map exceptions to DRF responses."""
    try:
        return func(*args, **kwargs)
    except (DjangoValidationError, DRFValidationError) as exc:
        msg = exc.messages if hasattr(exc, "messages") else str(exc)
        return Response({"error": "validation_error", "detail": msg}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionDenied as exc:
        return Response({"error": "permission_denied", "detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except sm.InvalidTransition as exc:
        return Response(
            {"error": "invalid_transition", "detail": str(exc), "from": exc.from_state, "to": exc.to_state},
            status=status.HTTP_400_BAD_REQUEST,
        )


# --- EL-UC-001: Apply for Leave / List Requests ---
class LeaveRequestListCreateView(APIView):
    """List accessible leave requests or submit a new leave application."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        actor_id = get_actor_id(request)
        if not actor_id:
            return Response({"error": "unauthenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        roles = get_actor_roles(request)
        # If user requests a specific user_id and has administrative/review privileges
        target_user_id = request.query_params.get("user_id")
        if target_user_id and bool(roles & {"leave_admin", "unit_head", "dean", "director"}):
            try:
                user_filter = int(target_user_id)
            except ValueError:
                return Response({"error": "Invalid user_id filter"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user_filter = actor_id

        requests_qs = list_leave_requests_for_user(user_filter)
        status_filter = request.query_params.get("status")
        if status_filter:
            requests_qs = requests_qs.filter(status=status_filter)

        serializer = LeaveRequestSerializer(requests_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        actor_id = get_actor_id(request)
        if not actor_id:
            return Response({"error": "unauthenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = LeaveRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        roles = get_actor_roles(request)
        is_faculty = "faculty" in roles
        is_director = "director" in roles

        try:
            req = services.submit_leave_request(
                applicant_user_id=actor_id,
                data=serializer.validated_data,
                is_faculty=is_faculty,
                is_director=is_director,
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, DRFValidationError) as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            return Response({"error": "validation_error", "detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as exc:
            return Response({"error": "permission_denied", "detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except sm.InvalidTransition as exc:
            return Response({"error": "invalid_transition", "detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# --- Leave Request Detail ---
class LeaveRequestDetailView(generics.RetrieveAPIView):
    """Retrieve details and audit history of a leave request."""

    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        actor_id = get_actor_id(self.request)
        roles = get_actor_roles(self.request)

        # Access permitted if owner, substitute, review/sanction authority, or leave_admin
        has_access = (
            obj.user_id == actor_id
            or obj.substitute_id == actor_id
            or bool(roles & {"leave_admin", "unit_head", "hod", "dean", "director", "registrar"})
        )
        if not has_access:
            raise PermissionDenied("You do not have access to view this leave request.")
        return obj


# --- EL-UC-007: Withdraw Pending Request ---
class LeaveRequestWithdrawView(APIView):
    """Applicant immediately terminates in-flight request before final approval (EL-UC-007, BR-EL-022)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        remarks = request.data.get("remarks", "")
        res = _handle_service_call(services.withdraw_leave_request, pk, actor_id, remarks)
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-002: Substitute Respond ---
class SubstituteResponseView(APIView):
    """Nominated substitute accepts or declines responsibility request (EL-UC-002, BR-EL-015)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = SubstituteResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        accept = serializer.validated_data["action"] == "accept"
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(services.respond_substitute, pk, actor_id, accept, remarks)
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-019: Nominate Replacement Substitute ---
class NominateReplacementSubstituteView(APIView):
    """Applicant nominates replacement substitute after a decline (EL-UC-019)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = ReplacementSubstituteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_substitute_id = serializer.validated_data["substitute_id"]
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(
            services.nominate_replacement_substitute, pk, actor_id, new_substitute_id, remarks
        )
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-003: Unit Head Review ---
class UnitHeadReviewView(APIView):
    """Unit Head review: Approve/Reject for CL/RH; Recommend/Not-Recommend for higher-sanction (BR-EL-016..018)."""

    permission_classes = [permissions.IsAuthenticated, CanReviewUnitHead]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = UnitHeadReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        decision = serializer.validated_data["decision"]
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(services.review_unit_head, pk, actor_id, decision, remarks)
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-005: Sanction Decision ---
class SanctionDecisionView(APIView):
    """Final sanction decision by Sanctioning Authority or Director self-sanction (BR-EL-018, BR-EL-020)."""

    permission_classes = [permissions.IsAuthenticated, CanSanctionLeave]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)
        is_director = "director" in roles

        serializer = SanctionDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        approve = serializer.validated_data["decision"] == "approve"
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(
            services.sanction_leave_request, pk, actor_id, approve, remarks, is_director=is_director
        )
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-008: Request Pre-Start Cancellation ---
class RequestCancellationView(APIView):
    """Applicant requests pre-start cancellation of approved leave (EL-UC-008, BR-EL-023)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = CancellationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        remarks = serializer.validated_data["remarks"]
        res = _handle_service_call(services.request_cancellation, pk, actor_id, remarks)
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- Cancellation Unit Head Review ---
class CancellationUnitHeadReviewView(APIView):
    """Unit Head reviews approved leave cancellation."""

    permission_classes = [permissions.IsAuthenticated, CanReviewUnitHead]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = CancellationReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        decision = serializer.validated_data["decision"]
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(
            services.review_cancellation_unit_head, pk, actor_id, decision, remarks
        )
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- Cancellation Final Sanction ---
class CancellationSanctionView(APIView):
    """Sanctioning Authority makes final decision on cancellation."""

    permission_classes = [permissions.IsAuthenticated, CanSanctionLeave]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        serializer = SanctionDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        approve = serializer.validated_data["decision"] == "approve"
        remarks = serializer.validated_data.get("remarks", "")
        res = _handle_service_call(services.sanction_cancellation, pk, actor_id, approve, remarks)
        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


# --- EL-UC-012: View Balances ---
class LeaveBalanceListView(APIView):
    """View leave balances for current employee or target employee (EL-UC-012)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)

        target_user = request.query_params.get("user_id")
        if target_user and bool(roles & {"leave_admin", "unit_head", "dean", "director"}):
            try:
                user_id = int(target_user)
            except ValueError:
                return Response({"error": "Invalid user_id filter"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user_id = actor_id

        year_param = request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year

        balances = get_user_leave_balances(user_id, year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


# --- Pending Approvals Inbox ---
class PendingApprovalsInboxView(APIView):
    """List actionable work items pending for the current actor across roles."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)
        inbox_items = get_pending_approvals_for_user(actor_id, roles)
        return Response(LeaveRequestSerializer(inbox_items, many=True).data)


# --- EL-UC-015: Holiday Calendar ---
class HolidayCalendarListView(APIView):
    """View published institute holidays and Restricted Holidays (RH)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        year_param = request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year

        holidays = get_published_holidays_for_year(year)
        from .serializers import HolidaySerializer
        return Response(HolidaySerializer(holidays, many=True).data)


# --- EL-UC-015: Publish Holiday Calendar (Admin) ---
class HolidayCalendarPublishView(APIView):
    """Publish the holiday calendar for an academic year (EL-UC-015, BR-EL-031)."""

    permission_classes = [permissions.IsAuthenticated, IsLeaveAdmin]

    def post(self, request):
        actor_id = get_actor_id(request)
        year = request.data.get("year")
        if not year:
            return Response({"error": "year is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            year_int = int(year)
        except ValueError:
            return Response({"error": "year must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        cal = services.publish_holiday_calendar(year_int, actor_id)
        return Response(HolidayCalendarSerializer(cal).data, status=status.HTTP_200_OK)


# --- EL-UC-020: Year-End Rollover (Admin) ---
class YearEndRolloverView(APIView):
    """Execute year-end VL to EL conversion and balance rollover idempotently (EL-UC-020)."""

    permission_classes = [permissions.IsAuthenticated, IsLeaveAdmin]

    def post(self, request):
        serializer = YearEndRolloverSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        year = serializer.validated_data["year"]
        user_id = serializer.validated_data.get("user_id")

        if user_id:
            unused_vl, el_credited = services.process_year_end_vl_conversion(user_id, year)
            return Response(
                {
                    "message": "Year-end VL conversion completed successfully.",
                    "user_id": user_id,
                    "year": year,
                    "unused_vl": str(unused_vl),
                    "el_credited": str(el_credited),
                },
                status=status.HTTP_200_OK,
            )
        else:
            # Batch process for all faculty with VL balances in year
            faculty_balances = LeaveBalance.objects.filter(year=year, category="vl")
            results = []
            for bal in faculty_balances:
                unused_vl, el_credited = services.process_year_end_vl_conversion(bal.user_id, year)
                results.append({
                    "user_id": bal.user_id,
                    "unused_vl": str(unused_vl),
                    "el_credited": str(el_credited),
                })
            return Response({"year": year, "processed_count": len(results), "results": results})


# --- EL-UC-016: Offline Sanction Synchronization ---
class OfflineSanctionView(APIView):
    """Record already sanctioned offline leave directly into records (EL-UC-016, BR-EL-029)."""

    permission_classes = [permissions.IsAuthenticated, IsLeaveAdmin]

    def post(self, request):
        actor_id = get_actor_id(request)
        serializer = OfflineSanctionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            req = services.record_offline_sanctioned_leave(
                admin_user_id=actor_id,
                applicant_user_id=data["applicant_user_id"],
                category=data["category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                sanction_reference=data["sanction_reference"],
                is_faculty=data.get("is_faculty", False),
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, DRFValidationError) as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            return Response({"error": "validation_error", "detail": msg}, status=status.HTTP_400_BAD_REQUEST)


# --- Phase 1 Legacy Compatibility Views ---
class LeaveRequestCreateView(APIView):
    """Legacy CreateView compatible with Assignment 6A test signatures."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        view = LeaveRequestListCreateView()
        return view.post(request)


class LeaveRequestListView(APIView):
    """Legacy ListView compatible with Assignment 6A test signatures."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        view = LeaveRequestListCreateView()
        return view.get(request)


class LeaveRequestApproveView(APIView):
    """Legacy ApproveView: routes through secure review/sanction handler with RBAC enforcement."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)
        req = get_leave_request_by_id(pk)
        if not req:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        if req.user_id == actor_id and "director" not in roles:
            return Response(
                {"error": "permission_denied", "detail": "Non-director applicants cannot approve own leave (BR-EL-036)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if req.category in services.UNIT_HEAD_FINAL_CATEGORIES:
            res = _handle_service_call(services.review_unit_head, pk, actor_id, "approve", "Approved via legacy API.")
        else:
            res = _handle_service_call(
                services.sanction_leave_request, pk, actor_id, True, "Approved via legacy API.", is_director=("director" in roles)
            )

        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


class LeaveRequestRejectView(APIView):
    """Legacy RejectView: routes through secure review/sanction handler."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)
        req = get_leave_request_by_id(pk)
        if not req:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        if req.category in services.UNIT_HEAD_FINAL_CATEGORIES:
            res = _handle_service_call(services.review_unit_head, pk, actor_id, "reject", "Rejected via legacy API.")
        else:
            res = _handle_service_call(
                services.sanction_leave_request, pk, actor_id, False, "Rejected via legacy API.", is_director=("director" in roles)
            )

        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)


class LeaveRequestCancelView(APIView):
    """Legacy CancelView: routes through pre-start cancellation or withdrawal."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        actor_id = get_actor_id(request)
        req = get_leave_request_by_id(pk)
        if not req:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        if req.status in sm.IN_FLIGHT_PENDING:
            res = _handle_service_call(services.withdraw_leave_request, pk, actor_id, "Cancelled/Withdrawn via legacy API.")
        elif req.status == sm.APPROVED:
            res = _handle_service_call(services.request_cancellation, pk, actor_id, "Cancellation requested via legacy API.")
        else:
            return Response(
                {"error": "invalid_status", "detail": f"Cannot cancel request in status '{req.status}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(res, Response):
            return res
        return Response(LeaveRequestSerializer(res).data, status=status.HTTP_200_OK)
