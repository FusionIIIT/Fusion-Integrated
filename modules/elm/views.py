
from rest_framework import generics

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from .models import LeaveRequest, LeaveBalance

from .serializers import LeaveRequestSerializer, LeaveBalanceSerializer

from .services import apply_for_leave

from .domain.state_machine import get_valid_transitions, LeaveStatus

from fusion_auth.permissions import HasModuleGrant, HasPermission





class MyLeavesView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated, HasModuleGrant("leave_management"),
HasPermission("leave_management.request.view_self")]



    def get_queryset(self):

        user_id = self.request.user.id

        return LeaveRequest.objects.filter(applicant_user_id=user_id)



    def get_serializer_class(self):

        return LeaveRequestSerializer



    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        leave_request = apply_for_leave(

            applicant_user_id=request.user.id,

            leave_type_id=serializer.validated_data['leave_type'].id,

            start_date=serializer.validated_data['start_date'],

            end_date=serializer.validated_data['end_date'],

            category=serializer.validated_data['leave_type'].category

        )

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)     





class SubstituteQueueView(generics.ListAPIView):

    permission_classes = [IsAuthenticated, HasModuleGrant("leave_management"),
HasPermission("leave_management.substitute.assign")]



    def get_queryset(self):

        user_id = self.request.user.id

        return SubstituteAssignment.objects.filter(substitute_user_id=user_id,
status=LeaveStatus.AWAITING_UNIT_HEAD.value)



    def get_serializer_class(self):

        return SubstituteAssignmentSerializer





class SubstituteRespondView(generics.UpdateAPIView):

    permission_classes = [IsAuthenticated, HasModuleGrant("leave_management"),
HasPermission("leave_management.substitute.assign")]



    def get_queryset(self):

        return SubstituteAssignment.objects.filter(substitute_user_id=self.request.user.id,
status=LeaveStatus.AWAITING_UNIT_HEAD.value)



    def get_serializer_class(self):

        return SubstituteAssignmentSerializer



    def perform_update(self, serializer):

        assignment = serializer.instance

        accept = serializer.validated_data.get('accept', False)

        if accept:

            assignment.status = LeaveStatus.AWAITING_UNIT_HEAD.value

        else:

            assignment.status = LeaveStatus.APPLICANT_ACTION_REQUIRED.value

        assignment.save()

        LeaveAuditTrail.objects.create(

            leave_request=assignment.leave_request,

            actor_user_id=self.request.user.id,

            from_status=LeaveStatus.AWAITING_SUBSTITUTE.value,

            to_status=assignment.status,

            action="Responded to substitute assignment",

            comments=f"Accept: {accept}"

        )                                                                                               
                                                                                                        




class UnitHeadApprovalsView(generics.ListAPIView):

    permission_classes = [IsAuthenticated, HasModuleGrant("leave_management"),
HasPermission("leave_management.unit_head.review")]



    def get_queryset(self):

        user_id = self.request.user.id

        return LeaveRequest.objects.filter(status=LeaveStatus.AWAITING_UNIT_HEAD.value)



    def get_serializer_class(self):

        return LeaveRequestSerializer
