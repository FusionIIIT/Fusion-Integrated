"""DRF API views for Employee Leave Management (ELM).

Authorization model
-------------------
Every view is gated by:
  1. HasModuleGrant("elm")         – the module is enabled for the caller's role
  2. HasPermission("elm.leave.X")  – the caller holds the specific fine-grained permission

Ownership
---------
Employees may only read/withdraw/cancel their own applications.
Action endpoints (substitute-respond, unit-head-review, sanction) validate that the
caller is the designated actor recorded on the leave request.
"""
from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.domain.errors import (
    InsufficientBalanceError,
    InvalidLeaveTransitionError,
    LeaveValidationError,
)
from modules.elm.selectors import (
    balances as balance_selectors,
    holidays as holiday_selectors,
    leaves as leave_selectors,
)
from modules.elm.services import (
    applications as application_services,
    balances as balance_services,
    workflows as workflow_services,
)
from modules.elm.api import serializers as s

# ── Permission objects (reused across views) ──────────────────────────────────
MODULE = HasModuleGrant("elm")
P_APPLY = HasPermission("elm.leave.apply")
P_VIEW_SELF = HasPermission("elm.leave.view_self")
P_SUBSTITUTE = HasPermission("elm.leave.substitute")
P_REVIEW = HasPermission("elm.leave.review")
P_SANCTION = HasPermission("elm.leave.sanction")
P_ADMIN = HasPermission("elm.leave.admin")


def _actor_user_id(request) -> int:
    """Extract the authenticated actor's user_id.  Raises 401 if not resolvable."""
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return int(principal.user_id)
    user = getattr(request, "user", None)
    if user and getattr(user, "id", None):
        return int(user.id)
    # Permit test header only when DEBUG is True
    from django.conf import settings
    if getattr(settings, "DEBUG", False):
        hdr = request.META.get("HTTP_X_USER_ID")
        if hdr and hdr.isdigit():
            return int(hdr)
    raise BadRequestError("Unable to determine authenticated user.")


# ── Employee endpoints ────────────────────────────────────────────────────────

class MyLeavesView(APIView):
    """List caller's own leave applications or submit a new leave application."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def get(self, request):
        user_id = _actor_user_id(request)
        qs = leave_selectors.visible_leaves_for_user(user_id)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        # Posting also requires apply permission in addition to view_self
        if not P_APPLY().has_permission(request, self):
            raise PermissionDeniedError("elm.leave.apply permission required to submit a leave application.")
        user_id = _actor_user_id(request)
        serializer = s.LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = application_services.apply_for_leave(
                user_id=user_id,
                category=data["category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                is_half_day=data.get("is_half_day", False),
                half_day_period=data.get("half_day_period"),
                leaving_station=data.get("leaving_station", False),
                station_start_date=data.get("station_start_date"),
                station_end_date=data.get("station_end_date"),
                station_address=data.get("station_address", ""),
                emergency_phone=data.get("emergency_phone", ""),
                substitute_user_id=data.get("substitute_user_id"),
                unit_head_user_id=data.get("unit_head_user_id"),
                sanctioning_authority_user_id=data.get("sanctioning_authority_user_id"),
            )
            return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except LeaveValidationError as e:
            raise BadRequestError(str(e)) from e
        except InsufficientBalanceError as e:
            raise ConflictError(str(e)) from e


class LeaveDetailWithdrawView(APIView):
    """Retrieve own leave application details, or withdraw an in-flight request."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def _own_leave_or_404(self, pk: int, user_id: int):
        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        if req.user_id != user_id:
            raise NotFoundError(f"Leave application #{pk} does not exist.")  # 404 not 403 (don't leak existence)
        return req

    def get(self, request, pk: int):
        user_id = _actor_user_id(request)
        req = self._own_leave_or_404(pk, user_id)
        return Response(s.LeaveRequestSerializer(req).data)

    def delete(self, request, pk: int):
        user_id = _actor_user_id(request)
        self._own_leave_or_404(pk, user_id)  # ownership check before service call
        try:
            req = application_services.withdraw_leave(leave_id=pk, actor_user_id=user_id)
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


