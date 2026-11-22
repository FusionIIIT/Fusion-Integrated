from decimal import Decimal

from rest_framework import serializers

from modules.phc.domain.schedules import weekly_range
from modules.phc.models import (
    AmbulanceUsage,
    Doctor,
    DoctorAttendance,
    DoctorScheduleSlot,
    HealthAdvisory,
    InventoryItem,
    InventoryMovement,
    InventoryRequisition,
    LowStockAlert,
    Notification,
    PatientVisit,
    Prescription,
    ReimbursementAction,
    ReimbursementClaim,
    RequisitionLine,
)


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "display_name", "specialization", "is_active"]
        read_only_fields = fields


class DoctorWriteSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=160)
    specialization = serializers.CharField(max_length=120)


class ScheduleSlotSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)

    class Meta:
        model = DoctorScheduleSlot
        fields = ["id", "doctor", "day_of_week", "starts_at", "ends_at",
                  "publication", "created_at", "updated_at"]
        read_only_fields = fields


class ScheduleAvailabilitySerializer(ScheduleSlotSerializer):
    attendance_status = serializers.CharField(read_only=True, allow_null=True,
                                             required=False)

    class Meta(ScheduleSlotSerializer.Meta):
        fields = [*ScheduleSlotSerializer.Meta.fields, "attendance_status"]
        read_only_fields = fields


class ScheduleSlotWriteSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(min_value=1, required=False)
    display_name = serializers.CharField(max_length=160, required=False)
    specialization = serializers.CharField(max_length=120, required=False)
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    starts_at = serializers.TimeField()
    ends_at = serializers.TimeField()

    def validate(self, attrs):
        if not attrs.get("doctor_id") and not (attrs.get("display_name") and
                                                attrs.get("specialization")):
            raise serializers.ValidationError(
                "Choose a doctor or enter a display name and specialization.")
        try:
            weekly_range(attrs["day_of_week"], attrs["starts_at"], attrs["ends_at"])
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class ScheduleSlotPatchSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6, required=False)
    starts_at = serializers.TimeField(required=False)
    ends_at = serializers.TimeField(required=False)

    def validate(self, attrs):
        if self.instance is None:
            return attrs
        day = attrs.get("day_of_week", self.instance.day_of_week)
        starts_at = attrs.get("starts_at", self.instance.starts_at)
        ends_at = attrs.get("ends_at", self.instance.ends_at)
        try:
            weekly_range(day, starts_at, ends_at)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    doctor = DoctorSerializer(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = DoctorAttendance
        fields = ["id", "doctor", "attendance_date", "status", "updated_at"]
        read_only_fields = fields


class AttendanceWriteSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=DoctorAttendance.Status.choices)


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "details", "issued_on", "issued_by_user_id", "created_at"]
        read_only_fields = fields


class PatientVisitSerializer(serializers.ModelSerializer):
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = PatientVisit
        fields = ["id", "patient_user_id", "visited_on", "notes",
                  "recorded_by_user_id", "prescriptions", "created_at"]
        read_only_fields = fields


class VisitWriteSerializer(serializers.Serializer):
    patient_user_id = serializers.IntegerField(min_value=1)
    visited_on = serializers.DateField()
    notes = serializers.CharField(trim_whitespace=True)
    prescription_details = serializers.CharField(trim_whitespace=True)
    issued_on = serializers.DateField()


class MedicalPdfRequestSerializer(serializers.Serializer):
    visit_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=50)

    def validate_visit_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Select each visit only once.")
        return value


class ReimbursementActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementAction
        fields = ["from_state", "to_state", "event", "actor_user_id", "created_at"]
        read_only_fields = fields


class ReimbursementSerializer(serializers.ModelSerializer):
    actions = ReimbursementActionSerializer(many=True, read_only=True)
    prescription_issued_on = serializers.DateField(source="prescription.issued_on",
                                                   read_only=True)
    prescription_details = serializers.CharField(source="prescription.details",
                                                 read_only=True)

    class Meta:
        model = ReimbursementClaim
        fields = ["id", "claimant_user_id", "prescription", "prescription_issued_on",
                  "prescription_details", "claim_amount", "expense_date",
                  "bill_reference", "remarks", "state", "submitted_at", "actions"]
        read_only_fields = fields


class ReimbursementWriteSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField(min_value=1)
    claim_amount = serializers.DecimalField(max_digits=12, decimal_places=2,
                                            min_value=Decimal("0.01"))
    expense_date = serializers.DateField()
    bill_reference = serializers.CharField(max_length=200, required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))


class InventoryItemSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ["id", "name", "unit", "reorder_threshold", "is_active",
                  "stock_quantity"]
        read_only_fields = ["id", "stock_quantity", "is_active"]


class InventoryItemWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    unit = serializers.CharField(max_length=40, default="units")
    reorder_threshold = serializers.IntegerField(min_value=1)


class StockAdjustmentSerializer(serializers.Serializer):
    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Enter a non-zero stock adjustment.")
        return value


class InventoryMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMovement
        fields = ["id", "item", "quantity_delta", "reason", "actor_user_id",
                  "created_at"]
        read_only_fields = fields


class LowStockAlertSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = LowStockAlert
        fields = ["id", "item", "item_name", "quantity_after",
                  "reorder_threshold", "created_at"]
        read_only_fields = fields


class RequisitionLineReadSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = RequisitionLine
        fields = ["item", "item_name", "unit", "quantity"]
        read_only_fields = fields


class RequisitionSerializer(serializers.ModelSerializer):
    lines = RequisitionLineReadSerializer(many=True, read_only=True)

    class Meta:
        model = InventoryRequisition
        fields = ["id", "originator_user_id", "state", "decided_by_user_id",
                  "fulfilled_by_user_id", "submitted_at", "lines"]
        read_only_fields = fields


class RequisitionLineWriteSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class RequisitionWriteSerializer(serializers.Serializer):
    lines = RequisitionLineWriteSerializer(many=True, allow_empty=False,
                                           max_length=50)


class AmbulanceUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceUsage
        fields = ["id", "used_at", "patient_name", "destination",
                  "recorded_by_user_id"]
        read_only_fields = fields


class AmbulanceUsageWriteSerializer(serializers.Serializer):
    used_at = serializers.DateTimeField()
    patient_name = serializers.CharField(max_length=160)
    destination = serializers.CharField(max_length=200)


class HealthAdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAdvisory
        fields = ["id", "title", "body", "published_at", "published_by_user_id"]
        read_only_fields = fields


class HealthAdvisoryWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    body = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "event_type", "message", "target_type", "target_id",
                  "created_at", "read_at"]
        read_only_fields = fields


class PatientSearchSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    kind = serializers.CharField()


class ReportSerializer(serializers.Serializer):
    report_type = serializers.CharField()
    data = serializers.JSONField()
