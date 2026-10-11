from rest_framework import serializers
from ..models.leave import LeaveTypeMaster, LeaveStatusMaster, UserLeaveQuota, LeaveApplication, StationOutstationInfo

class LeaveTypeMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTypeMaster
        fields = ['id', 'code', 'description']

class StationOutstationInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationOutstationInfo
        fields = ['id', 'source_city', 'target_destination', 'contact_number', 'residential_address']

class UserLeaveQuotaSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)

    class Meta:
        model = UserLeaveQuota
        fields = ['id', 'academic_session', 'leave_type', 'leave_type_code', 'total_credited', 'total_availed', 'current_balance']

class LeaveApplicationSerializer(serializers.ModelSerializer):
    outstation_detail = StationOutstationInfoSerializer(required=False)
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    status_label = serializers.CharField(source='status.status_code', read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'applicant', 'applicant_name', 'leave_type', 'start_date', 'end_date',
            'number_of_days', 'reason', 'status', 'status_label', 'approving_authority',
            'reviewer_comments', 'created_at', 'outstation_detail'
        ]
        read_only_fields = ['applicant', 'created_at']

    def create(self, validated_data):
        outstation_data = validated_data.pop('outstation_detail', None)
        request = self.context.get('request')
        user = request.user if request else validated_data.get('applicant')
        validated_data['applicant'] = user
        application = LeaveApplication.objects.create(**validated_data)
        if outstation_data:
            StationOutstationInfo.objects.create(application=application, **outstation_data)
        return application