"""IAA HTTP layer: module grant plus one permission per action, logic in services."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iaa import services
from modules.iaa.models import ExpenseRequest
from modules.iaa.serializers import DecisionSerializer, ExpenseRequestSerializer

MODULE = HasModuleGrant("iaa")


class _Scoped:
    serializer_class = ExpenseRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExpenseRequest.objects.none()
        return services.visible_requests(self.request.principal)


class RequestListCreateView(_Scoped, generics.ListCreateAPIView):
    """GET: requests visible to you. POST: IAA-UC-101 save a Draft."""

    def get_permissions(self):
        codes = (services.P_CREATE,) if self.request.method == "POST" \
            else services.ALL_PERMISSIONS
        return [MODULE(), HasPermission(*codes)()]

    def perform_create(self, serializer):
        serializer.instance = services.create_draft(
            self.request.principal, serializer.validated_data)


class RequestDetailView(_Scoped, generics.RetrieveUpdateAPIView):
    """GET one request; PATCH edits your own Draft (IAA-BR-104)."""

    http_method_names = ["get", "patch"]

    def get_permissions(self):
        codes = (services.P_CREATE,) if self.request.method == "PATCH" \
            else services.ALL_PERMISSIONS
        return [MODULE(), HasPermission(*codes)()]

    def get_object(self):
        return services.get_request(self.request.principal, self.kwargs["pk"])

    def perform_update(self, serializer):
        serializer.instance = services.update_draft(
            self.request.principal, self.kwargs["pk"], serializer.validated_data)


class _ActionView(_Scoped, generics.GenericAPIView):
    permission_code = ""

    def get_permissions(self):
        return [MODULE(), HasPermission(self.permission_code)()]


class SubmitView(_ActionView):
    """IAA-UC-102 Submit Expense/Voucher Request."""

    permission_code = services.P_CREATE

    @extend_schema(request=None, responses=ExpenseRequestSerializer)
    def post(self, request, pk):
        return Response(self.get_serializer(services.submit(request.principal, pk)).data)


class ValidateView(_ActionView):
    """IAA-UC-103 Review & Validate Request (Finance)."""

    permission_code = services.P_VALIDATE

    @extend_schema(request=None, responses=ExpenseRequestSerializer)
    def post(self, request, pk):
        return Response(self.get_serializer(services.validate(request.principal, pk)).data)


class DecideView(_ActionView):
    """IAA-UC-201 Approve / Reject Request."""

    permission_code = services.P_DECIDE

    @extend_schema(request=DecisionSerializer, responses=ExpenseRequestSerializer)
    def post(self, request, pk):
        body = DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        req = services.decide(request.principal, pk, **body.validated_data)
        return Response(self.get_serializer(req).data)


class RecordView(_ActionView):
    """IAA-UC-105 Process & Record Approved Request."""

    permission_code = services.P_RECORD

    @extend_schema(request=None, responses=ExpenseRequestSerializer)
    def post(self, request, pk):
        return Response(self.get_serializer(services.record(request.principal, pk)).data)
