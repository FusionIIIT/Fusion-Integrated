from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from core.api.views import BaseAPIView
from modules.leave.models import LeaveApplication, SubstituteRequest
from modules.leave.selectors import (
    list_my_leaves,
    get_substitute_requests_by_user,
    get_pending_approvals_for_user,
    get_leave_balances,
    get_calendar_entries,
)
from modules.leave.services import (
    apply_for_leave,
    withdraw_application,
    request_cancellation,
    request_extension,
    submit_resumption_declaration,
    respond_to_substitute_request,
    nominate_replacement_substitute,
    review_by_unit_head,
    verify_by_establishment,
    sanction_application,
    process_cancellation_decision,
    review_resumption_declaration,
    record_offline_sanctioned_leave,
    run_year_end_processing,
    process_sla_reminders_and_escalations,
)
from modules.leave.serializers import (
    LeaveApplicationSerializer,
    SubstituteRequestSerializer,
)

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return list_my_leaves(self.request.principal.user_id)

    @action(detail=False, methods=['post'])
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user_id'] = self.request.principal.user_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, *args, **kwargs):
        instance = self.get_object()
        services.withdraw_application(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def request_cancellation(self, request, *args, **kwargs):
        instance = self.get_object()
        services.request_cancellation(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def request_extension(self, request, *args, **kwargs):
        instance = self.get_object()
        services.request_extension(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def resumption(self, request, *args, **kwargs):
        instance = self.get_object()
        services.submit_resumption_declaration(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubstituteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubstituteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_substitute_requests_by_user(self.request.principal.user_id)

    @action(detail=True, methods=['post'])
    def respond(self, request, *args, **kwargs):
        instance = self.get_object()
        services.respond_to_substitute_request(instance.id, request.data['response'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def nominate_replacement(self, request, *args, **kwargs):
        data = request.data.copy()
        data['substitute_user_id'] = self.request.principal.user_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        services.nominate_replacement_substitute(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApprovalViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = get_pending_approvals_for_user(request.principal.user_id)
        serializer = LeaveApplicationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def review_unit_head(self, request, *args, **kwargs):
        instance = self.get_object()
        services.review_by_unit_head(instance.id, request.data['decision'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def verify_establishment(self, request, *args, **kwargs):
        instance = self.get_object()
        services.verify_by_establishment(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def sanction(self, request, *args, **kwargs):
        instance = self.get_object()
        services.sanction_application(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def review_cancellation(self, request, *args, **kwargs):
        instance = self.get_object()
        services.process_cancellation_decision(instance.id, request.data['decision'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def review_resumption(self, request, *args, **kwargs):
        instance = self.get_object()
        services.review_resumption_declaration(instance.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BalanceViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = get_leave_balances(request.principal.user_id)
        serializer = LeaveApplicationSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def ledger(self, request, *args, **kwargs):
        # Implement ledger history retrieval logic here
        pass


class CalendarViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_calendar_entries()


class AdminLeaveViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['post'])
    def record_offline(self, request, *args, **kwargs):
        services.record_offline_sanctioned_leave(request.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def run_year_end(self, request, *args, **kwargs):
        services.run_year_end_processing()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def process_sla(self, request, *args, **kwargs):
        services.process_sla_reminders_and_escalations()
        return Response(status=status.HTTP_204_NO_CONTENT)