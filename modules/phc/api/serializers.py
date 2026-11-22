"""PHC API serializers."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from modules.phc.models import (
    AmbulanceLog,
    DoctorAttendance,
    DoctorSchedule,
    HealthAnnouncement,
    InventoryItem,
    PatientVisit,
    PhcNotification,
    Prescription,
    ProcurementRequisition,
    ReimbursementAudit,
    ReimbursementClaim,
    ReimbursementConfig,
    RequisitionLineItem,
)

# ---------------------------------------------------------------------------
# Schedule & Attendance
# ---------------------------------------------------------------------------


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor_name",
            "specialisation",
            "day_of_week",
            "start_time",
            "end_time",
            "room",
            "is_published",
            "created_at",
        ]
        read_only_fields = ["id", "is_published", "created_at"]


class DoctorAttendanceSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="schedule.doctor_name", read_only=True)
    day_of_week = serializers.CharField(source="schedule.day_of_week", read_only=True)
    start_time = serializers.TimeField(source="schedule.start_time", read_only=True)

    class Meta:
        model = DoctorAttendance
        fields = [
            "id",
            "schedule",
            "doctor_name",
            "day_of_week",
            "start_time",
            "date",
            "status",
            "marked_by_user_id",
        ]
        read_only_fields = ["id", "marked_by_user_id"]


class MarkAttendanceSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["available", "departed"])
    date = serializers.DateField(required=False)


# ---------------------------------------------------------------------------
# Patient Records
# ---------------------------------------------------------------------------


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = [
            "id",
            "visit",
            "medicine_name",
            "dosage",
            "duration_days",
            "instructions",
            "expense_date",
            "prescribed_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "prescribed_by_user_id", "created_at"]


class PatientVisitSerializer(serializers.ModelSerializer):
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = PatientVisit
        fields = [
            "id",
            "user_id",
            "visit_date",
            "chief_complaint",
            "diagnosis",
            "notes",
            "recorded_by_user_id",
            "created_at",
            "prescriptions",
        ]
        read_only_fields = ["id", "user_id", "recorded_by_user_id", "created_at"]


class CreateVisitSerializer(serializers.Serializer):
    patient_user_id = serializers.IntegerField()
    visit_date = serializers.DateField()
    chief_complaint = serializers.CharField()
    diagnosis = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AddPrescriptionSerializer(serializers.Serializer):
    medicine_name = serializers.CharField()
    dosage = serializers.CharField()
    duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    expense_date = serializers.DateField(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Reimbursement
# ---------------------------------------------------------------------------


class ReimbursementAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementAudit
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_role",
            "notes",
            "at",
        ]


class ReimbursementClaimSerializer(serializers.ModelSerializer):
    audit_entries = ReimbursementAuditSerializer(many=True, read_only=True)
    prescription_detail = PrescriptionSerializer(source="prescription", read_only=True)

    class Meta:
        model = ReimbursementClaim
        fields = [
            "id",
            "user_id",
            "prescription",
            "prescription_detail",
            "amount_claimed",
            "description",
            "status",
            "submitted_at",
            "audit_entries",
        ]
        read_only_fields = ["id", "user_id", "status", "submitted_at"]


class SubmitClaimSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField()
    amount_claimed = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")


class ClaimDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReimbursementConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementConfig
        fields = ["submission_window_days", "updated_at"]
        read_only_fields = ["updated_at"]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "unit",
            "stock_quantity",
            "reorder_threshold",
            "description",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_low_stock"]


class AdjustStockSerializer(serializers.Serializer):
    delta = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Procurement Requisitions
# ---------------------------------------------------------------------------


class RequisitionLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisitionLineItem
        fields = ["id", "item_name", "quantity", "unit", "notes"]


class ProcurementRequisitionSerializer(serializers.ModelSerializer):
    line_items = RequisitionLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProcurementRequisition
        fields = [
            "id",
            "title",
            "justification",
            "status",
            "submitted_by_user_id",
            "decided_by_user_id",
            "decision_notes",
            "decided_at",
            "fulfilled_at",
            "created_at",
            "updated_at",
            "line_items",
        ]
        read_only_fields = [
            "id",
            "status",
            "submitted_by_user_id",
            "decided_by_user_id",
            "decision_notes",
            "decided_at",
            "fulfilled_at",
            "created_at",
            "updated_at",
        ]


class CreateRequisitionSerializer(serializers.Serializer):
    title = serializers.CharField()
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    line_items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of {item_name, quantity, unit?, notes?}",
    )

    def validate_line_items(self, value):
        for li in value:
            if "item_name" not in li or not li["item_name"]:
                raise serializers.ValidationError("Each line item must have an item_name.")
            if "quantity" not in li:
                raise serializers.ValidationError("Each line item must have a quantity.")
        return value


class RequisitionDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Ambulance
# ---------------------------------------------------------------------------


class AmbulanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceLog
        fields = [
            "id",
            "patient_name",
            "destination",
            "usage_at",
            "notes",
            "recorded_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "recorded_by_user_id", "created_at"]


class CreateAmbulanceLogSerializer(serializers.Serializer):
    patient_name = serializers.CharField()
    destination = serializers.CharField()
    usage_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


class HealthAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAnnouncement
        fields = [
            "id",
            "title",
            "body",
            "is_published",
            "published_by_user_id",
            "published_at",
        ]
        read_only_fields = ["id", "is_published", "published_by_user_id", "published_at"]


class PublishAnnouncementSerializer(serializers.Serializer):
    title = serializers.CharField()
    body = serializers.CharField()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class PhcNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhcNotification
        fields = [
            "id",
            "event_type",
            "subject",
            "body",
            "delivered",
            "delivered_at",
            "created_at",
        ]
