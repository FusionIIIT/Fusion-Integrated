# modules/hr_eis/serializers.py
from rest_framework import serializers
from .models import EmployeeProfile, WorkExperience


class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['id', 'organization', 'position', 'start_date', 'end_date', 'description']

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if end and start and end < start:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return data


class EmployeeProfileSerializer(serializers.ModelSerializer):
    experiences = WorkExperienceSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ['id', 'username', 'pf_number', 'designation', 'department', 'date_of_joining', 'about_me', 'experiences']