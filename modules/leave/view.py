from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LeaveType, LeaveBalance, Leave
from .serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveSerializer


class LeaveTypeListView(generics.ListCreateAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]


class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user=self.request.user)


class LeaveListView(generics.ListCreateAPIView):
    serializer_class = LeaveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Leave.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        substitute = serializer.validated_data.get('substitute')
        # BR-EL-015: If substitute is assigned, require substitute response first
        initial_status = 'Awaiting_Substitute' if substitute else 'Awaiting_Unit_Head'
        serializer.save(user=self.request.user, status=initial_status)


class LeaveDetailView(generics.RetrieveAPIView):
    """
    BR-EL-034 Enforcement:
    Exposes ONLY Retrieve (GET). In-place modification (PUT/PATCH) is forbidden.
    """
    queryset = Leave.objects.all()
    serializer_class = LeaveSerializer
    permission_classes = [IsAuthenticated]


class WithdrawLeaveView(APIView):
    """
    EL-UC-007 / BR-EL-022: Immediate withdrawal of pending requests.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            leave = Leave.objects.get(pk=pk, user=request.user)
            if leave.status in ['Approved', 'Cancelled', 'Withdrawn', 'Rejected']:
                return Response(
                    {"error": "Cannot withdraw a finalized or approved request."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            leave.status = 'Withdrawn'
            leave.save()
            return Response({"message": "Leave application immediately withdrawn.", "status": leave.status})
        except Leave.DoesNotExist:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)


class SubstituteResponseView(APIView):
    """
    EL-UC-002 & EL-UC-019: Substitute Accept or Decline action.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        action = request.data.get('action')  # 'accept' or 'decline'
        try:
            leave = Leave.objects.get(pk=pk, substitute=request.user, status='Awaiting_Substitute')
            if action == 'accept':
                leave.substitute_accepted = True
                leave.status = 'Awaiting_Unit_Head'
                leave.save()
                return Response({"message": "Substitute assignment accepted. Advanced to Unit Head."})
            elif action == 'decline':
                leave.substitute_accepted = False
                leave.status = 'Action_Required'  # Recovery gate for EL-UC-019
                leave.save()
                return Response({"message": "Substitute assignment declined. Returned to applicant."})
            return Response({"error": "Invalid action. Choose 'accept' or 'decline'."}, status=status.HTTP_400_BAD_REQUEST)
        except Leave.DoesNotExist:
            return Response({"error": "Pending substitute request not found."}, status=status.HTTP_404_NOT_FOUND)


class UnitHeadReviewView(APIView):
    """
    EL-UC-003 / BR-EL-016 & BR-EL-017:
    Unit Head review endpoint for CL/RH final decision or higher-sanction recommendation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        decision = request.data.get('decision')  # 'approve', 'reject', 'recommend', 'not_recommend'
        try:
            leave = Leave.objects.get(pk=pk, status='Awaiting_Unit_Head')

            # BR-EL-016: Final decision for CL and RH
            if leave.leave_type.code in ['CL', 'RH']:
                if decision in ['approve', 'reject']:
                    leave.status = 'Approved' if decision == 'approve' else 'Rejected'
                    leave.save()
                    return Response({"message": f"Casual/Restricted leave {leave.status.lower()} by Unit Head."})
                return Response({"error": "CL/RH requires explicit Approve or Reject decision."}, status=status.HTTP_400_BAD_REQUEST)

            # BR-EL-017: Recommendation for higher-sanction categories (EL, COL, VL, SCL)
            if decision in ['recommend', 'not_recommend']:
                leave.unit_head_recommendation = 'Recommended' if decision == 'recommend' else 'Not Recommended'
                leave.status = 'Awaiting_Sanction'
                leave.save()
                return Response({"message": f"Leave marked {leave.unit_head_recommendation} and routed to Sanctioning Authority."})

            return Response({"error": "Higher-sanction leave requires Recommend or Not Recommend."}, status=status.HTTP_400_BAD_REQUEST)
        except Leave.DoesNotExist:
            return Response({"error": "Leave request awaiting Unit Head review not found."}, status=status.HTTP_404_NOT_FOUND)