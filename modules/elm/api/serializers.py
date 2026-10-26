from rest_framework import serializers

from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = ["applicant", "status", "decided_at", "decided_by", "submitted_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        applicant_id = self.context["applicant_id"]

        # Rule 1: end_date must not be before start_date
        if end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must not be before start date."})

        # Rule 2: The leave type must be active
        leave_type = attrs["leave_type"]
        if not leave_type.is_active:
            raise serializers.ValidationError({"leave_type": "Leave type is not active."})

        # Rule 3: A new application must not overlap any existing application of the SAME applicant whose status is PENDING or APPROVED
        overlapping_applications = LeaveApplication.objects.filter(
            applicant_id=applicant_id,
            status__in=["PENDING", "APPROVED"],
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        if overlapping_applications.exists():
            raise serializers.ValidationError({"start_date": "Overlapping application found."})

        return attrs


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
