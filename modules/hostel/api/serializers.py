"""Serializers for Hostel Management REST API."""

from rest_framework import serializers

from modules.hostel.models import (
    AccommodationRequest,
    AttendanceRecord,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelInventory,
    HostelLeave,
    HostelNotice,
    HostelNotification,
    HostelRoleBinding,
    HostelStaff,
    Room,
    RoomAllotment,
    RoomExchangeRequest,
    SecurityShift,
)


class HostelSerializer(serializers.ModelSerializer):
    rooms_count = serializers.IntegerField(source="rooms.count", read_only=True)
    active_bindings_count = serializers.SerializerMethodField()

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "code",
            "capacity",
            "gender",
            "description",
            "is_active",
            "rooms_count",
            "active_bindings_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_active_bindings_count(self, obj) -> int:
        return obj.role_bindings.filter(is_active=True).count()


class HostelRoleBindingSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelRoleBinding
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "hostel_name",
            "user_id",
            "role",
            "start_date",
            "end_date",
            "is_active",
            "assigned_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RoomSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "hostel_name",
            "room_number",
            "floor",
            "capacity",
            "current_occupancy",
            "available_beds",
            "status",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_occupancy", "created_at", "updated_at"]

    def get_available_beds(self, obj) -> int:
        return max(0, obj.capacity - obj.current_occupancy)


class AccommodationRequestSerializer(serializers.ModelSerializer):
    preferred_hostel_code = serializers.CharField(source="preferred_hostel.code", read_only=True)

    class Meta:
        model = AccommodationRequest
        fields = [
            "id",
            "student_user_id",
            "preferred_hostel",
            "preferred_hostel_code",
            "room_type_preference",
            "academic_year",
            "semester",
            "reason",
            "status",
            "decided_by_user_id",
            "decided_at",
            "remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "status",
            "decided_by_user_id",
            "decided_at",
            "created_at",
        ]


class RoomAllotmentSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)

    class Meta:
        model = RoomAllotment
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "hostel_name",
            "room",
            "room_number",
            "bed_number",
            "allotment_date",
            "vacated_date",
            "status",
            "allotted_by_user_id",
            "vacation_clearance_status",
            "vacation_remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RoomExchangeRequestSerializer(serializers.ModelSerializer):
    from_room_number = serializers.CharField(source="from_room.room_number", read_only=True)
    to_room_number = serializers.CharField(source="to_room.room_number", read_only=True)

    class Meta:
        model = RoomExchangeRequest
        fields = [
            "id",
            "requester_student_user_id",
            "target_student_user_id",
            "from_room",
            "from_room_number",
            "to_room",
            "to_room_number",
            "reason",
            "status",
            "approved_by_user_id",
            "decision_remarks",
            "created_at",
        ]
        read_only_fields = ["id", "status", "approved_by_user_id", "created_at"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "date",
            "status",
            "recorded_by_user_id",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HostelLeaveSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelLeave
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "leave_type",
            "from_date",
            "to_date",
            "reason",
            "destination",
            "emergency_contact",
            "status",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "status",
            "decided_by_user_id",
            "decided_at",
            "created_at",
        ]


class HostelComplaintSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelComplaint
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "category",
            "title",
            "description",
            "location",
            "severity",
            "status",
            "assigned_worker",
            "resolution_notes",
            "escalated_to_warden",
            "resolved_by_user_id",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "status",
            "escalated_to_warden",
            "resolved_by_user_id",
            "resolved_at",
            "created_at",
            "updated_at",
        ]


class GuestRoomBookingSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = GuestRoomBooking
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "guest_name",
            "relationship",
            "num_guests",
            "check_in_date",
            "check_out_date",
            "purpose",
            "status",
            "allocated_room_number",
            "charges",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "status",
            "allocated_room_number",
            "charges",
            "decided_by_user_id",
            "decided_at",
            "created_at",
        ]


class ExtendedStayRequestSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = ExtendedStayRequest
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "from_date",
            "to_date",
            "reason_type",
            "reason_details",
            "supporting_document_url",
            "charge_amount",
            "payment_deadline",
            "compliance_status",
            "status",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "status",
            "charge_amount",
            "payment_deadline",
            "compliance_status",
            "decided_by_user_id",
            "decided_at",
            "created_at",
        ]


class HostelFineSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelFine
        fields = [
            "id",
            "student_user_id",
            "hostel",
            "hostel_code",
            "amount",
            "reason",
            "issued_date",
            "due_date",
            "status",
            "imposed_by_user_id",
            "receipt_reference",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HostelInventorySerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelInventory
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "item_name",
            "category",
            "quantity_total",
            "quantity_functional",
            "quantity_damaged",
            "location",
            "last_inspected_at",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HostelStaffSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelStaff
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "name",
            "role",
            "phone_number",
            "shift",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SecurityShiftSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = SecurityShift
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "guard_name",
            "shift_date",
            "shift_type",
            "gate_location",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class HostelNoticeSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelNotice
        fields = [
            "id",
            "hostel",
            "hostel_code",
            "title",
            "content",
            "target_audience",
            "published_by_user_id",
            "is_active",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "published_by_user_id", "created_at"]


class HostelNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelNotification
        fields = [
            "id",
            "recipient_user_id",
            "title",
            "message",
            "event_type",
            "is_read",
            "link",
            "created_at",
        ]
        read_only_fields = ["id", "recipient_user_id", "created_at"]
