"""Hostel Management API Serializers."""

from rest_framework import serializers
from ..models import (
    AccommodationRequest,
    AttendanceRecord,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelInventoryItem,
    HostelNotice,
    HostelRoleBinding,
    InventoryAuditLog,
    LeaveRequest,
    NotificationRecord,
    Room,
    RoomAllotment,
    RoomAssignmentHistory,
    SecurityGuardShift,
    StaffAssignment,
)


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"


class HostelRoleBindingSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)

    class Meta:
        model = HostelRoleBinding
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = "__all__"

    def get_available_beds(self, obj) -> int:
        return max(0, obj.capacity - obj.current_occupancy)


class AccommodationRequestSerializer(serializers.ModelSerializer):
    requested_hostel_name = serializers.CharField(source="requested_hostel.name", read_only=True)

    class Meta:
        model = AccommodationRequest
        fields = "__all__"


class RoomAllotmentSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)

    class Meta:
        model = RoomAllotment
        fields = "__all__"


class RoomAssignmentHistorySerializer(serializers.ModelSerializer):
    from_room_number = serializers.CharField(source="from_room.room_number", read_only=True)
    to_room_number = serializers.CharField(source="to_room.room_number", read_only=True)

    class Meta:
        model = RoomAssignmentHistory
        fields = "__all__"


class AttendanceRecordSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"


class HostelComplaintSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelComplaint
        fields = "__all__"


class GuestRoomBookingSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    assigned_room_number = serializers.CharField(source="assigned_room.room_number", read_only=True)

    class Meta:
        model = GuestRoomBooking
        fields = "__all__"


class ExtendedStayRequestSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = ExtendedStayRequest
        fields = "__all__"


class HostelFineSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelFine
        fields = "__all__"


class HostelInventoryItemSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelInventoryItem
        fields = "__all__"


class InventoryAuditLogSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.item_name", read_only=True)

    class Meta:
        model = InventoryAuditLog
        fields = "__all__"


class StaffAssignmentSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = StaffAssignment
        fields = "__all__"


class SecurityGuardShiftSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = SecurityGuardShift
        fields = "__all__"


class HostelNoticeSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = HostelNotice
        fields = "__all__"


class NotificationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecord
        fields = "__all__"
