from rest_framework import serializers
from modules.oap.models import StudentLeaveRequest, BonafideRequest, NoDuesClearance, NoDuesItem, PGAssistantshipClaim, GraduateSeminar

class StudentLeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentLeaveRequest
        fields = '__all__'

class BonafideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonafideRequest
        fields = '__all__'

class NoDuesClearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesClearance
        fields = '__all__'

class NoDuesItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesItem
        fields = '__all__'

class PGAssistantshipClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGAssistantshipClaim
        fields = '__all__'

class GraduateSeminarSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraduateSeminar
        fields = '__all__'