from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType, SubstituteNominee


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

class SubstituteNomineeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteNominee
        fields = '__all__'
