from rest_framework import serializers

from .models import LeaveCategory, LeaveApplication



class LeaveCategorySerializer(serializers.ModelSerializer):

    class Meta:

        model = LeaveCategory

        fields = '__all__'



class LeaveApplicationSerializer(serializers.ModelSerializer):

    class Meta:

        model = LeaveApplication

        fields = '__all__'
