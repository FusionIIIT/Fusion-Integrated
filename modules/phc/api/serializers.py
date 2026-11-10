from rest_framework import serializers
from modules.phc.models import PatientVisit, Prescription
from modules.phc.domain.inventory import RequisitionState

class PatientVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientVisit
        fields = [
            "id", "patient_user_id", "visited_on", "notes", "recorded_by_user_id"
        ]
        read_only_fields = ["id"]

class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = [
            "id", "patient_visit", "details", "issued_on"
        ]
        read_only_fields = ["id"]
