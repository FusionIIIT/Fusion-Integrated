"""HTTP views for Employee Leave Management.

Adheres strictly to the two-gate access pattern:
1. HasModuleGrant('elm') — coarse gate
2. HasPermission(...)   — fine action gate
"""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationCreateSerializer,
    LeaveApplicationReviewSerializer,
    LeaveApplicationSerializer,
)
from modules.elm.models import LeaveApplication
from modules.elm.selectors import leave as selectors
from modules.elm.services import leave as services

MODULE = HasModuleGrant("elm")


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    """List leave applications visible to the user, or submit a new application."""

    queryset = LeaveApplication.objects.none()
    serializer_class = LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("elm.leave_application.apply")()]
        return [
            MODULE(),
            HasPermission(
                "elm.leave_application.view_self",
                "elm.leave_application.manage",
            )(),
        ]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        status_param = self.request.query_params.get("status")
        category_param = self.request.query_params.get("category")
        return selectors.visible_leave_applications(
            getattr(self.request, "principal", None),
            status=status_param,
            category=category_param,
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer

    @extend_schema(
        summary="List visible leave applications",
        tags=["elm"],
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by status",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="category",
                description="Filter by category",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Submit a new leave application",
        tags=["elm"],
        request=LeaveApplicationCreateSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        app = services.apply_leave(
            principal=request.principal,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
        )
        return Response(
            LeaveApplicationSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    """Retrieve details of a single leave application."""

    queryset = LeaveApplication.objects.none()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [
        MODULE,
        HasPermission(
            "elm.leave_application.view_self",
            "elm.leave_application.manage",
        ),
    ]

    def get_object(self):
        if getattr(self, "swagger_fake_view", False):
            return None
        return selectors.get_leave_application(
            getattr(self.request, "principal", None),
            self.kwargs["pk"],
        )

    @extend_schema(
        summary="Get details of a leave application",
        tags=["elm"],
        responses={200: LeaveApplicationSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class LeaveApplicationReviewView(APIView):
    """Approve or reject a leave application. Restricted to managers/HR."""

    serializer_class = LeaveApplicationReviewSerializer
    permission_classes = [MODULE, HasPermission("elm.leave_application.manage")]

    @extend_schema(
        summary="Review (approve or reject) a leave application",
        tags=["elm"],
        request=LeaveApplicationReviewSerializer,
        responses={200: LeaveApplicationSerializer},
    )
    def post(self, request, pk: int):
        serializer = LeaveApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        app = services.review_leave(
            principal=request.principal,
            application_id=pk,
            action=data["action"],
            remarks=data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class LeaveApplicationCancelView(APIView):
    """Cancel a pending leave application."""

    serializer_class = LeaveApplicationSerializer
    permission_classes = [
        MODULE,
        HasPermission(
            "elm.leave_application.apply",
            "elm.leave_application.view_self",
        ),
    ]

    @extend_schema(
        summary="Cancel a pending leave application",
        tags=["elm"],
        responses={200: LeaveApplicationSerializer},
    )
    def post(self, request, pk: int):
        app = services.cancel_leave(
            principal=request.principal,
            application_id=pk,
        )
        return Response(LeaveApplicationSerializer(app).data)
