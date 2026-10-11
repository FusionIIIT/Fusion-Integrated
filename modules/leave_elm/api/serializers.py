from rest_framework import serializers

class LeaveTypeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=255, required=False)

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['employee', 'leave_type', 'balance']

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            'id',
            'employee',
            'leave_type',
            'start_date',
            'end_date',
            'status',
            'created_at'
        ]

class LeaveActionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    application = serializers.PrimaryKeyRelatedField(queryset=LeaveApplication.objects.all())
    action_taken = serializers.CharField(max_length=100)
    approved_by = serializers.CharField(max_length=255, required=False)
    approved_at = serializers.DateTimeField(required=False)