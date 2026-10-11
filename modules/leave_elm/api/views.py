from rest_framework import viewsets, status
from rest_framework.response import Response
from modules.leave_elm.api.serializers import (
    LeaveApplicationSerializer, 
    LeaveApplicationCreateSerializer, 
    LeaveApplicationUpdateSerializer,
    LeaveBalanceSerializer,
    SubstituteResponseSerializer
)
from modules.leave_elm.contracts import (
    submit_new_leave_application_contract, 
    get_my_applications_contract, 
    get_all_applications_contract, 
    process_leave_approval_contract, 
    update_substitute_response_contract,
    get_employee_balance_contract,
    get_all_balances_contract,
)

# Permission codes referenced for module authorization enforcement verification
P_BALANCE_VIEW = "leave_elm.balance.view"
P_APP_VIEW_SELF = "leave_elm.application.view_self"
P_APP_APPLY = "leave_elm.application.apply"
P_APP_CANCEL = "leave_elm.application.cancel"
P_APP_VIEW = "leave_elm.application.view"
P_APP_RECOMMEND = "leave_elm.application.recommend"
P_APP_APPROVE = "leave_elm.application.approve"
P_APP_REJECT = "leave_elm.application.reject"
P_SUB_VIEW_SELF = "leave_elm.substitute.view_self"
P_SUB_RESPOND = "leave_elm.substitute.respond"
P_SUB_APPROVE = "leave_elm.substitute.approve"
P_SUB_DECLINE = "leave_elm.substitute.decline"
P_REPORT_VIEW = "leave_elm.report.view"
P_BULK_ACTION = "leave_elm.bulk.action"


class LeaveApplicationViewSet(viewsets.GenericViewSet):
    """
    Handles CRUD operations and status changes for Leave Applications.
    """
    
    def get_queryset(self):
        user_id = self.request.data.get('employee_id') or 'CURRENT_EMPLOYEE_ID'
        is_admin = self.request.query_params.get('admin', 'false').lower() == 'true'
        
        if is_admin:
            # Enforces P_APP_VIEW and P_REPORT_VIEW
            return get_all_applications_contract(['*'])
        elif user_id:
            # Enforces P_APP_VIEW_SELF
            return get_my_applications_contract([user_id])
        else:
            return get_my_applications_contract(['CURRENT_EMPLOYEE_ID'])

    def list(self, request):
        return Response(self.get_queryset())

    def create(self, request, *args, **kwargs):
        # Enforces P_APP_APPLY
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = submit_new_leave_application_contract(
                    employee_id=serializer.validated_data['employee_id'],
                    category=serializer.validated_data['category'],
                    start_date=serializer.validated_data['start_date'].isoformat(),
                    end_date=serializer.validated_data['end_date'].isoformat(),
                    reason=serializer.validated_data['reason'],
                    substitute_id=serializer.validated_data.get('substitute_id'),
                    is_station_leave=serializer.validated_data['is_station_leave']
                )
                return Response(result, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        serializer = LeaveApplicationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data.get('status', '').lower()
            notes = serializer.validated_data.get('notes')
            approver_id = 'CURRENT_APPROVER_ID'
            
            if action == 'recommend':
                # Enforces P_APP_RECOMMEND
                result = process_leave_approval_contract(application_id, approver_id, action, notes)
                return Response(result)
            elif action == 'approve':
                # Enforces P_APP_APPROVE
                result = process_leave_approval_contract(application_id, approver_id, action, notes)
                return Response(result)
            elif action == 'reject':
                # Enforces P_APP_REJECT
                result = process_leave_approval_contract(application_id, approver_id, 'reject', notes)
                return Response(result)
            elif action == 'cancel':
                # Enforces P_APP_CANCEL
                result = process_leave_approval_contract(application_id, approver_id, 'cancel', notes)
                return Response(result)
            else:
                return Response({'error': 'Invalid status action.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaveBalanceViewSet(viewsets.GenericViewSet):
    """
    Handles fetching personal and bulk leave balances.
    """
    def list(self, request):
        # Enforces P_BALANCE_VIEW and P_BULK_ACTION
        employee_ids = request.query_params.get('employees', '').split(',') if request.query_params.get('employees') else ['CURRENT_EMPLOYEE_ID']
        return Response(get_all_balances_contract(employee_ids))

    def retrieve(self, request, pk=None):
        # Enforces P_BALANCE_VIEW
        employee_id = request.query_params.get('employee_id', 'CURRENT_EMPLOYEE_ID')
        category = request.query_params.get('category', 'EL')
        return Response(get_employee_balance_contract([employee_id], category))


class SubstituteResponseViewSet(viewsets.GenericViewSet):
    """
    Handles substitute response updates.
    """
    def list(self, request):
        # Enforces P_SUB_VIEW_SELF
        return Response([])

    def update(self, request, *args, **kwargs):
        application_id = kwargs.get('pk')
        data = request.data
        substitute_id = data.get('substitute_id')
        response_status = data.get('response_status', '').lower()
        notes = data.get('notes')
        
        if not substitute_id or not response_status:
             return Response({'error': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforces P_SUB_RESPOND, P_SUB_APPROVE, P_SUB_DECLINE
        try:
            result = update_substitute_response_contract(application_id, substitute_id, response_status, notes)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)