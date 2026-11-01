from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.api.serializers import (
    ArchivalDecisionSerializer,
    ArchivalRequestCreateSerializer,
    ArchivalRequestSerializer,
)
from modules.badms.models import ArchivalRequest
from modules.directory import contracts as directory

MODULE = HasModuleGrant("badms")
P_SUBMIT = "badms.archival.submit"
P_REVIEW = "badms.archival.review"


def _department(principal):
    user = directory.get_users([principal.user_id]).get(principal.user_id)
    if not user or not user.department.strip():
        raise PermissionDeniedError(
            "Your department could not be confirmed in the institute directory.")
    return user.department.strip()


class ArchivalRequestListCreateView(APIView):
    def get_permissions(self):
        permission = HasPermission(P_SUBMIT, P_REVIEW)
        if self.request.method == "POST":
            permission = HasPermission(P_SUBMIT)
        return [MODULE(), permission()]

    @extend_schema(responses=ArchivalRequestSerializer(many=True))
    def get(self, request):
        principal = request.principal
        requests = ArchivalRequest.objects.all()
        if principal.has_permission(P_REVIEW):
            requests = requests.filter(department=_department(principal))
        else:
            requests = requests.filter(requester_user_id=principal.user_id)
        requests = requests.order_by("-created_at")
        return Response(ArchivalRequestSerializer(requests, many=True).data)

    @extend_schema(
        request=ArchivalRequestCreateSerializer,
        responses={status.HTTP_201_CREATED: ArchivalRequestSerializer},
    )
    def post(self, request):
        serializer = ArchivalRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        archival_request = ArchivalRequest.objects.create(
            requester_user_id=request.principal.user_id,
            department=_department(request.principal),
            **serializer.validated_data,
        )
        return Response(
            ArchivalRequestSerializer(archival_request).data,
            status=status.HTTP_201_CREATED,
        )


class ArchivalDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(
        request=ArchivalDecisionSerializer,
        responses=ArchivalRequestSerializer,
    )
    def post(self, request, pk):
        serializer = ArchivalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            archival_request = get_object_or_404(
                ArchivalRequest.objects.select_for_update().filter(
                    department=_department(request.principal)),
                pk=pk,
            )
            if archival_request.status != "submitted":
                raise ConflictError("This request has already been decided.")

            approved = serializer.validated_data["decision"] == "approve"
            archival_request.status = "hod_approved" if approved else "rejected"
            archival_request.decided_by_user_id = request.principal.user_id
            archival_request.decided_at = timezone.now()
            archival_request.decision_note = serializer.validated_data.get("note", "")
            archival_request.save(update_fields=(
                "status", "decided_by_user_id", "decided_at", "decision_note",
                "updated_at",
            ))
        return Response(ArchivalRequestSerializer(archival_request).data)
