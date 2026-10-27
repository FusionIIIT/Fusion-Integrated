from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import (
    LeaveRequest, LeaveBalance, LeaveSubstituteConsent, DutyResumption,
    HolidayCalendar, LeaveStatus
)
from modules.elm.api.serializers import (
    LeaveRequestSerializer, LeaveRequestCreateSerializer,
    LeaveBalanceSerializer, SubstituteConsentSerializer,
    DutyResumptionSerializer, HolidayCalendarSerializer
)
from modules.elm.services import leave_service

MODULE = HasModuleGrant("leave_elm")

def current_user_id(request):
    principal = getattr(request, "principal", None)
    if principal is None or getattr(principal, "user_id", None) is None:
        raise PermissionDenied("Cannot identify current Fusion user.")
    return int(principal.user_id)

class LeaveRequestListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self", "leave_elm.request.apply")]
    
    def get(self, request):
        items = LeaveRequest.objects.filter(user_id=current_user_id(request)).order_by('-created_at')
        return Response(LeaveRequestSerializer(items, many=True).data)
        
    def post(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = leave_service.apply_for_leave(user_id=current_user_id(request), **serializer.validated_data)
            return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class LeaveWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.withdraw", "leave_elm.request.apply")]
    
    def post(self, request, pk):
        try:
            obj = leave_service.withdraw_leave_request(request_id=pk, user_id=current_user_id(request), reason=request.data.get('reason', ''))
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class LeaveCancellationRequestView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.cancel", "leave_elm.request.apply")]
    
    def post(self, request, pk):
        try:
            obj = leave_service.request_cancellation(request_id=pk, user_id=current_user_id(request), reason=request.data.get('reason', ''))
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class SubstituteQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.substitute.respond")]
    
    def get(self, request):
        items = LeaveRequest.objects.filter(substitute_user_id=current_user_id(request), status=LeaveStatus.PENDING_SUBSTITUTE)
        return Response(LeaveRequestSerializer(items, many=True).data)
        
class SubstituteConsentView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.substitute.respond")]
    
    def post(self, request, pk):
        decision = request.data.get('decision')
        note = request.data.get('note', '')
        try:
            obj = leave_service.respond_substitute_consent(request_id=pk, substitute_user_id=current_user_id(request), decision=decision, note=note)
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class UnitHeadQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]
    
    def get(self, request):
        items = LeaveRequest.objects.filter(status=LeaveStatus.PENDING_UNIT_HEAD)
        return Response(LeaveRequestSerializer(items, many=True).data)
        
class UnitHeadReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]
    
    def post(self, request, pk):
        decision = request.data.get('decision')
        note = request.data.get('note', '')
        try:
            obj = leave_service.review_unit_head(request_id=pk, reviewer_user_id=current_user_id(request), decision=decision, note=note)
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class HigherSanctionQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.sanction")]
    
    def get(self, request):
        items = LeaveRequest.objects.filter(status=LeaveStatus.PENDING_SANCTION)
        return Response(LeaveRequestSerializer(items, many=True).data)
        
class HigherSanctionDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.sanction")]
    
    def post(self, request, pk):
        decision = request.data.get('decision')
        note = request.data.get('note', '')
        try:
            obj = leave_service.sanction_final_decision(request_id=pk, sanctioner_user_id=current_user_id(request), decision=decision, note=note)
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class CancellationReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review", "leave_elm.request.sanction")]
    
    def post(self, request, pk):
        decision = request.data.get('decision')
        note = request.data.get('note', '')
        try:
            obj = leave_service.review_cancellation(request_id=pk, reviewer_user_id=current_user_id(request), decision=decision, note=note)
            return Response(LeaveRequestSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class DutyResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.apply")]
    
    def post(self, request, pk):
        resumption_date = request.data.get('actual_resumption_date')
        reason = request.data.get('reason', '')
        try:
            obj = leave_service.submit_duty_resumption(request_id=pk, user_id=current_user_id(request), actual_resumption_date=resumption_date, reason=reason)
            return Response(DutyResumptionSerializer(obj).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class DutyResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.sanction")]
    
    def post(self, request, pk):
        decision = request.data.get('decision')
        note = request.data.get('note', '')
        try:
            obj = leave_service.review_duty_resumption(resumption_id=pk, reviewer_user_id=current_user_id(request), decision=decision, note=note)
            return Response(DutyResumptionSerializer(obj).data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.balance.view_self")]
    
    def get(self, request):
        balances = LeaveBalance.objects.filter(user_id=current_user_id(request), year=timezone.localdate().year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)
        
class HolidayCalendarListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.calendar.view")]
    
    def get(self, request):
        holidays = HolidayCalendar.objects.filter(year=timezone.localdate().year).order_by('date')
        return Response(HolidayCalendarSerializer(holidays, many=True).data)
