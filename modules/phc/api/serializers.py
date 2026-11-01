from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.phc.models import (
    Announcement,
    Appointment,
    Consultation,
    Doctor,
    DoctorSchedule,
    InventoryTransaction,
    Medicine,
    Patient,
)


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("id", "user_id", "patient_number", "created_at")
        read_only_fields = fields


class PatientCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ("id", "user_id", "specialty", "is_available")
        read_only_fields = ("id", "user_id", "specialty", "is_available")


class DoctorCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    specialty = serializers.CharField(max_length=100, required=False, allow_blank=True)


class DoctorUpdateSerializer(serializers.Serializer):
    specialty = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_available = serializers.BooleanField(required=False)


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = (
            "id",
            "doctor",
            "weekday",
            "starts_at",
            "ends_at",
            "slot_minutes",
            "effective_from",
            "effective_until",
            "is_active",
        )
        read_only_fields = ("id", "is_active")


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ("id", "patient", "doctor", "starts_at", "status", "reason", "created_at")
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AppointmentTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["confirmed", "completed", "cancelled", "rejected", "no_show"]
    )
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)


class ConsultationCreateSerializer(serializers.Serializer):
    symptoms = serializers.CharField(max_length=4000)
    observations = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    diagnosis = serializers.CharField(max_length=2000)
    treatment = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    medicines = serializers.ListField(child=serializers.DictField(), required=False)

    def validate_medicines(self, value):
        item_serializer = PrescribedMedicineInputSerializer(data=value, many=True)
        item_serializer.is_valid(raise_exception=True)
        return item_serializer.validated_data


class PrescribedMedicineInputSerializer(serializers.Serializer):
    medicine_name = serializers.CharField(max_length=150)
    dosage = serializers.CharField(max_length=100)
    frequency = serializers.CharField(max_length=100)
    duration = serializers.CharField(max_length=100)
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ConsultationSerializer(serializers.ModelSerializer):
    patient_user_id = serializers.IntegerField(source="appointment.patient.user_id", read_only=True)
    appointment_id = serializers.IntegerField(read_only=True)
    prescriptions = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.JSONField()))
    def get_prescriptions(self, obj):
        return [
            {
                "id": p.pk,
                "items": [
                    {
                        "medicine_name": item.medicine_name,
                        "dosage": item.dosage,
                        "frequency": item.frequency,
                        "duration": item.duration,
                        "instructions": item.instructions,
                    }
                    for item in p.items.all()
                ],
            }
            for p in obj.prescriptions.prefetch_related("items").all()
        ]

    class Meta:
        model = Consultation
        fields = (
            "id",
            "appointment_id",
            "patient_user_id",
            "symptoms",
            "observations",
            "diagnosis",
            "treatment",
            "finalized_at",
            "created_at",
            "prescriptions",
        )
        read_only_fields = fields


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = (
            "id",
            "name",
            "unit",
            "quantity",
            "low_stock_threshold",
            "expires_on",
            "is_active",
        )
        read_only_fields = ("id", "quantity")


class StockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=["addition", "dispense"])
    patient_id = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


class InventoryTransactionSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = (
            "id",
            "medicine",
            "medicine_name",
            "transaction_type",
            "quantity",
            "actor_user_id",
            "patient_id",
            "note",
            "created_at",
        )
        read_only_fields = fields


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        ref_name = "PhcAnnouncement"
        fields = ("id", "title", "body", "published", "created_at")
        read_only_fields = ("id", "published", "created_at")


class AnnouncementWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    body = serializers.CharField(max_length=3000)
