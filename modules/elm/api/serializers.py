"""Explicit serializers for the leave self-service API."""
from rest_framework import serializers

from ..models import LeaveApplication


class LeaveTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class LeaveTypeListSerializer(serializers.Serializer):
    results = LeaveTypeSerializer(many=True)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type_label = serializers.CharField(source="get_leave_type_display", read_only=True)
    days_requested = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "leave_type",
            "leave_type_label",
            "start_date",
            "end_date",
            "days_requested",
            "reason",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "leave_type_label", "days_requested", "status", "created_at", "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        # Avoid accepting a request that overlaps another active full-day
        # request. Half-day CL and holiday-calendar rules are deferred in this MVP.
        request = self.context.get("request")
        actor = getattr(request, "principal", None) if request else None
        if actor is not None and start_date and end_date and self.instance is None:
            active = LeaveApplication.objects.filter(
                user_id=actor.user_id,
                status__in=(LeaveApplication.Status.PENDING, LeaveApplication.Status.APPROVED),
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if active.exists():
                raise serializers.ValidationError({
                    "start_date": "This period overlaps a pending or approved leave request."
                })

        if "reason" in attrs and not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "Please provide a reason for leave."})
        return attrs
