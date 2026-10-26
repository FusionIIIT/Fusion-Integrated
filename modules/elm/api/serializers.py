from rest_framework import serializers
from .models import LeaveRequest

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__'
