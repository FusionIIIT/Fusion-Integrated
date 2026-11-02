from rest_framework import serializers
from modules.oap import models

class LeaveSerializer(serializers.ModelSerializer):
    class Meta: model = models.LeaveApplication; fields = "__all__"; read_only_fields = ("student_user_id", "status", "decided_by_user_id", "decided_at", "created_at", "updated_at")
class BonafideSerializer(serializers.ModelSerializer):
    class Meta: model = models.BonafideRequest; fields = "__all__"; read_only_fields = ("student_user_id", "status", "decided_by_user_id", "decided_at", "created_at", "updated_at")
class NoDuesSerializer(serializers.ModelSerializer):
    clearances = serializers.StringRelatedField(many=True, read_only=True)
    class Meta: model = models.NoDuesRequest; fields = "__all__"; read_only_fields = ("student_user_id", "status", "finalized_by_user_id", "finalized_at", "created_at", "updated_at")
class ClaimSerializer(serializers.ModelSerializer):
    class Meta: model = models.AssistantshipClaim; fields = "__all__"; read_only_fields = ("student_user_id", "status", "thesis_supervisor_user_id", "ta_supervisor_user_id", "thesis_decision", "ta_decision")
class SeminarSerializer(serializers.ModelSerializer):
    class Meta: model = models.GraduateSeminar; fields = "__all__"; read_only_fields = ("student_user_id", "status", "scheduled_at", "scheduled_by_user_id", "created_at", "updated_at")
