from rest_framework import serializers
from modules.oap.models import (
    StudentLeave, BonafideRequest, NoDuesRequest, NoDuesAuthorityClearance,
    ThesisSupervisorAssignment, TAAssignment, AssistantshipClaim,
    GraduateSeminarRequest, OAPNotification
)

class StudentLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLeave
        fields = '__all__'

class BonafideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonafideRequest
        fields = '__all__'

class NoDuesAuthorityClearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesAuthorityClearance
        fields = '__all__'

class NoDuesRequestSerializer(serializers.ModelSerializer):
    clearances = NoDuesAuthorityClearanceSerializer(many=True, read_only=True)

    class Meta:
        model = NoDuesRequest
        fields = '__all__'

class ThesisSupervisorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisSupervisorAssignment
        fields = '__all__'

class TAAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAAssignment
        fields = '__all__'

class AssistantshipClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantshipClaim
        fields = '__all__'

class GraduateSeminarRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraduateSeminarRequest
        fields = '__all__'

class OAPNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAPNotification
        fields = '__all__'
