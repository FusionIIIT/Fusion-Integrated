"""Authenticated ELM request APIs; every employee query is applicant-scoped."""

from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import LeaveRequest
from modules.elm.selectors import requests_for_applicant
from modules.elm.services.submission import submit_leave_request
from modules.elm.services.workflow import (
    decide_leave_request,
    nominate_replacement_substitute,
    respond_to_substitute_assignment,
    withdraw_leave_request,
)

MODULE = HasModuleGrant("elm")
P_CREATE = "elm.request.create"
P_VIEW_SELF = "elm.request.view_self"
P_WITHDRAW = "elm.request.withdraw"


class ELMDataView(APIView):
    """The original authenticated metadata endpoint."""

    @extend_schema(responses=s.ELMMetadataSerializer)
    def get(self, request):
        return Response(
            {
                "label": "elm",
                "description": "ELM module metadata",
                "version": "1.0.0",
            },
            status=status.HTTP_200_OK,
        )


class RequestListCreateView(generics.ListCreateAPIView):
    serializer_class = s.LeaveRequestSerializer
    queryset = LeaveRequest.objects.none()

    def get_permissions(self):
        permission = P_CREATE if self.request.method == "POST" else P_VIEW_SELF
        return [MODULE(), HasPermission(permission)()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.LeaveRequestSubmissionSerializer
        return s.LeaveRequestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        queryset = requests_for_applicant(self.request.principal)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            valid_statuses = {value for value, _ in LeaveRequest.Status.choices}
            if status_filter not in valid_statuses:
                raise BadRequestError(
                    "Unsupported request status filter.", code="invalid_status_filter"
                )
            queryset = queryset.filter(status=status_filter)

        category = self.request.query_params.get("leave_type")
        if category:
            valid_categories = {value for value, _ in LeaveRequest.LeaveType.choices}
            if category not in valid_categories:
                raise BadRequestError(
                    "Unsupported leave category filter.",
                    code="invalid_category_filter",
                )
            queryset = queryset.filter(leave_type=category)

        from_raw = self.request.query_params.get("from_date")
        to_raw = self.request.query_params.get("to_date")
        from_date = parse_date(from_raw) if from_raw else None
        to_date = parse_date(to_raw) if to_raw else None
        if from_raw and from_date is None:
            raise BadRequestError("from_date must use YYYY-MM-DD.", code="invalid_date_filter")
        if to_raw and to_date is None:
            raise BadRequestError("to_date must use YYYY-MM-DD.", code="invalid_date_filter")
        if from_date and to_date and from_date > to_date:
            raise BadRequestError(
                "from_date must not be after to_date.", code="reversed_date_filter"
            )
        if from_date:
            queryset = queryset.filter(end_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(start_date__lte=to_date)
        return queryset.order_by("-id")

    @extend_schema(
        request=s.LeaveRequestSubmissionSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = submit_leave_request(actor=request.principal, **serializer.validated_data)
        return Response(
            s.LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class RequestHistoryView(RequestListCreateView):
    """Read-only history alias with the same ownership and filter rules."""

    http_method_names = ["get", "head", "options"]


class RequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveRequestSerializer)
    def get(self, request, pk):
        leave_request = requests_for_applicant(request.principal).filter(pk=pk).first()
        if leave_request is None:
            raise NotFoundError("No leave request was found.")
        return Response(s.LeaveRequestSerializer(leave_request).data)


class RequestWithdrawalView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(
        request=s.LeaveWithdrawalSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.LeaveWithdrawalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = withdraw_leave_request(
            request_id=pk, actor=request.principal, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)


class RequestDecisionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.LeaveDecisionSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.LeaveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = decide_leave_request(
            request_id=pk, actor=request.principal, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.SubstituteResponseSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = respond_to_substitute_assignment(
            request_id=pk, actor=request.principal, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)


class SubstituteNominationView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(
        request=s.SubstituteNominationSerializer,
        responses=s.LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = s.SubstituteNominationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = nominate_replacement_substitute(
            request_id=pk, actor=request.principal, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)
