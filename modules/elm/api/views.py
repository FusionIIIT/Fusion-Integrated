from drf_spectacular.utils import OpenApiParameter, extend_schema
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication
from modules.elm.api.serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveApplicationSerializer, LeaveDecisionSerializer


@extend_schema(responses=LeaveTypeSerializer(many=True))
class LeaveTypeListView(APIView):
    permission_classes = [HasPermission("elm.leave_type.view")]

    def get(self, request):
        leave_types = LeaveType.objects.filter(is_active=True)
        serializer = LeaveTypeSerializer(leave_types, many=True)
        return Response(serializer.data)


@extend_schema(responses=LeaveBalanceSerializer(many=True))
class LeaveBalanceListView(APIView):
    permission_classes = [HasPermission("elm.balance.view")]

    def get(self, request):
        user_id = request.user.user_id
        balances = LeaveBalance.objects.filter(employee_id=user_id)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


@extend_schema(responses=LeaveApplicationSerializer(many=True))
class LeaveApplicationListView(APIView):
    permission_classes = [HasPermission("elm.application.view")]

    def get(self, request):
        user_id = request.user.user_id
        applications = LeaveApplication.objects.filter(applicant_id=user_id)
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


@extend_schema(request=LeaveApplicationSerializer, responses={201: LeaveApplicationSerializer})
class LeaveApplicationCreateView(APIView):
    permission_classes = [HasPermission("elm.application.create")]

    def post(self, request):
        user_id = request.user.user_id
        serializer = LeaveApplicationSerializer(data=request.data, context={"applicant_id": user_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(applicant_id=user_id, status="PENDING")
        return Response(serializer.data, status=201)


@extend_schema(request=None, parameters=[OpenApiParameter('pk', int, OpenApiParameter.PATH)], responses=LeaveApplicationSerializer)
class LeaveApplicationWithdrawView(APIView):
    permission_classes = [HasPermission("elm.application.delete")]

    def post(self, request, pk):
        user_id = request.user.user_id
        try:
            application = LeaveApplication.objects.get(pk=pk, applicant_id=user_id, status="PENDING")
        except LeaveApplication.DoesNotExist:
            raise BadRequestError("Application not found or not pending", code="application_not_found_or_pending")

        application.status = "WITHDRAWN"
        application.save()
        return Response(LeaveApplicationSerializer(application).data)


@extend_schema(request=LeaveDecisionSerializer, parameters=[OpenApiParameter('pk', int, OpenApiParameter.PATH)], responses=LeaveApplicationSerializer)
class LeaveApplicationDecideView(APIView):
    permission_classes = [HasPermission("elm.application.approve")]

    def post(self, request, pk):
        user_id = request.user.user_id
        application = LeaveApplication.objects.filter(pk=pk, applicant__elm_unit_head_link__unit_head_id=user_id).first()
        if not application:
            raise NotFound("Application not found or not authorized")

        decision = request.data.get("decision")
        if decision not in ["approve", "reject"]:
            raise BadRequestError("Decision must be approve or reject", code="invalid_decision")

        if application.status != "PENDING":
            raise BadRequestError("Only a pending application can be decided", code="not_pending")

        if application.leave_type_id not in ("CL", "RH"):
            raise BadRequestError("The Unit Head can finally decide only CL and RH", code="not_final_authority")

        application.status = "APPROVED" if decision == "approve" else "REJECTED"
        application.decided_by_id = user_id
        application.decided_at = timezone.now()  # Use the imported module
        application.save()

        return Response(LeaveApplicationSerializer(application).data)
