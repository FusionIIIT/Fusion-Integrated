from rest_framework import serializers

from modules.vms.models import VisitRequest, Zone

ID_DOC_TYPES = ["passport", "aadhaar", "driving_licence", "voter_id"]


class PreRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    id_doc_type = serializers.ChoiceField(choices=ID_DOC_TYPES)
    id_doc_number = serializers.CharField(max_length=60)
    host_user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    requested_zones = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Zone.objects.all())

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError("scheduled_end must follow scheduled_start.")
        return attrs


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name")
    requested_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitRequest
        fields = ["id", "visitor_name", "host_user_id", "purpose", "scheduled_start",
                  "scheduled_end", "status", "requested_zones", "decision_note",
                  "decided_at", "created_at"]