class LeaveCancellationView(APIView):
    """Request pre-start cancellation of caller's own approved leave."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        # Ownership: only the applicant may cancel their own leave
        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        if req.user_id != user_id:
            raise NotFoundError(f"Leave application #{pk} does not exist.")

        serializer = s.CancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data.get("remarks", "")

        try:
            req = application_services.cancel_approved_leave(
                leave_id=pk,
                actor_user_id=user_id,
                remarks=remarks,
            )
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


class LeaveResumptionView(APIView):
    """Record duty resumption after approved leave completion."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        if req.user_id != user_id:
            raise NotFoundError(f"Leave application #{pk} does not exist.")

        serializer = s.ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = application_services.resume_duty(
                leave_id=pk,
                actor_user_id=user_id,
                actual_resumption_date=data["actual_resumption_date"],
                remarks=data.get("remarks", ""),
            )
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


class MyBalancesView(APIView):
    """View caller's leave balances and entitlements for a given year."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def get(self, request):
        user_id = _actor_user_id(request)
        year_param = request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else date.today().year

        balances = list(balance_selectors.get_user_balances(user_id=user_id, year=year))
        if not balances:
            balances = balance_services.seed_default_balances(user_id=user_id, year=year)

        return Response(s.LeaveBalanceSerializer(balances, many=True).data)


# ── Workflow endpoints ────────────────────────────────────────────────────────

class SubstituteQueueView(APIView):
    """Queue of leave applications awaiting this user's substitute response."""
    permission_classes = [MODULE, P_SUBSTITUTE]

    def get(self, request):
        user_id = _actor_user_id(request)
        qs = leave_selectors.pending_substitute_requests(user_id)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)


class SubstituteRespondView(APIView):
    """Accept or decline substitute responsibility for a specific leave application."""
    permission_classes = [MODULE, P_SUBSTITUTE]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)

        # Verify caller is actually the designated substitute for this request
        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        if req.substitute_user_id != user_id:
            raise PermissionDeniedError("You are not the designated substitute for this leave application.")

        serializer = s.SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = workflow_services.respond_as_substitute(
                leave_id=pk,
                substitute_user_id=user_id,
                accepted=data["accepted"],
                remarks=data.get("remarks", ""),
            )
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


class UnitHeadQueueView(APIView):
    """List applications assigned to this Unit Head that await review."""
    permission_classes = [MODULE, P_REVIEW]

    def get(self, request):
        user_id = _actor_user_id(request)
        qs = leave_selectors.pending_unit_head_reviews(unit_head_user_id=user_id)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)


class UnitHeadReviewView(APIView):
    """Submit Unit Head recommendation or rejection for a specific application."""
    permission_classes = [MODULE, P_REVIEW]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)

        # Verify caller is the assigned Unit Head for this request
        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        if req.unit_head_user_id is not None and req.unit_head_user_id != user_id:
            raise PermissionDeniedError("You are not the assigned Unit Head for this leave application.")

        serializer = s.UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = workflow_services.review_as_unit_head(
                leave_id=pk,
                unit_head_user_id=user_id,
                recommended=data["recommended"],
                remarks=data.get("remarks", ""),
            )
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


class SanctionQueueView(APIView):
    """List applications awaiting sanction decision by this Competent Authority."""
    permission_classes = [MODULE, P_SANCTION]

    def get(self, request):
        user_id = _actor_user_id(request)
        qs = leave_selectors.pending_sanctions(authority_user_id=user_id)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)


class SanctionDecisionView(APIView):
    """Record final sanction or rejection by the Competent Authority."""
    permission_classes = [MODULE, P_SANCTION]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)

        req = leave_selectors.get_leave_by_id(pk)
        if not req:
            raise NotFoundError(f"Leave application #{pk} does not exist.")
        # If a specific sanctioning authority is recorded, enforce it
        if (req.sanctioning_authority_user_id is not None
                and req.sanctioning_authority_user_id != user_id):
            raise PermissionDeniedError("You are not the assigned Sanctioning Authority for this application.")

        serializer = s.SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = workflow_services.sanction_leave(
                leave_id=pk,
                authority_user_id=user_id,
                approved=data["approved"],
                remarks=data.get("remarks", ""),
            )
            return Response(s.LeaveRequestSerializer(req).data)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e


# ── Admin / calendar endpoints ────────────────────────────────────────────────

class HolidayCalendarView(APIView):
    """Retrieve published holidays for a year (no special permission required beyond module access)."""
    permission_classes = [MODULE, P_VIEW_SELF]

    def get(self, request):
        year_param = request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else date.today().year
        qs = holiday_selectors.get_holidays_for_year(year)
        return Response(s.HolidayCalendarSerializer(qs, many=True).data)
