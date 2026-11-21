from rest_framework import serializers
from modules.phc.models import PatientVisit, Prescription

class PatientVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientVisit
        fields = ["id", "patient_user_id", "visited_on", "notes", "recorded_by_user_id"]
        read_only_fields = ["id", "recorded_by_user_id"]

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "patient_visit", "details", "issued_on"]
        read_only_fields = ["id", "issued_on"]

class PrescriptionCreateSerializer(serializers.Serializer):
    details = serializers.CharField(max_length=500)
