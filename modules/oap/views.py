from rest_framework import viewsets, decorators, response, status
from modules.oap.models import StudentLeaveRequest, BonafideRequest, NoDuesClearance, NoDuesItem, PGAssistantshipClaim, GraduateSeminar
from modules.oap.serializers import StudentLeaveRequestSerializer, BonafideRequestSerializer, NoDuesClearanceSerializer, NoDuesItemSerializer, PGAssistantshipClaimSerializer, GraduateSeminarSerializer

class StudentLeaveViewSet(viewsets.ModelViewSet):
    queryset = StudentLeaveRequest.objects.all()
    serializer_class = StudentLeaveRequestSerializer

    @decorators.action(detail=True, methods=['POST'])
    def hod_approve(self, request, pk):
        student_leave_request = self.get_object()
        student_leave_request.hod_approve()
        serializer = StudentLeaveRequestSerializer(student_leave_request)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class BonafideViewSet(viewsets.ModelViewSet):
    queryset = BonafideRequest.objects.all()
    serializer_class = BonafideRequestSerializer

    @decorators.action(detail=True, methods=['POST'])
    def approve_and_issue(self, request, pk):
        bonafide_request = self.get_object()
        bonafide_request.approve_and_issue()
        serializer = BonafideRequestSerializer(bonafide_request)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class NoDuesViewSet(viewsets.ModelViewSet):
    queryset = NoDuesClearance.objects.all()
    serializer_class = NoDuesClearanceSerializer



    @decorators.action(detail=True, methods=['POST'])
    def initiate(self, request, pk):
        no_dues_clearance = self.get_object()
        no_dues_clearance.initiate()
        serializer = NoDuesClearanceSerializer(no_dues_clearance)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['POST'])
    def finalize_clearance(self, request, pk):
        no_dues_clearance = self.get_object()
        no_dues_clearance.finalize_clearance()
        serializer = NoDuesClearanceSerializer(no_dues_clearance)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class NoDuesItemViewSet(viewsets.ModelViewSet):
    queryset = NoDuesItem.objects.all()
    serializer_class = NoDuesItemSerializer

    def update_clearance_status(self, request, pk):
        no_dues_item = self.get_object()
        no_dues_item.update_clearance_status()
        serializer = NoDuesItemSerializer(no_dues_item)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class PGAssistantshipViewSet(viewsets.ModelViewSet):
    queryset = PGAssistantshipClaim.objects.all()
    serializer_class = PGAssistantshipClaimSerializer

    @decorators.action(detail=True, methods=['POST'])
    def claim_submission(self, request, pk):
        pg_assistantship_claim = self.get_object()
        pg_assistantship_claim.claim_submission()
        serializer = PGAssistantshipClaimSerializer(pg_assistantship_claim)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['POST'])
    def verify_supervisor(self, request, pk):
        pg_assistantship_claim = self.get_object()
        pg_assistantship_claim.verify_supervisor()
        serializer = PGAssistantshipClaimSerializer(pg_assistantship_claim)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['POST'])
    def forward_dept_admin(self, request, pk):
        pg_assistantship_claim = self.get_object()
        pg_assistantship_claim.forward_dept_admin()
        serializer = PGAssistantshipClaimSerializer(pg_assistantship_claim)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['POST'])
    def hod_approve(self, request, pk):
        pg_assistantship_claim = self.get_object()
        pg_assistantship_claim.hod_approve()
        serializer = PGAssistantshipClaimSerializer(pg_assistantship_claim)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['POST'])
    def disburse_stipend(self, request, pk):
        pg_assistantship_claim = self.get_object()
        pg_assistantship_claim.disburse_stipend()
        serializer = PGAssistantshipClaimSerializer(pg_assistantship_claim)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class GraduateSeminarViewSet(viewsets.ModelViewSet):
    queryset = GraduateSeminar.objects.all()
    serializer_class = GraduateSeminarSerializer

    def list(self, request):
        queryset = GraduateSeminar.objects.all()
        serializer = GraduateSeminarSerializer(queryset, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = GraduateSeminarSerializer(data=request.data)
        if serializer.is_valid():
            seminar = serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=True, methods=['POST'])
    def schedule_slot(self, request, pk):
        seminar = self.get_object()
        seminar.schedule_slot(request.data)
        serializer = GraduateSeminarSerializer(seminar)
        return response.Response(serializer.data, status=status.HTTP_200_OK)