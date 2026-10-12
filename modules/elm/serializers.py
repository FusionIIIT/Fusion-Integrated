from rest_framework import serializers
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication, LeaveSubstitute, LeaveApproval

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = '__all__'

class LeaveSubstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSubstitute
        fields = '__all__'

class LeaveApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApproval
        fields = '__all__'
