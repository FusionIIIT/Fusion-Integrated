"""HTTP endpoints for Leave Management (ELM).

Views handle request parsing, authentication checks, delegation to services/selectors,
and serialization. Domain exceptions are mapped to standard platform HTTP error responses.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.domain.errors import (
    ElmDomainError,
    IllegalStateTransitionError,
    IneligibleCategoryError,
    InsufficientLeaveBalanceError,
    InvalidLeaveDateError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    StationLeaveValidationError,
)
from modules.elm.models import LeaveApplication
from modules.elm.selectors import applications as application_selectors
from modules.elm.services import applications as application_services

MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.leave.view_self"
P_APPLY = "elm.leave.apply"
P_WITHDRAW = "elm.leave.withdraw"
P_SUBSTITUTE = "elm.leave.substitute_respond"
P_REVIEW = "elm.leave.review_unit_head"
P_SANCTION = "elm.leave.sanction"


class _BaseView(APIView):
    """Base helper extracting current user and role claims from the session principal."""

    @property
    def current_user_id(self) -> int:
        principal = getattr(self.request, "principal", None)
        return principal.user_id if principal else self.request.user.id

    @property
    def is_faculty(self) -> bool:
        principal = getattr(self.request, "principal", None)
        return bool(principal and getattr(principal, "kind", None) == "faculty")

    def is_approver(self) -> bool:
        principal = getattr(self.request, "principal", None)
        if not principal:
            return False
        return principal.has_any_permission(P_REVIEW, P_SANCTION)


@extend_schema(responses=s.LeaveCategorySerializer(many=True))
class CategoryListView(_BaseView):
    """List all active leave categories with their quotas and rules."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        application_services.ensure_leave_categories()
        categories = application_selectors.list_categories()
        return Response(s.LeaveCategorySerializer(categories, many=True).data)


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class BalanceListView(_BaseView):
    """List leave balances for the currently authenticated employee."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        application_services.ensure_leave_categories()
        # Seed balances if missing
        for cat in application_selectors.list_categories():
            application_services.get_or_create_balance(self.current_user_id, cat)

        balances = application_selectors.list_user_balances(self.current_user_id)
        return Response(s.LeaveBalanceSerializer(balances, many=True).data)


class ApplicationListCreateView(_BaseView):
    """List current user's leave applications or submit a new leave request."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveApplicationListSerializer(many=True))
    def get(self, request):
        apps = application_selectors.list_applications_for_user(self.current_user_id)
        return Response(s.LeaveApplicationListSerializer(apps, many=True).data)

    @extend_schema(
        request=s.LeaveApplicationCreateSerializer,
        responses=s.LeaveApplicationDetailSerializer,
    )
    def post(self, request):
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        if not payload.is_valid():
            raise BadRequestError("Validation failed", details=payload.errors)

        data = payload.validated_data
        try:
            app = application_services.submit_leave_application(
                user_id=self.current_user_id,
                category_code=data["category_code"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                half_day=data.get("half_day", "none"),
                is_faculty=self.is_faculty,
                station_leave=data.get("station_leave", False),
                station_address=data.get("station_address", ""),
                station_start_date=data.get("station_start_date"),
                station_end_date=data.get("station_end_date"),
                emergency_contact=data.get("emergency_contact", ""),
                substitute_id=data.get("substitute_id"),
            )
        except OverlappingLeaveError as err:
            raise ConflictError(str(err)) from err
        except (
            InvalidLeaveDateError,
            IneligibleCategoryError,
            StationLeaveValidationError,
            InvalidSubstituteError,
            InsufficientLeaveBalanceError,
            ElmDomainError,
        ) as err:
            raise BadRequestError(str(err)) from err

        return Response(
            s.LeaveApplicationDetailSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(responses=s.LeaveApplicationDetailSerializer)
class ApplicationDetailView(_BaseView):
    """Fetch details and history of a single leave application. 404 if out of scope."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request, pk: int):
        app = application_selectors.get_application_scoped(
            application_id=pk,
            user_id=self.current_user_id,
            is_approver=self.is_approver(),
        )
        if not app:
            raise NotFoundError("Leave application not found.")
        return Response(s.LeaveApplicationDetailSerializer(app).data)


@extend_schema(
    request=s.LeaveWithdrawSerializer,
    responses=s.LeaveApplicationDetailSerializer,
)
class ApplicationWithdrawView(_BaseView):
    """Withdraw a pending leave application."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        payload = s.LeaveWithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        remarks = payload.validated_data.get("remarks", "")

        app = application_selectors.get_application_scoped(
            application_id=pk,
            user_id=self.current_user_id,
        )
        if not app:
            raise NotFoundError("Leave application not found.")

        try:
            updated = application_services.withdraw_application(
                application_id=pk,
                user_id=self.current_user_id,
                remarks=remarks,
            )
        except IllegalStateTransitionError as err:
            raise ConflictError(str(err)) from err
        except ElmDomainError as err:
            raise BadRequestError(str(err)) from err

        return Response(s.LeaveApplicationDetailSerializer(updated).data)


@extend_schema(
    request=s.SubstituteResponseSerializer,
    responses=s.LeaveApplicationDetailSerializer,
)
class SubstituteResponseView(_BaseView):
    """Accept or decline a nominated substitute request."""

    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, pk: int):
        payload = s.SubstituteResponseSerializer(data=request.data)
        if not payload.is_valid():
            raise BadRequestError("Validation failed", details=payload.errors)

        action = payload.validated_data["action"]
        remarks = payload.validated_data.get("remarks", "")

        try:
            updated = application_services.respond_substitute(
                application_id=pk,
                substitute_id=self.current_user_id,
                action=action,
                remarks=remarks,
            )
        except IllegalStateTransitionError as err:
            raise ConflictError(str(err)) from err
        except ElmDomainError as err:
            raise BadRequestError(str(err)) from err

        return Response(s.LeaveApplicationDetailSerializer(updated).data)


@extend_schema(responses=s.LeaveApplicationListSerializer(many=True))
class PendingApprovalsListView(_BaseView):
    """List applications pending action by current user (substitute, unit head, sanctioner)."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        apps = application_selectors.list_pending_approvals(
            user_id=self.current_user_id,
            is_approver=self.is_approver(),
        )
        return Response(s.LeaveApplicationListSerializer(apps, many=True).data)


@extend_schema(
    request=s.WorkflowTransitionSerializer,
    responses=s.LeaveApplicationDetailSerializer,
)
class ApplicationTransitionView(_BaseView):
    """Process workflow transition (Unit Head review or Sanctioning Authority decision)."""

    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION)]

    def post(self, request, pk: int):
        payload = s.WorkflowTransitionSerializer(data=request.data)
        if not payload.is_valid():
            raise BadRequestError("Validation failed", details=payload.errors)

        action = payload.validated_data["action"]
        remarks = payload.validated_data.get("remarks", "")

        app = application_selectors.get_application_scoped(
            application_id=pk,
            user_id=self.current_user_id,
            is_approver=True,
        )
        if not app:
            raise NotFoundError("Leave application not found.")

        try:
            if app.status == LeaveApplication.STATUS_SUBMITTED:
                updated = application_services.review_unit_head(
                    application_id=pk,
                    actor_id=self.current_user_id,
                    action=action,
                    remarks=remarks,
                )
            elif app.status == LeaveApplication.STATUS_PENDING_SANCTION:
                updated = application_services.review_sanctioning_authority(
                    application_id=pk,
                    actor_id=self.current_user_id,
                    action=action,
                    remarks=remarks,
                )
            else:
                raise ConflictError(
                    f"Application in status '{app.status}' cannot be transitioned."
                )
        except IllegalStateTransitionError as err:
            raise ConflictError(str(err)) from err
        except InsufficientLeaveBalanceError as err:
            raise BadRequestError(str(err)) from err
        except ElmDomainError as err:
            raise BadRequestError(str(err)) from err

        return Response(s.LeaveApplicationDetailSerializer(updated).data)
