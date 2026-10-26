from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from modules.leave_elm.models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveAction,
    HolidayCalendar,
)
from modules.leave_elm.api.serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveActionSerializer,
    LeaveApplicationReadSerializer,
    LeaveApplicationCreateSerializer,
    SubstituteConsentSerializer,
    SubstituteNominationSerializer,
    UnitHeadDecisionSerializer,
    HigherSanctionDecisionSerializer,
    CancellationSerializer,
    ResumptionSerializer,
    YearEndConversionSerializer,
    HolidayCalendarSerializer,
)
from modules.leave_elm.services import (
    apply_leave,
    respond_substitute,
    nominate_new_substitute,
    process_unit_head_decision,
    process_higher_sanction_decision,
    withdraw_application,
    cancel_approved_leave,
    convert_faculty_vl_to_el,
    process_resumption,
)
# Module permission constants required for accesscontrol manifest enforcement
PERMISSION_APPLICATION_VIEW = "leave_elm.application.view"
PERMISSION_APPLICATION_APPLY = "leave_elm.application.apply"
PERMISSION_APPLICATION_APPROVE = "leave_elm.application.approve"
PERMISSION_BALANCE_MANAGE = "leave_elm.balance.manage"
PERMISSION_REPORT_VIEW = "leave_elm.report.view"


def _get_request_username(request) -> str:
    """Helper to safely extract authenticated username or fallback header/param."""
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        return request.user.username
    # Fallback to header or query parameter for testing/tokenless dev
    return request.headers.get('X-User', request.query_params.get('user', 'anonymous'))


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.AllowAny]


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        username = self.request.query_params.get('username')
        if username:
            return LeaveBalance.objects.filter(username=username)
        current_user = _get_request_username(self.request)
        if current_user and current_user != 'anonymous':
            return LeaveBalance.objects.filter(username=current_user)
        return super().get_queryset()


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all().order_by('-created_at')
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return LeaveApplicationCreateSerializer
        return LeaveApplicationReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = _get_request_username(self.request)
        role = self.request.query_params.get('role')

        if role == 'substitute':
            return qs.filter(substitute_username=user, status='SUBSTITUTE_PENDING')
        elif role == 'unit_head':
            return qs.filter(status='PENDING_UNIT_HEAD')
        elif role == 'higher_sanction':
            return qs.filter(status='PENDING_HIGHER_SANCTION')
        elif role == 'my_leaves':
            return qs.filter(applicant_username=user)
        
        applicant = self.request.query_params.get('applicant')
        if applicant:
            return qs.filter(applicant_username=applicant)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        applicant = _get_request_username(request)
        # Allow explicit applicant override if passed by admin
        if 'applicant_username' in request.data:
            applicant = request.data['applicant_username']

        try:
            application = apply_leave(
                applicant_username=applicant,
                leave_type_code=data['leave_type_code'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                half_day=data.get('half_day', False),
                half_day_period=data.get('half_day_period', 'NONE'),
                reason=data.get('reason', ''),
                substitute_username=data.get('substitute_username'),
                station_leave=data.get('station_leave', False),
                station_details=data.get('station_details'),
                actor_username=applicant
            )
        except ValidationError as e:
            return Response({'error': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)

        read_serializer = LeaveApplicationReadSerializer(application)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        try:
            app = withdraw_application(
                application=application,
                applicant_username=actor,
                remarks=request.data.get('remarks', '')
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = CancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = cancel_approved_leave(
                application=application,
                applicant_username=actor,
                reason=serializer.validated_data['reason']
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def substitute_consent(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = SubstituteConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = respond_substitute(
                application=application,
                substitute_username=actor,
                accept=serializer.validated_data['accept'],
                remarks=serializer.validated_data.get('remarks', '')
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def nominate_substitute(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = SubstituteNominationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = nominate_new_substitute(
                application=application,
                applicant_username=actor,
                new_substitute_username=serializer.validated_data['new_substitute_username']
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unit_head_decision(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = UnitHeadDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = process_unit_head_decision(
                application=application,
                actor_username=actor,
                decision=serializer.validated_data['decision'],
                remarks=serializer.validated_data.get('remarks', '')
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def higher_sanction_decision(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = HigherSanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = process_higher_sanction_decision(
                application=application,
                actor_username=actor,
                decision=serializer.validated_data['decision'],
                remarks=serializer.validated_data.get('remarks', '')
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resumption(self, request, pk=None):
        application = self.get_object()
        actor = _get_request_username(request)
        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            app = process_resumption(
                application=application,
                actual_resumption_date=serializer.validated_data['actual_resumption_date'],
                actor_username=actor,
                remarks=serializer.validated_data.get('remarks', '')
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HolidayCalendarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HolidayCalendar.objects.all().order_by('date')
    serializer_class = HolidayCalendarSerializer
    permission_classes = [permissions.AllowAny]


class YearEndConversionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = YearEndConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            converted = convert_faculty_vl_to_el(
                faculty_username=serializer.validated_data['faculty_username'],
                year=serializer.validated_data['year']
            )
            return Response({
                'status': 'success',
                'faculty_username': serializer.validated_data['faculty_username'],
                'year': serializer.validated_data['year'],
                'converted_el_days': str(converted)
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)