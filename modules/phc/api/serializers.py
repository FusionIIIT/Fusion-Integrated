from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from modules.phc.models import DoctorSchedule, Prescription, Visit


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor_name",
            "specialization",
            "day_of_week",
            "start_time",
            "end_time",
            "published",
            "is_present",
        ]
        read_only_fields = ["id", "published", "is_present"]

    def validate(self, attrs):
        start_time = (
            attrs.get("start_time")
            if attrs.get("start_time") is not None
            else self.instance.start_time if self.instance else None
        )
        end_time = (
            attrs.get("end_time")
            if attrs.get("end_time") is not None
            else self.instance.end_time if self.instance else None
        )
        if start_time and end_time and end_time <= start_time:
            raise ValidationError(
                {"end_time": ["End time must be greater than start time."]}
            )
        return attrs


class PresenceSerializer(serializers.Serializer):
    is_present = serializers.BooleanField()


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = [
            "id",
            "medicine",
            "dosage",
            "duration_days",
            "notes",
        ]
        read_only_fields = ["id"]


class VisitSerializer(serializers.ModelSerializer):
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Visit
        fields = [
            "id",
            "patient_id",
            "schedule",
            "visit_date",
            "complaint",
            "diagnosis",
            "recorded_by",
            "prescriptions",
        ]
        read_only_fields = [
            "id",
            "patient_id",
            "schedule",
            "visit_date",
            "complaint",
            "diagnosis",
            "recorded_by",
        ]


class VisitCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(min_value=1)
    schedule = serializers.PrimaryKeyRelatedField(
        queryset=DoctorSchedule.objects.all(),
        allow_null=True,
        required=False,
    )
    visit_date = serializers.DateField()
    complaint = serializers.CharField()
    diagnosis = serializers.CharField(required=False, allow_blank=True, default="")
    prescriptions = PrescriptionSerializer(
        many=True, required=False, default=list
    )
