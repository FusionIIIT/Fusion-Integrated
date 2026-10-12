"""Leave Management API views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date
from decimal import Decimal
from typing import Optional

from .serializers import LeaveApplicationSerializer, WorkflowTaskSerializer
from fusion_auth.principal import Principal
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, WorkflowTask, SLAEventLog,
    HolidayCalendar, VacationPeriod, OrganizationalUnit,
    LeaveHierarchy, LeaveHierarchyStep, LeavePolicy
)
from modules.leave_elm.services.leave import (
    _validate_leave_request, _create_application, _process_substitute_response,
    _route_to_sanctioning, _make_final_decision, _withdraw_application,
    _cancel_approved_leave, _extend_ongoing_leave, _submit_resumption,
    _record_offline_sanction, _get_leave_balances, _get_leave_history,
    _process_year_end, _process_sla_task
)
from modules.directory.contracts import get_users

class LeaveAPI(viewsets.GenericViewSet):
    permission_classes = []  # Handled by HasPermission decorators
    
    def get_serializer_class(self):
        return LeaveApplicationSerializer
    
    @action(detail=False, methods=['get'])
    def mine(self, request: dict) -> Response:
        """Get own leave applications."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        apps = LeaveApplication.objects.filter(user_id=user_id).order_by('-created_at')
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def apply(self, request: dict) -> Response:
        """Create new leave application."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = request.data
        category = data.get('category')
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])
        purpose = data.get('purpose', '')
        substitute_user_id = data.get('substitute_user_id')
        
        valid, errors = _validate_leave_request(
            user_id, category, start_date, end_date, substitute_user_id
        )
        if not valid:
            return Response({'errors': errors}, status=400)
        
        app = _create_application(
            user_id=user_id, category=category, start_date=start_date,
            end_date=end_date, purpose=purpose, substitute_user_id=substitute_user_id
        )
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data, status=201)
    
    @action(detail=True, methods=['get'])
    def details(self, request: dict) -> Response:
        """Get application details."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        app = LeaveApplication.objects.filter(id=app_id, user_id=user_id).first()
        if not app:
            return Response({'error': 'Not found'}, status=404)
        
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request: dict) -> Response:
        """Withdraw pending application."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _withdraw_application(app_id, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request: dict) -> Response:
        """Cancel approved leave."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _cancel_approved_leave(app_id, 'CANCELLED', user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def extend(self, request: dict) -> Response:
        """Extend ongoing leave."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        additional_days = Decimal(request.data.get('additional_days', '0'))
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _extend_ongoing_leave(app_id, additional_days, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resumption(self, request: dict) -> Response:
        """Submit resumption of duty."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        actual_date = date.fromisoformat(request.data.get('actual_date'))
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _submit_resumption(app_id, actual_date, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balances(self, request: dict) -> Response:
        """Get leave balances."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = _get_leave_balances(user_id)
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def history(self, request: dict) -> Response:
        """Get leave history."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        history = _get_leave_history(user_id)
        return Response(history)
    
    @action(detail=False, methods=['get'])
    def queue(self, request: dict) -> Response:
        """Get assigned tasks."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        tasks = WorkflowTask.objects.filter(assigned_to_user_id=user_id, status='PENDING')
        serializer = WorkflowTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def substitute_accept(self, request: dict) -> Response:
        """Accept substitute responsibility."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _process_substitute_response(app_id, user_id, accepted=True)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def substitute_decline(self, request: dict) -> Response:
        """Decline substitute responsibility."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        new_substitute_user_id = request.data.get('new_substitute_user_id')
        
        if not app_id or not user_id:
            return Response({'error': 'ID and User ID required'}, status=400)
        
        success, msg = _process_substitute_response(app_id, user_id, accepted=False, new_substitute_user_id=new_substitute_user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def review(self, request: dict) -> Response:
        """Review and make final decision."""
        app_id = request.get('id')
        user_id = request.get('principal', {}).get('user_id')
        decision = request.data.get('decision')
        
        if not app_id or not user_id or not decision:
            return Response({'error': 'ID, User ID and decision required'}, status=400)
        
        success, msg = _make_final_decision(app_id, decision, user_id)
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.get(id=app_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def policy(self, request: dict) -> Response:
        """Get current leave policy."""
        policy = _get_policy()
        return Response({
            'CL_DAYS': policy.cl_days,
            'RH_DAYS': policy.rh_days,
            'SCL_MAX_DAYS': policy.scl_max_days,
            'EL_DAYS': policy.el_days,
            'COL_DAYS': policy.col_days,
            'VL_DAYS': policy.vl_days,
            'VL_TO_EL_RATIO': float(policy.vl_to_el_ratio)
        })
    
    @action(detail=False, methods=['get'])
    def calendar(self, request: dict) -> Response:
        """Get holiday calendar."""
        cal = _get_calendar()
        return Response({
            'year': cal.year,
            'holidays': list(cal.holidays),
            'restricted_holidays': list(cal.restricted_holidays),
            'is_effective': cal.is_effective
        })
    
    @action(detail=False, methods=['post'])
    def offline_record(self, request: dict) -> Response:
        """Record offline-sanctioned leave."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        data = request.data
        category = data.get('category')
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])
        reference_number = data.get('reference_number', '')
        evidence = data.get('evidence', '')
        
        success, msg = _record_offline_sanction(
            user_id, category, start_date, end_date, reference_number, evidence
        )
        if not success:
            return Response({'error': msg}, status=400)
        
        app = LeaveApplication.objects.filter(user_id=user_id).last()
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def notifications(self, request: dict) -> Response:
        """Get SLA notifications."""
        user_id = request.get('principal', {}).get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=401)
        
        notifications = get_notifications(user_id)
        serializer = WorkflowTaskSerializer(notifications, many=True)
        return Response(serializer.data)
