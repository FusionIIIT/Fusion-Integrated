"""API views for Employee Leave Management."""

from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError

from fusion_auth.permissions import (
    HasModuleGrant,
    HasPermission,
    IsAuthenticatedPrincipal,
)
from modules.elm.models import LeaveApplication


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "leave_type",
            "start_date",
            "end_date",
            "requested_days",
            "reason",
            "status",
            "substitute_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        return attrs


class MyLeaveApplicationsView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            action_permission = HasPermission("elm.application.view_self")
        else:
            action_permission = HasPermission("elm.application.create")

        return [
            IsAuthenticatedPrincipal(),
            HasModuleGrant("elm"),
            action_permission(),
        ]

    def get_queryset(self):
        principal = self.request.principal
        return LeaveApplication.objects.filter(user_id=principal.user_id)

    def perform_create(self, serializer):
        principal = self.request.principal
        serializer.save(user_id=principal.user_id)