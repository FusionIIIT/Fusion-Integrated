from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    HolidayCalendar,
    LeaveStatus,
    SubstituteStatus,
)
from modules.leave.api.serializers import (
    LeaveApplicationSerializer,
    LeaveApplicationCreateSerializer,
    SubstituteResponseSerializer,
    UnitHeadReviewSerializer,
    SanctionDecisionSerializer,
    CancellationRequestSerializer,
    ResumptionSerializer,
    LeaveBalanceSerializer,
    HolidayCalendarSerializer,
)
from modules.leave.services.workflow import (
    submit_application,
    respond_substitute,
    unit_head_review,
    sanction_decision,
    withdraw_application,
    cancel_approved_leave,
    submit_resumption,
)
from modules.leave.services.ledger import (
    ensure_balance,
    credit_annual_entitlements,
)


def _get_principal_id(request) -> int:
    if not (request.principal and request.principal.user_id):
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user.pk
        return 1
    return int(request.principal.user_id)


def _parse_year_param(val, default_year: int) -> int:
    if val is None or val == "":
        return default_year
    try:
        parsed = int(val)
        if 1900 <= parsed <= 2100:
            return parsed
    except (ValueError, TypeError):
        pass
    raise ValidationError({"year": "Year must be a valid 4-digit integer between 1900 and 2100."})


class LeaveApplicationListCreateView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(responses={200: LeaveApplicationSerializer(many=True)})
    def get(self, request):
        user_id = _get_principal_id(request)
        apps = LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)

    @extend_schema(request=LeaveApplicationCreateSerializer, responses={201: LeaveApplicationSerializer})
    def post(self, request):
        user_id = _get_principal_id(request)
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        app = LeaveApplication(
            user_id=user_id,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            half_day_slot=data.get("half_day_slot", "none"),
            reason=data.get("reason", ""),
            substitute_id=data.get("substitute_id"),
            unit_head_id=data.get("unit_head_id"),
            sanctioning_authority_id=data.get("sanctioning_authority_id"),
            station_leave_applied=data.get("station_leave_applied", False),
            station_leave_address=data.get("station_leave_address", ""),
            station_leave_contact=data.get("station_leave_contact", ""),
        )

        try:
            if data.get("submit_now", True):
                submit_application(app, user_id)
            else:
                app.full_clean()
                app.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(responses={200: LeaveApplicationSerializer})
    def get(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found.")

        is_owner = app.user_id == user_id
        is_sub = app.substitute_id == user_id
        is_uh = app.unit_head_id == user_id
        is_sanc = app.sanctioning_authority_id == user_id

        if not (is_owner or is_sub or is_uh or is_sanc):
            raise PermissionDenied(detail="You do not have access to view this leave application.")

        return Response(LeaveApplicationSerializer(app).data)


class LeaveApplicationSubmitView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(request=None, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found.")

        try:
            submit_application(app, user_id)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class LeaveApplicationWithdrawView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(request=None, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found.")

        try:
            withdraw_application(app, user_id)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class LeaveApplicationCancelView(APIView):
    serializer_class = CancellationRequestSerializer

    @extend_schema(request=CancellationRequestSerializer, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found.")

        serializer = CancellationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cancel_approved_leave(app, user_id, serializer.validated_data["reason"])
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class LeaveApplicationResumeView(APIView):
    serializer_class = ResumptionSerializer

    @extend_schema(request=ResumptionSerializer, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, user_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found.")

        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            submit_resumption(
                app,
                user_id,
                serializer.validated_data["actual_resumption_date"],
                serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class SubstituteRequestsView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(responses={200: LeaveApplicationSerializer(many=True)})
    def get(self, request):
        user_id = _get_principal_id(request)
        apps = LeaveApplication.objects.filter(
            substitute_id=user_id,
            status=LeaveStatus.SUBSTITUTE_PENDING,
            substitute_status=SubstituteStatus.PENDING,
        ).order_by("-created_at")
        return Response(LeaveApplicationSerializer(apps, many=True).data)


class SubstituteRespondView(APIView):
    serializer_class = SubstituteResponseSerializer

    @extend_schema(request=SubstituteResponseSerializer, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, substitute_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Substitute request #{pk} not found.")

        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            respond_substitute(
                app,
                user_id,
                serializer.validated_data["accept"],
                serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class ApprovalQueueView(APIView):
    serializer_class = LeaveApplicationSerializer

    @extend_schema(responses={200: LeaveApplicationSerializer(many=True)})
    def get(self, request):
        user_id = _get_principal_id(request)
        uh_pending = LeaveApplication.objects.filter(
            unit_head_id=user_id,
            status=LeaveStatus.UNIT_HEAD_PENDING,
        )
        sanc_pending = LeaveApplication.objects.filter(
            sanctioning_authority_id=user_id,
            status=LeaveStatus.SANCTIONING_PENDING,
        )
        combined = (uh_pending | sanc_pending).distinct().order_by("-created_at")
        return Response(LeaveApplicationSerializer(combined, many=True).data)


class UnitHeadReviewView(APIView):
    serializer_class = UnitHeadReviewSerializer

    @extend_schema(request=UnitHeadReviewSerializer, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, unit_head_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found for Unit Head review.")

        serializer = UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            unit_head_review(
                app,
                user_id,
                serializer.validated_data["approve_or_recommend"],
                serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class SanctionDecisionView(APIView):
    serializer_class = SanctionDecisionSerializer

    @extend_schema(request=SanctionDecisionSerializer, responses={200: LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _get_principal_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, sanctioning_authority_id=user_id)
        except LeaveApplication.DoesNotExist:
            raise NotFound(detail=f"Leave application #{pk} not found for Sanctioning Authority decision.")

        serializer = SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sanction_decision(
                app,
                user_id,
                serializer.validated_data["approve"],
                serializer.validated_data.get("remarks", ""),
            )
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))

        return Response(LeaveApplicationSerializer(app).data)


class LeaveBalancesView(APIView):
    serializer_class = LeaveBalanceSerializer

    @extend_schema(responses={200: LeaveBalanceSerializer(many=True)})
    def get(self, request):
        user_id = _get_principal_id(request)
        year = _parse_year_param(request.query_params.get("year"), timezone.now().year)
        credit_annual_entitlements(user_id, year, is_faculty=True)
        balances = LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")
        return Response(LeaveBalanceSerializer(balances, many=True).data)

    @extend_schema(request=None, responses={200: None})
    def post(self, request):
        user_id = _get_principal_id(request)
        year = _parse_year_param(request.data.get("year"), timezone.now().year)
        is_faculty = bool(request.data.get("is_faculty", True))
        results = credit_annual_entitlements(user_id, year, is_faculty=is_faculty)
        return Response({"status": "seeded", "year": year, "balances": results})


class HolidayCalendarView(APIView):
    serializer_class = HolidayCalendarSerializer

    @extend_schema(responses={200: HolidayCalendarSerializer(many=True)})
    def get(self, request):
        year = _parse_year_param(request.query_params.get("year"), timezone.now().year)
        holidays = HolidayCalendar.objects.filter(year=year)
        return Response(HolidayCalendarSerializer(holidays, many=True).data)
