from django.db.models import Q
from rest_framework import serializers

from ..models import LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "user",
            "status",
            "created_at",
            "updated_at",
        )

    def validate(self, data):
        start_date = data.get(
            "start_date",
            self.instance.start_date if self.instance else None,
        )
        end_date = data.get(
            "end_date",
            self.instance.end_date if self.instance else None,
        )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before start date."}
            )

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and start_date
            and end_date
        ):
            overlaps = LeaveRequest.objects.filter(
                user=user,
                status__in=("pending", "approved"),
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if self.instance is not None:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise serializers.ValidationError({
                    "start_date": (
                        "These dates overlap an existing pending or approved "
                        "leave request."
                    )
                })

        return data
