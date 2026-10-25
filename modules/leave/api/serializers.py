from rest_framework import serializers

from modules.leave.models import LeaveBalance, LeaveRequest, LeaveResumption, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "max_days_per_year",
            "requires_attachment",
            "is_active",
            "carry_forward",
            "continuous_count",
            "allow_half_day",
            "requires_rh_calendar",
            "requires_vacation_period",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining_days = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "year",
            "allocated_days",
            "used_days",
            "remaining_days",
        ]
        read_only_fields = ["id", "user_id", "remaining_days"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "half_day",
            "duration_days",
            "reason",
            "status",
            "substitute_user_id",
            "substitute_status",
            "unit_head_recommendation",
            "current_stage",
            "approver_user_id",
            "rejection_reason",
            "approved_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "duration_days",
            "status",
            "approver_user_id",
            "approved_at",
            "created_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        leave_type = attrs.get("leave_type")
        half_day = attrs.get("half_day", "none")

        # Half-day only where the category allows it (CL).
        if leave_type is not None and half_day != "none" and not leave_type.allow_half_day:
            raise serializers.ValidationError(
                {"half_day": "half-day is not allowed for this leave type"}
            )

        # RH applicability: requested start date must be a published RH.
        if leave_type is not None and getattr(leave_type, "requires_rh_calendar", False):
            from modules.leave.models import RestrictedHoliday

            if not RestrictedHoliday.objects.filter(
                year=start.year if start else None, date=start, is_published=True
            ).exists():
                raise serializers.ValidationError(
                    {"start_date": "start date must be an applicable restricted holiday"}
                )

        # Impermissible overlap with the applicant's own pending/approved requests.
        request = self.context.get("request")
        if request is not None and start and end:
            user_id = getattr(request, "principal", None)
            user_id = getattr(user_id, "user_id", None) if user_id else None
            if user_id is not None:
                overlap = LeaveRequest.objects.filter(
                    user_id=user_id,
                    status__in=["pending", "approved"],
                    start_date__lte=end,
                    end_date__gte=start,
                )
                if self.instance is not None:
                    overlap = overlap.exclude(pk=self.instance.pk)
                if overlap.exists():
                    raise serializers.ValidationError(
                        {"detail": "dates overlap an existing pending/approved request"}
                    )
        return attrs


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True)


class SubstituteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveResumption
        fields = [
            "id",
            "leave_request",
            "actual_resumption_date",
            "details",
            "status",
            "reviewed_by_user_id",
            "adjustment_days",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "leave_request",
            "status",
            "reviewed_by_user_id",
            "adjustment_days",
            "reviewed_at",
            "created_at",
        ]


class SubstituteNominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["recommend", "not_recommend"])
