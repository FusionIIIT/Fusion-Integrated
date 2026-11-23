"""Request parsing and response shapes; every field listed, every server-owned field read-only."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from modules.phc.domain.reports import CATEGORIES
from modules.phc.domain.state_machine import (
    CLAIM_EVENTS,
    CLAIM_TRANSITIONS,
    REQUISITION_EVENTS,
    REQUISITION_TRANSITIONS,
    events_for,
)
from modules.phc.models import (
    AmbulanceLog,
    ClaimAction,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    LowStockAlert,
    Notification,
    PatientVisit,
    Prescription,
    ReimbursementClaim,
    Requisition,
    RequisitionLine,
    ScheduleSlot,
    StockAdjustment,
)


def _permissions(context) -> frozenset[str]:
    actor = context.get("actor")
    return getattr(actor, "permissions", frozenset())


# -- Schedules -------------------------------------------------------------------
class SlotSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = ScheduleSlot
        fields = ["day_of_week", "day_label", "start_time", "end_time"]


class ScheduleSerializer(serializers.ModelSerializer):
    slots = SlotSerializer(many=True, read_only=True)
    today_status = serializers.SerializerMethodField()

    class Meta:
        model = DoctorSchedule
        fields = ["id", "doctor_name", "specialization", "is_published", "published_at",
                  "slots", "today_status"]
        read_only_fields = fields

    def get_today_status(self, obj) -> str | None:
        rows = getattr(obj, "today_attendance", None) or []
        return rows[0].status if rows else None


class ScheduleWriteSerializer(serializers.Serializer):
    doctor_name = serializers.CharField(max_length=160)
    specialization = serializers.CharField(max_length=120, required=False, allow_blank=True,
                                           default="")
    slots = SlotSerializer(many=True)


class AttendanceWriteSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DoctorAttendance.Status.choices)


class AttendanceSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = DoctorAttendance
        fields = ["schedule", "attendance_date", "status"]
        read_only_fields = fields


# -- Records ---------------------------------------------------------------------
class PatientSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "medicine", "dosage", "duration_days", "instructions"]
        read_only_fields = ["id"]


class VisitSerializer(serializers.ModelSerializer):
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = PatientVisit
        fields = ["id", "patient_user_id", "visit_date", "complaint", "diagnosis",
                  "prescriptions", "created_at"]
        read_only_fields = fields


class VisitWriteSerializer(serializers.Serializer):
    patient_user_id = serializers.IntegerField(min_value=1)
    visit_date = serializers.DateField()
    complaint = serializers.CharField()
    diagnosis = serializers.CharField(required=False, allow_blank=True, default="")
    prescriptions = PrescriptionSerializer(many=True)


# -- Claims ----------------------------------------------------------------------
class ClaimActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimAction
        fields = ["event", "from_status", "to_status", "note", "created_at"]
        read_only_fields = fields


class ClaimSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    prescription_label = serializers.SerializerMethodField()
    actions = ClaimActionSerializer(many=True, read_only=True)
    allowed_events = serializers.SerializerMethodField()

    class Meta:
        model = ReimbursementClaim
        fields = ["id", "user_id", "prescription", "prescription_label", "expense_date",
                  "amount", "description", "status", "status_label", "submitted_at",
                  "actions", "allowed_events"]
        read_only_fields = fields

    def get_prescription_label(self, obj) -> str:
        p = obj.prescription
        return f"{p.medicine} ({p.visit.visit_date.isoformat()})"

    def get_allowed_events(self, obj) -> list[str]:
        actor = self.context.get("actor")
        if actor is not None and obj.user_id == getattr(actor, "user_id", None):
            return []
        return events_for(CLAIM_TRANSITIONS, obj.status, _permissions(self.context))


class ClaimWriteSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField(min_value=1)
    expense_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                        default="")


class ClaimTransitionSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=sorted(CLAIM_EVENTS))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class EligiblePrescriptionSerializer(serializers.ModelSerializer):
    visit_date = serializers.DateField(source="visit.visit_date", read_only=True)

    class Meta:
        model = Prescription
        fields = ["id", "medicine", "dosage", "visit_date"]
        read_only_fields = fields


# -- Inventory -------------------------------------------------------------------
class InventoryItemSerializer(serializers.ModelSerializer):
    is_low = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = ["id", "name", "unit", "stock_level", "reorder_threshold", "is_low"]
        read_only_fields = fields

    def get_is_low(self, obj) -> bool:
        return obj.stock_level < obj.reorder_threshold


class InventoryItemWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    unit = serializers.CharField(max_length=40)
    stock_level = serializers.DecimalField(max_digits=12, decimal_places=2,
                                           min_value=Decimal(0))
    reorder_threshold = serializers.DecimalField(max_digits=12, decimal_places=2,
                                                 min_value=Decimal(0))


class StockAdjustmentWriteSerializer(serializers.Serializer):
    delta = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class StockAdjustmentSerializer(serializers.ModelSerializer):
    low_stock_alert = serializers.SerializerMethodField()

    class Meta:
        model = StockAdjustment
        fields = ["id", "item", "delta", "level_after", "reason", "created_at",
                  "low_stock_alert"]
        read_only_fields = fields

    def get_low_stock_alert(self, obj) -> bool:
        return getattr(obj, "raised_low_stock_alert", False)


class LowStockAlertSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = LowStockAlert
        fields = ["id", "item", "item_name", "level", "threshold", "created_at"]
        read_only_fields = fields


# -- Requisitions ----------------------------------------------------------------
class RequisitionLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = RequisitionLine
        fields = ["item", "item_name", "unit", "quantity"]
        read_only_fields = fields


class RequisitionSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines = RequisitionLineSerializer(many=True, read_only=True)
    allowed_events = serializers.SerializerMethodField()

    class Meta:
        model = Requisition
        fields = ["id", "originator_user_id", "purpose", "status", "status_label", "lines",
                  "decision_note", "decided_at", "fulfilled_at", "created_at",
                  "allowed_events"]
        read_only_fields = fields

    def get_allowed_events(self, obj) -> list[str]:
        actor = self.context.get("actor")
        events = events_for(REQUISITION_TRANSITIONS, obj.status, _permissions(self.context))
        if actor is not None and obj.originator_user_id == getattr(actor, "user_id", None):
            events = [e for e in events if e == "fulfill"]
        return events


class RequisitionLineWriteSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class RequisitionWriteSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=500)
    lines = RequisitionLineWriteSerializer(many=True)


class RequisitionTransitionSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=sorted(REQUISITION_EVENTS))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


# -- Ambulance, advisories, notifications, reports -------------------------------
class AmbulanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceLog
        fields = ["id", "used_at", "patient_name", "destination", "created_at"]
        read_only_fields = ["id", "created_at"]


class AdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAdvisory
        fields = ["id", "title", "body", "published_at"]
        read_only_fields = ["id", "published_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "message", "resource_type", "resource_id", "created_at"]
        read_only_fields = fields


class ReportQuerySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    start = serializers.DateField()
    end = serializers.DateField()


class ReportSerializer(serializers.Serializer):
    category = serializers.CharField(read_only=True)
    start = serializers.DateField(read_only=True)
    end = serializers.DateField(read_only=True)
    data = serializers.DictField(read_only=True)
