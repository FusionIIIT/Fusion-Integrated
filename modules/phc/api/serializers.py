"""PHC serializers — thin, explicit allow-lists. `fields = "__all__"` never used.
"""
from rest_framework import serializers

from modules.phc.models import (
    AmbulanceLog,
    AuditLog,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    StockAdjustment,
    Visit,
)


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = ("id", "doctor_name", "day_of_week", "start_time", "end_time",
                  "is_published", "published_at", "published_by",
                  "created_at", "updated_at")
        read_only_fields = ("published_at", "published_by", "created_at",
                            "updated_at")


class DoctorScheduleCreateSerializer(serializers.Serializer):
    doctor_name = serializers.CharField(max_length=120)
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


class DoctorScheduleMaintainSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6,
                                           required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)


class DoctorAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAttendance
        fields = ("id", "doctor_name", "date", "status", "updated_by",
                  "created_at", "updated_at")
        read_only_fields = ("updated_by", "created_at", "updated_at")


class DoctorAttendanceMarkSerializer(serializers.Serializer):
    doctor_name = serializers.CharField(max_length=120)
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=["available", "departed"])


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("user_id", "display_name", "kind")
        read_only_fields = fields


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ("id", "patient", "recorded_by", "notes", "visit_date")
        read_only_fields = ("recorded_by", "visit_date")


class VisitCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ("id", "visit", "patient", "medicine", "dosage",
                  "recorded_by", "created_at")
        read_only_fields = ("recorded_by", "created_at")


class PrescriptionCreateSerializer(serializers.Serializer):
    visit_id = serializers.IntegerField()
    patient_id = serializers.IntegerField()
    medicine = serializers.CharField(max_length=200)
    dosage = serializers.CharField(required=False, allow_blank=True)


class ReimbursementClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementClaim
        fields = ("claim_id", "employee", "prescription", "expense_date",
                  "amount", "description", "state", "stage_actor",
                  "action_history", "created_at", "updated_at")
        read_only_fields = ("claim_id", "state", "stage_actor",
                            "action_history", "created_at", "updated_at")


class ReimbursementClaimCreateSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField()
    expense_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)


class ClaimTransitionSerializer(serializers.Serializer):
    """Forward-stage transition used by review / verify / sanction / payment."""
    note = serializers.CharField(required=False, allow_blank=True)


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True)


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ("id", "name", "unit", "quantity", "reorder_threshold",
                  "created_at", "updated_at")
        read_only_fields = ("quantity", "created_at", "updated_at")


class InventoryItemCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    unit = serializers.CharField(required=False, allow_blank=True, default="units")
    reorder_threshold = serializers.IntegerField(required=False, default=0)


class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = ("id", "item", "quantity", "direction", "adjusted_by",
                  "reason", "created_at")
        read_only_fields = ("adjusted_by", "created_at")


class StockAdjustmentCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    direction = serializers.ChoiceField(choices=["add", "deduct"])
    reason = serializers.CharField(required=False, allow_blank=True)


class RequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisition
        fields = ("requisition_id", "originator", "decided_by", "decided_at",
                  "state", "decision_note", "created_at", "updated_at")
        read_only_fields = ("requisition_id", "decided_by", "decided_at",
                            "state", "decision_note", "created_at", "updated_at")


class RequisitionCreateSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(),
                                  allow_empty=False)


class RequisitionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True)


class RequisitionFulfillSerializer(serializers.Serializer):
    pass


class AmbulanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceLog
        fields = ("id", "timestamp", "patient_name", "destination",
                  "logged_by", "created_at")
        read_only_fields = ("logged_by", "created_at")


class AmbulanceLogCreateSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    patient_name = serializers.CharField(max_length=120)
    destination = serializers.CharField(max_length=200)


class HealthAdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAdvisory
        fields = ("id", "title", "content", "is_published", "published_at",
                  "published_by", "created_at", "updated_at")
        read_only_fields = ("published_at", "published_by", "created_at",
                            "updated_at")


class HealthAdvisoryCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    content = serializers.CharField()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ("id", "actor", "actor_role", "action", "target_type",
                  "target_id", "detail", "created_at")
        read_only_fields = fields
