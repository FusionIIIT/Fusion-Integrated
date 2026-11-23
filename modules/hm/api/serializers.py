from rest_framework import serializers
from modules.hm.models import (
    Hostel,
    HostelRoleBinding,
    Room,
    AccommodationRequest,
    RoomAssignment,
    AttendanceRecord,
    LeaveRequest,
    Complaint,
    ComplaintEvent,
    GuestBooking,
    ExtendedStayRequest,
    FineRecord,
    InventoryItem,
    GuardShift,
    Notice,
)


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = ["id", "name", "code", "is_active", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class HostelRoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelRoleBinding
        fields = [
            "id", "hostel", "user_id", "role_kind", "is_active",
            "valid_from", "valid_to", "assigned_by_user_id", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RoomSerializer(serializers.ModelSerializer):
    occupied_count = serializers.IntegerField(read_only=True)
    available_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = [
            "id", "hostel", "room_number", "capacity", "occupied_count",
            "available_capacity", "is_active", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "occupied_count", "available_capacity", "created_at", "updated_at"]


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = [
            "id", "user_id", "hostel", "preferred_room_type", "reason",
            "status", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user_id", "status", "created_at", "updated_at"]


class RoomAssignmentSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    hostel_id = serializers.IntegerField(source="room.hostel_id", read_only=True)

    class Meta:
        model = RoomAssignment
        fields = [
            "id", "user_id", "room", "room_number", "hostel_id", "status",
            "effective_from", "effective_to", "assigned_by_user_id", "reason",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "user_id", "hostel", "date", "is_present",
            "recorded_by_user_id", "remarks", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "hostel", "start_date", "end_date", "reason",
            "status", "decided_by_user_id", "decision_remarks", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user_id", "status", "decided_by_user_id", "decision_remarks", "created_at", "updated_at"]


class ComplaintEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintEvent
        fields = ["id", "actor_user_id", "actor_kind", "event", "remarks", "created_at"]


class ComplaintSerializer(serializers.ModelSerializer):
    events = ComplaintEventSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "user_id", "hostel", "category", "description",
            "status", "events", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user_id", "status", "created_at", "updated_at"]


class GuestBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestBooking
        fields = [
            "id", "user_id", "hostel", "guest_name", "relation",
            "start_date", "end_date", "status", "decided_by_user_id",
            "remarks", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user_id", "status", "decided_by_user_id", "remarks", "created_at", "updated_at"]


class ExtendedStayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtendedStayRequest
        fields = [
            "id", "user_id", "hostel", "start_date", "end_date", "reason",
            "status", "decided_by_user_id", "remarks", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user_id", "status", "decided_by_user_id", "remarks", "created_at", "updated_at"]


class FineRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FineRecord
        fields = ["id", "user_id", "hostel", "amount", "reason", "imposed_by_user_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "id", "hostel", "name", "quantity", "description",
            "updated_by_user_id", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "updated_by_user_id", "created_at", "updated_at"]


class GuardShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardShift
        fields = ["id", "hostel", "guard_name", "shift_date", "shift_type", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = [
            "id", "hostel", "title", "content", "status",
            "published_by_user_id", "published_at", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "status", "published_by_user_id", "published_at", "created_at", "updated_at"]
