from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    CancellationRequestSerializer,
    ExtensionRequestSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationReadSerializer,
    LeaveBalanceSerializer,
    ReplacementSubstituteSerializer,
    ResumptionReviewSerializer,
    ResumptionSubmitSerializer,
    SanctionActionSerializer,
    SubstituteActionSerializer,
    UnitHeadReviewSerializer,
)
from modules.elm.domain.errors import (
    ElmDomainError,
    InsufficientBalanceError,
    InvalidDateRangeError,
    InvalidLeaveCategoryError,
    InvalidStateTransitionError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    RestrictedHolidayMismatchError,
    VacationPeriodMismatchError,
)
from modules.elm.models import HolidayCalendar, LeaveApplication
from modules.elm.selectors.applications import (
    get_application_by_id,
    get_pending_establishment_reviews,
    get_pending_sanctions,
    get_pending_substitute_requests,
    get_pending_unit_head_reviews,
    get_user_applications,
)
from modules.elm.selectors.balances import get_user_balances
from modules.elm.services.applications import (
    apply_for_leave,
    cancel_approved_leave,
    extend_ongoing_leave,
    submit_resumption,
    withdraw_leave,
)
from modules.elm.services.balances import get_or_create_default_balances
from modules.elm.services.reviews import (
    nominate_replacement_substitute,
    respond_as_substitute,
    review_at_unit_head,
    review_resumption,
    route_at_establishment,
    sanction_final_decision,
)


def _handle_domain_error(e: ElmDomainError):
    if isinstance(e, (OverlappingLeaveError, InvalidStateTransitionError)):
        raise ConflictError(str(e)) from e
    if isinstance(
        e,
        (
            InsufficientBalanceError,
            InvalidLeaveCategoryError,
            InvalidDateRangeError,
            InvalidSubstituteError,
            RestrictedHolidayMismatchError,
            VacationPeriodMismatchError,
        ),
    ):
        raise BadRequestError(str(e)) from e
    raise BadRequestError(str(e)) from e


