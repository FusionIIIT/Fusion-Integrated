from rest_framework import serializers
from modules.leave_elm.models import LeaveHistory, LeaveNotification

class LeaveHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHistory
        fields = '__all__'

class LeaveNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = '__all__'