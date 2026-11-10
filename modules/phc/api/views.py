from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from fusion_auth.permissions import HasPermission
from modules.phc.models import ReimbursementClaim, AuditEvent
from modules.phc.api.serializers import ReimbursementClaimSerializer, AuditEventSerializer

class ClaimListView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.create")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={201: ReimbursementClaimSerializer}
    )
    def post(self, request):
        serializer = ReimbursementClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data, status=201)

    @extend_schema(
        responses={200: ReimbursementClaimSerializer(many=True)}
    )
    def get(self, request):
        qs = ReimbursementClaim.objects.filter(claimant_user_id=request.user.user_id).order_by("-submitted_at")
        serializer = ReimbursementClaimSerializer(qs, many=True)
        return Response(serializer.data)

class ClaimDetailView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.view")]

    @extend_schema(
        responses={200: ReimbursementClaimSerializer}
    )
    def get(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk, claimant_user_id=request.user.user_id).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim)
        return Response(serializer.data)

class ClaimReviewListView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.review")]

    @extend_schema(
        responses={200: ReimbursementClaimSerializer(many=True)}
    )
    def get(self, request):
        qs = ReimbursementClaim.objects.filter(status="PENDING_PHC_REVIEW").order_by("-submitted_at")
        serializer = ReimbursementClaimSerializer(qs, many=True)
        return Response(serializer.data)

class ClaimReviewView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.review")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={200: ReimbursementClaimSerializer}
    )
    def post(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim, data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data)

class ClaimVerificationListView(APIView):
    permission_classes = [HasPermission("phc.reimbursement_audit.review")]

    @extend_schema(
        responses={200: ReimbursementClaimSerializer(many=True)}
    )
    def get(self, request):
        qs = ReimbursementClaim.objects.filter(status="PENDING_ACCOUNTS_VERIFICATION").order_by("-submitted_at")
        serializer = ReimbursementClaimSerializer(qs, many=True)
        return Response(serializer.data)

class ClaimVerificationView(APIView):
    permission_classes = [HasPermission("phc.reimbursement_audit.review")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={200: ReimbursementClaimSerializer}
    )
    def post(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim, data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data)

class ClaimSanctionListView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.approve")]

    @extend_schema(
        responses={200: ReimbursementClaimSerializer(many=True)}
    )
    def get(self, request):
        qs = ReimbursementClaim.objects.filter(status="PENDING_SANCTION").order_by("-submitted_at")
        serializer = ReimbursementClaimSerializer(qs, many=True)
        return Response(serializer.data)

class ClaimSanctionView(APIView):
    permission_classes = [HasPermission("phc.reimbursement.approve")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={200: ReimbursementClaimSerializer}
    )
    def post(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim, data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data)

class ClaimPaymentListView(APIView):
    permission_classes = [HasPermission("phc.reimbursement_payment.create")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={200: ReimbursementClaimSerializer}
    )
    def post(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim, data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data)

class ClaimPaymentView(APIView):
    permission_classes = [HasPermission("phc.reimbursement_payment.create")]

    @extend_schema(
        request=ReimbursementClaimSerializer,
        responses={200: ReimbursementClaimSerializer}
    )
    def post(self, request, pk):
        claim = ReimbursementClaim.objects.filter(id=pk).first()
        if not claim:
            raise NotFound("Claim not found")
        serializer = ReimbursementClaimSerializer(claim, data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(serializer.data)
