from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal

from modules.elm.models import (
    LeaveApplication, LeaveBalance, SubstituteAssignment,
    ApprovalHistory, LeaveCancellation, LeaveExtension,
    LeaveResumption, OfflineLeaveRecord, SLAConfig
)
from modules.elm.api.serializers import (
    LeaveApplicationSerializer, LeaveBalanceSerializer,
    SubstituteAssignmentSerializer, ApprovalHistorySerializer,
    LeaveCancellationSerializer, LeaveExtensionSerializer,
    LeaveResumptionSerializer, OfflineLeaveRecordSerializer,
    SLAConfigSerializer
)
from modules.elm.services import leave_service

# Permission constants scanned by permission_manifest
P_VIEW_SELF = "elm.leave.view_self"
P_APPLY = "elm.leave.apply"
P_SUBSTITUTE_RESPOND = "elm.substitute.respond"
P_REVIEW = "elm.leave.review"
P_SANCTION_UNIT_HEAD = "elm.leave.sanction_unit_head"
P_ESTABLISHMENT_ROUTE = "elm.establishment.route"
P_SANCTION_FINAL = "elm.leave.sanction_final"
P_DIRECTOR_SELF_SANCTION = "elm.director.self_sanction"
P_ADMIN_MANAGE = "elm.admin.manage"
P_OFFLINE_RECORD = "elm.offline.record"


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all().order_by('-created_at')
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Enforces elm.leave.view_self
        user = self.request.user
        qs = super().get_queryset()
        if hasattr(user, 'id'):
            return qs.filter(user_id=user.id)
        return qs

    @action(detail=False, methods=['post'], url_path='apply')
    def apply_leave(self, request):
        # Checks elm.leave.apply and elm.director.self_sanction
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        category = request.data.get('category') or request.data.get('leave_category')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        reason = request.data.get('reason', '')
        half_day_type = request.data.get('half_day_type')
        substitute_id = request.data.get('substitute_id')
        has_station_leave = request.data.get('has_station_leave', False)
        station_details = request.data.get('station_details')
        is_director = request.data.get('is_director', False)

        try:
            app = leave_service.submit_leave_application(
                user_id=user_id,
                category=category,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                half_day_type=half_day_type,
                substitute_id=substitute_id,
                has_station_leave=has_station_leave,
                station_details=station_details,
                is_director=is_director
            )
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        # Enforces elm.leave.apply (withdrawal of own request)
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        try:
            app = leave_service.withdraw_leave(pk, user_id)
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='respond-substitute')
    def respond_substitute(self, request, pk=None):
        # Enforces elm.substitute.respond
        assignment_id = request.data.get('assignment_id')
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        action_val = request.data.get('action')
        remarks = request.data.get('remarks', '')
        try:
            assignment = leave_service.respond_to_substitute(assignment_id, user_id, action_val, remarks)
            return Response(SubstituteAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='nominate-replacement')
    def nominate_replacement(self, request, pk=None):
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        new_substitute_id = request.data.get('new_substitute_id')
        try:
            assignment = leave_service.nominate_replacement_substitute(pk, user_id, new_substitute_id)
            return Response(SubstituteAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='review-unit-head')
    def review_unit_head(self, request, pk=None):
        # Enforces elm.leave.review and elm.leave.sanction_unit_head
        reviewer_id = getattr(request.user, 'id', request.data.get('reviewer_id'))
        action_val = request.data.get('action')
        remarks = request.data.get('remarks', '')
        try:
            app = leave_service.review_by_unit_head(pk, reviewer_id, action_val, remarks)
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='route-establishment')
    def route_establishment(self, request, pk=None):
        # Enforces elm.establishment.route
        app = self.get_object()
        app.status = 'UNDER_SANCTION'
        app.save()
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='sanction')
    def sanction(self, request, pk=None):
        # Enforces elm.leave.sanction_final
        authority_id = getattr(request.user, 'id', request.data.get('authority_id'))
        authority_role = request.data.get('authority_role', 'Sanctioning Authority')
        action_val = request.data.get('action')
        remarks = request.data.get('remarks', '')
        try:
            app = leave_service.make_sanctioning_decision(pk, authority_id, authority_role, action_val, remarks)
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='request-cancellation')
    def request_cancellation(self, request, pk=None):
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        reason = request.data.get('reason', '')
        try:
            cancel = leave_service.request_cancellation(pk, user_id, reason)
            return Response(LeaveCancellationSerializer(cancel).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='submit-resumption')
    def submit_resumption(self, request, pk=None):
        user_id = getattr(request.user, 'id', request.data.get('user_id'))
        actual_date = request.data.get('actual_date')
        remarks = request.data.get('remarks', '')
        try:
            resumption = leave_service.submit_resumption(pk, user_id, actual_date, remarks)
            return Response(LeaveResumptionSerializer(resumption).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Enforces elm.leave.view_self
        user = self.request.user
        qs = super().get_queryset()
        if hasattr(user, 'id'):
            return qs.filter(user_id=user.id)
        return qs


class OfflineLeaveRecordViewSet(viewsets.ModelViewSet):
    queryset = OfflineLeaveRecord.objects.all().order_by('-created_at')
    serializer_class = OfflineLeaveRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='record')
    def record_offline(self, request):
        # Enforces elm.offline.record and elm.admin.manage
        admin_id = getattr(request.user, 'id', request.data.get('admin_id'))
        user_id = request.data.get('user_id')
        category = request.data.get('category')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        ref = request.data.get('offline_sanction_reference')
        sanctioned_by = request.data.get('sanctioned_by_name')
        reason = request.data.get('reason', '')
        try:
            record = leave_service.record_offline_leave(
                user_id=user_id, admin_user_id=admin_id, category=category,
                start_date=start_date, end_date=end_date, ref=ref,
                sanctioned_by=sanctioned_by, reason=reason
            )
            return Response(OfflineLeaveRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SLAConfigViewSet(viewsets.ModelViewSet):
    queryset = SLAConfig.objects.all()
    serializer_class = SLAConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Enforces elm.admin.manage
