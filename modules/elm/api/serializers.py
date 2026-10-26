from rest_framework import serializers

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType, SubstituteResponse


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name']

class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())
    status = serializers.CharField(read_only=True, default='pending')

    class Meta:
        model = LeaveRequest
        fields = ['id', 'leave_type', 'user_id', 'start_date', 'end_date', 'reason', 'status']

    def create(self, validated_data):
        validated_data['status'] = 'pending'
        validated_data['user_id'] = self.context['request'].user.id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.user_id != self.context['request'].user.id:
            raise serializers.ValidationError(
                "You do not have permission to update this leave request."
            )
        return super().update(instance, validated_data)

    def validate_user_id(self, value):
        request = self.context.get("request")
        if request and value != request.user.id:
            raise serializers.ValidationError(
                "You cannot create a leave request for another user."
            )
        return value

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['id', 'leave_type', 'user_id', 'balance']

class SubstituteResponseSerializer(serializers.ModelSerializer):
    leave_request = serializers.PrimaryKeyRelatedField(queryset=LeaveRequest.objects.all())
    response = serializers.ChoiceField(choices=['accepted', 'rejected'])

    class Meta:
        model = SubstituteResponse
        fields = ['id', 'leave_request', 'substitute_user_id', 'response']

    def create(self, validated_data):
        leave_request = validated_data['leave_request']
        if leave_request.user_id != self.context['request'].user.id:
            raise serializers.ValidationError(
                "You do not have permission to create a substitute response for this leave request."
            )
        return super().create(validated_data)
