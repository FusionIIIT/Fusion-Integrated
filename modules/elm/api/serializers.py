from rest_framework import serializers

from modules.elm.domain.entities import HalfDay, LeaveCategory, LeaveStatus
from modules.elm.models import LeaveRequest, LeaveRequestTransition
from modules.elm.services import leaves as service


class LeaveHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestTransition
        fields = ["from_status", "to_status", "actor_user_id", "remarks", "at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Read shape. `allowed_transitions` is computed for the caller, so the UI
    shows only the buttons that would succeed."""

    allowed_transitions = serializers.SerializerMethodField()
    history = LeaveHistorySerializer(source="transitions", many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ["id", "applicant_user_id", "category", "start_date", "end_date", "half",
                  "days", "reason", "status", "is_station_leave", "station_address",
                  "station_contact", "created_at", "allowed_transitions", "history"]
        read_only_fields = fields

    def get_allowed_transitions(self, obj) -> list[str]:
        principal = self.context.get("principal")
        return service.allowed_targets(obj, principal) if principal else []


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[c.value for c in LeaveCategory])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=[h.value for h in HalfDay], required=False,
                                   allow_blank=True, default="")
    reason = serializers.CharField(max_length=2000)
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(max_length=300, required=False,
                                            allow_blank=True, default="")
    station_contact = serializers.CharField(max_length=30, required=False,
                                            allow_blank=True, default="")


class LeaveTransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(
        choices=[s.value for s in LeaveStatus if s != LeaveStatus.PENDING])
    remarks = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                    default="")


class LeaveBalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    credited = serializers.DecimalField(max_digits=5, decimal_places=1)
    availed = serializers.DecimalField(max_digits=5, decimal_places=1)
    reserved = serializers.DecimalField(max_digits=5, decimal_places=1)
    available = serializers.DecimalField(max_digits=5, decimal_places=1)