class LeaveApplicationListCreateView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave.view_self", "elm.leave.apply"),
    ]

    def get(self, request):
        if not request.principal.has_permission("elm.leave.view_self"):
            raise PermissionDeniedError("Permission elm.leave.view_self required.")

        user_id = request.principal.user_id
        is_faculty = request.principal.active_role == "faculty"
        get_or_create_default_balances(user_id=user_id, is_faculty=is_faculty)

        apps = get_user_applications(user_id=user_id)
        serializer = LeaveApplicationReadSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.principal.has_permission("elm.leave.apply"):
            raise PermissionDeniedError("Permission elm.leave.apply required.")

        user_id = request.principal.user_id
        is_faculty = request.principal.active_role == "faculty"
        is_director = request.principal.active_role == "director"

        get_or_create_default_balances(user_id=user_id, is_faculty=is_faculty)

        input_serializer = LeaveApplicationCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        try:
            application = apply_for_leave(
                user_id=user_id,
                leave_category=data["leave_category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                half_day=data["half_day"],
                half_day_type=data.get("half_day_type", ""),
                station_leave=data["station_leave"],
                station_start_date=data.get("station_start_date"),
                station_end_date=data.get("station_end_date"),
                station_address=data.get("station_address", ""),
                station_emergency_contact=data.get("station_emergency_contact", ""),
                substitute_required=data["substitute_required"],
                substitute_id=data.get("substitute_id"),
                is_director=is_director,
            )
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(
            LeaveApplicationReadSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationDetailView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request, pk: int):
        app = get_application_by_id(pk)
        if not app:
            raise NotFoundError(f"Leave application {pk} not found.")

        user_id = request.principal.user_id
        is_staff_reviewer = request.principal.has_any_permission(
            "elm.leave.unit_head_review", "elm.leave.sanction", "elm.leave.establishment"
        )
        if app.user_id != user_id and app.substitute_id != user_id and not is_staff_reviewer:
            raise PermissionDeniedError("Not authorized to view this application.")

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        try:
            app = withdraw_leave(application_id=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class LeaveApplicationCancelView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = CancellationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data.get("reason", "")

        try:
            app = cancel_approved_leave(application_id=pk, user_id=user_id, reason=reason)
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class LeaveApplicationExtendView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = ExtensionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            app = extend_ongoing_leave(
                application_id=pk,
                user_id=user_id,
                extended_end_date=data["extended_end_date"],
                reason=data["reason"],
                substitute_id=data.get("substitute_id"),
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationResumeView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = ResumptionSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            app = submit_resumption(
                application_id=pk,
                user_id=user_id,
                actual_resumption_date=data["actual_resumption_date"],
                resumption_reason=data.get("resumption_reason", ""),
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class SubstitutePendingListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]

    def get(self, request):
        user_id = request.principal.user_id
        pending = get_pending_substitute_requests(substitute_id=user_id)
        return Response(
            LeaveApplicationReadSerializer(pending, many=True).data,
            status=status.HTTP_200_OK,
        )


class SubstituteRespondView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = SubstituteActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        is_director = request.principal.active_role == "director"

        try:
            app = respond_as_substitute(
                application_id=pk,
                substitute_id=user_id,
                decision=data["decision"],
                remarks=data.get("remarks", ""),
                is_director=is_director,
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class SubstituteReplacementView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = ReplacementSubstituteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            app = nominate_replacement_substitute(
                application_id=pk,
                user_id=user_id,
                new_substitute_id=ser.validated_data["substitute_id"],
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class UnitHeadPendingListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.unit_head_review")]

    def get(self, request):
        pending = get_pending_unit_head_reviews()
        return Response(
            LeaveApplicationReadSerializer(pending, many=True).data,
            status=status.HTTP_200_OK,
        )


class UnitHeadReviewActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.unit_head_review")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = UnitHeadReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            app = review_at_unit_head(
                application_id=pk,
                unit_head_id=user_id,
                action=data["action"],
                remarks=data.get("remarks", ""),
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class EstablishmentPendingListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.establishment")]

    def get(self, request):
        pending = get_pending_establishment_reviews()
        return Response(
            LeaveApplicationReadSerializer(pending, many=True).data,
            status=status.HTTP_200_OK,
        )


class EstablishmentRouteActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.establishment")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        try:
            app = route_at_establishment(application_id=pk, reviewer_id=user_id)
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class SanctionPendingListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.sanction")]

    def get(self, request):
        pending = get_pending_sanctions()
        return Response(
            LeaveApplicationReadSerializer(pending, many=True).data,
            status=status.HTTP_200_OK,
        )


class SanctionActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.sanction")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = SanctionActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        role = getattr(request.principal, "active_role", "director")

        try:
            app = sanction_final_decision(
                application_id=pk,
                sanctioner_id=user_id,
                role=role,
                action=data["action"],
                remarks=data.get("remarks", ""),
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class ResumptionReviewActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.sanction")]

    def post(self, request, pk: int):
        user_id = request.principal.user_id
        ser = ResumptionReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        remarks = ser.validated_data.get("remarks", "")

        try:
            app = review_resumption(
                application_id=pk,
                reviewer_id=user_id,
                remarks=remarks,
            )
        except LeaveApplication.DoesNotExist as err:
            raise NotFoundError("Application not found.") from err
        except ElmDomainError as e:
            _handle_domain_error(e)

        return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_200_OK)


class LeaveBalanceListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        user_id = request.principal.user_id
        is_faculty = request.principal.active_role == "faculty"
        get_or_create_default_balances(user_id=user_id, is_faculty=is_faculty)

        balances = get_user_balances(user_id=user_id)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class HolidayCalendarListView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        holidays = HolidayCalendar.objects.filter(is_published=True).order_by("date")
        serializer = HolidayCalendarSerializer(holidays, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
