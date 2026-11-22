"""DRF Serializers for PHC module."""
from rest_framework import serializers

from modules.phc.models.ambulance import AmbulanceLog
from modules.phc.models.announcements import HealthAnnouncement
from modules.phc.models.audit import PHCAuditTrail
from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule
from modules.phc.models.inventory import (
    InventoryItem,
    InventoryStockAdjustment,
    ProcurementRequisition,
    RequisitionItem,
)
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.models.reimbursement import ReimbursementActionHistory, ReimbursementClaim


# --- Doctors & Schedules ---
class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization", "contact_phone", "email", "is_visiting", "is_active"]


class DoctorScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = [
            "id", "doctor", "doctor_name", "specialization", "day_of_week",
            "start_time", "end_time", "room_number", "is_published",
        ]


class DoctorAttendanceSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)

    class Meta:
        model = DoctorAttendance
        fields = ["id", "doctor", "doctor_name", "date", "status", "marked_by_user_id", "remarks", "updated_at"]


# --- Patient Records & Prescriptions ---
class PrescriptionSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="visit.doctor.name", read_only=True, default="N/A")

    class Meta:
        model = Prescription
        fields = [
            "id", "visit", "patient_user_id", "prescription_number", "prescribed_date",
            "medicines_prescribed", "scanned_document_url", "notes", "doctor_name", "created_at",
        ]


class PatientVisitSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True, default="N/A")
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = PatientVisit
        fields = [
            "id", "patient_user_id", "doctor", "doctor_name", "visit_date",
            "symptoms", "diagnosis", "notes", "created_by_user_id", "prescriptions", "created_at",
        ]


class PatientVisitCreateSerializer(serializers.Serializer):
    patient_user_id = serializers.IntegerField()
    doctor_id = serializers.IntegerField(required=False, allow_null=True)
    visit_date = serializers.DateField(required=False)
    symptoms = serializers.CharField()
    diagnosis = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PrescriptionCreateSerializer(serializers.Serializer):
    visit_id = serializers.IntegerField()
    prescription_number = serializers.CharField(max_length=64)
    prescribed_date = serializers.DateField(required=False)
    medicines_prescribed = serializers.CharField()
    scanned_document_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# --- Reimbursement Claims ---
class ReimbursementActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementActionHistory
        fields = ["id", "action", "from_status", "to_status", "actor_user_id", "actor_role", "comments", "created_at"]


class ReimbursementClaimSerializer(serializers.ModelSerializer):
    history = ReimbursementActionHistorySerializer(many=True, read_only=True)
    prescription_number = serializers.CharField(source="prescription.prescription_number", read_only=True)

    class Meta:
        model = ReimbursementClaim
        fields = [
            "id", "claim_number", "claimant_user_id", "prescription", "prescription_number",
            "expense_date", "amount_claimed", "amount_approved", "bills_document_url",
            "status", "remarks", "created_at", "updated_at", "history",
        ]


class ReimbursementClaimSubmitSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField()
    expense_date = serializers.DateField()
    amount_claimed = serializers.DecimalField(max_digits=10, decimal_places=2)
    bills_document_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# --- Inventory & Requisitions ---
class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id", "item_code", "name", "category", "stock_level",
            "reorder_threshold", "unit", "description", "is_low_stock",
        ]

    def get_is_low_stock(self, obj) -> bool:
        return obj.stock_level < obj.reorder_threshold


class StockAdjustmentSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = InventoryStockAdjustment
        fields = ["id", "item", "item_name", "adjustment_type", "quantity", "previous_stock", "new_stock", "reason", "adjusted_by_user_id", "created_at"]


class StockAdjustmentCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    adjustment_type = serializers.ChoiceField(choices=["ADD", "DEDUCT"])
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255)


class RequisitionItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.item_code", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = RequisitionItem
        fields = ["id", "item", "item_name", "item_code", "unit", "quantity_requested"]


class ProcurementRequisitionSerializer(serializers.ModelSerializer):
    items = RequisitionItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProcurementRequisition
        fields = [
            "id", "requisition_number", "originator_user_id", "status", "justification",
            "approver_user_id", "decision_at", "decision_remarks", "fulfilled_at",
            "fulfilled_by_user_id", "items", "created_at",
        ]


class ProcurementRequisitionSubmitSerializer(serializers.Serializer):
    justification = serializers.CharField()
    items = serializers.ListField(child=serializers.DictField())


# --- Ambulance, Announcements, Audit, Notifications ---
class AmbulanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbulanceLog
        fields = [
            "id", "patient_name", "patient_user_id", "destination", "departure_time",
            "return_time", "driver_name", "reason", "recorded_by_user_id", "created_at",
        ]


class HealthAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthAnnouncement
        fields = ["id", "title", "content", "priority", "published_date", "is_active", "published_by_user_id"]


class PHCAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PHCAuditTrail
        fields = ["id", "target_type", "target_id", "action", "details", "actor_user_id", "actor_username", "created_at"]


class PHCNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PHCNotification
        fields = ["id", "recipient_user_id", "notification_type", "title", "message", "is_read", "created_at"]
