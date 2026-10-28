from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from modules.elm.models import CalendarVersion, LeavePolicy, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    parent_request_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "kind",
            "status",
            "start_date",
            "end_date",
            "half_day",
            "chargeable_days",
            "purpose",
            "station_leave",
            "station_leave_details",
            "substitute_user_id",
            "substitute_response",
            "medical_evidence_ref",
            "parent_request_id",
            "decision_reason",
            "submitted_at",
            "decided_at",
            "actual_resumption_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "kind",
            "status",
            "chargeable_days",
            "substitute_response",
            "parent_request_id",
            "decision_reason",
            "submitted_at",
            "decided_at",
            "created_at",
            "updated_at",
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=LeaveRequest._meta.get_field("half_day").choices, default="none"
    )
    purpose = serializers.CharField(max_length=4000)
    station_leave = serializers.BooleanField(default=False)
    station_leave_details = serializers.DictField(required=False, default=dict)
    substitute_user_id = serializers.IntegerField(required=False, min_value=1)
    medical_evidence_ref = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date cannot precede start date."})
        return attrs


@extend_schema_serializer(component_name="ELMTransition")
class TransitionSerializer(serializers.Serializer):
    target = serializers.CharField(max_length=32)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    recommendation = serializers.ChoiceField(
        choices=["recommended", "not_recommended"], required=False
    )


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"
        read_only_fields = [
            "id",
            "published_at",
            "published_by_user_id",
            "created_at",
            "updated_at",
        ]


class CalendarVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarVersion
        fields = "__all__"
        read_only_fields = [
            "id",
            "published_at",
            "published_by_user_id",
            "created_at",
            "updated_at",
        ]


class RelatedRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["cancellation", "extension", "resumption"])
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    actual_resumption_date = serializers.DateField(required=False)
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    substitute_user_id = serializers.IntegerField(required=False, min_value=1)
    medical_evidence_ref = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["kind"] == "extension" and (
            not attrs.get("start_date") or not attrs.get("end_date")
        ):
            raise serializers.ValidationError("Extensions require start_date and end_date.")
        if attrs["kind"] == "resumption" and not attrs.get("actual_resumption_date"):
            raise serializers.ValidationError({"actual_resumption_date": "This field is required."})
        return attrs


class LeaveRequestModifySerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["CL", "RH", "SCL", "EL", "COL", "VL"], required=False
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    half_day = serializers.ChoiceField(
        choices=LeaveRequest._meta.get_field("half_day").choices, required=False
    )
    purpose = serializers.CharField(max_length=4000, required=False)
    station_leave = serializers.BooleanField(required=False)
    station_leave_details = serializers.DictField(required=False)
    substitute_user_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    medical_evidence_ref = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field must be changed.")
        return attrs
