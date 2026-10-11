from rest_framework import serializers
from ..models.leave import StationLeaveDetail, LeaveBalance, EmployeeLeave

class StationLeaveDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationLeaveDetail
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'

class EmployeeLeaveSerializer(serializers.ModelSerializer):
    station_leave = StationLeaveDetailSerializer(required=False)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = EmployeeLeave
        fields = '__all__'

    def create(self, validated_data):
        station_leave_data = validated_data.pop('station_leave', None)
        user = self.context['request'].user
        leave = EmployeeLeave.objects.create(applicant=user, **validated_data)
        if station_leave_data:
            StationLeaveDetail.objects.create(leave_application=leave, **station_leave_data)
        return leave