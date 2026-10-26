"""Wire shapes for ELM's endpoints."""
from rest_framework import serializers

from modules.elm.models import HierarchyRule, LeaveRequest, LeaveType

HALF = ["", "first", "second"]


class RequestOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["id", "applicant_id", "leave_type", "kind", "parent", "start_date",
                  "end_date", "half", "reason", "days", "status", "substitute_required",
                  "outside_station", "station_address", "station_contact",
                  "medical_evidence_ref", "created_at", "updated_at"]
        read_only_fields = fields


class DraftSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=HALF, required=False, allow_blank=True, default="")
    reason = serializers.CharField(max_length=2000)
    substitute_required = serializers.BooleanField(default=False)
    outside_station = serializers.BooleanField(default=False)
    station_address = serializers.CharField(required=False, allow_blank=True, default="",
                                            max_length=255)
    station_contact = serializers.CharField(required=False, allow_blank=True, default="",
                                            max_length=64)
    medical_evidence_ref = serializers.CharField(required=False, allow_blank=True, default="",
                                                 max_length=255)

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        if (not self.partial and attrs.get("outside_station")
                and not attrs.get("station_address")):
            raise serializers.ValidationError("station_address is required outside Jabalpur.")
        return attrs


class ModifySerializer(DraftSerializer):
    """Used with partial=True: only the fields sent are changed."""
    nominee_id = serializers.IntegerField(required=False, allow_null=True)


class SubmitSerializer(serializers.Serializer):
    nominee_id = serializers.IntegerField(required=False, allow_null=True)


class NominateSerializer(serializers.Serializer):
    nominee_id = serializers.IntegerField()


class ExtendSerializer(serializers.Serializer):
    new_end = serializers.DateField()
    nominee_id = serializers.IntegerField(required=False, allow_null=True)
    substitute_required = serializers.BooleanField(default=False)


class ResumeSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    details = serializers.CharField(required=False, allow_blank=True, default="")


class VerifySerializer(serializers.Serializer):
    verified = serializers.BooleanField(default=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class UnitHeadSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=["approved", "rejected", "recommended", "not_recommended"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class FinalSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class RemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class EmptySerializer(serializers.Serializer):
    pass


class PolicySerializer(serializers.Serializer):
    params = serializers.DictField(child=serializers.IntegerField(min_value=0))
    effective_from = serializers.DateField(required=False, allow_null=True, default=None)
    publish = serializers.BooleanField(default=True)


class CalendarDayInSerializer(serializers.Serializer):
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=["holiday", "rh", "vacation"])
    name = serializers.CharField(required=False, allow_blank=True, default="", max_length=120)


class CalendarSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    days = CalendarDayInSerializer(many=True)
    publish = serializers.BooleanField(default=True)

    def validate_days(self, days):
        seen = set()
        for d in days:
            key = (d["date"], d["kind"])
            if key in seen:
                raise serializers.ValidationError(f"Duplicate entry for {key[0]} ({key[1]}).")
            seen.add(key)
        return days


class HierarchySerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=HierarchyRule.Stage.choices)
    unit = serializers.CharField(required=False, allow_blank=True, default="", max_length=80)
    applicant_kind = serializers.ChoiceField(choices=["", "faculty", "staff"],
                                             required=False, allow_blank=True, default="")
    leave_type = serializers.ChoiceField(choices=LeaveType.choices, required=False,
                                         allow_blank=True, default="")
    approver_id = serializers.IntegerField()


class OfflineSerializer(serializers.Serializer):
    applicant_id = serializers.IntegerField()
    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=HALF, required=False, allow_blank=True, default="")
    reference = serializers.CharField(max_length=255)
    sanctioned_by = serializers.CharField(max_length=120)
    sanctioned_on = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
