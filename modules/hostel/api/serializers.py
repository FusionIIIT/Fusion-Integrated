"""Hostel Management API Serializers."""

from rest_framework import serializers

from modules.hostel.models import (
    AccommodationRequest,
    AttendanceRecord,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelInventoryItem,
    HostelNotice,
    HostelNotification,
    HostelRoleBinding,
    HostelStaffDutyLog,
    LeaveRequest,
    Room,
    RoomAllotment,
    RoomExchange,
    SecurityGuardShift,
)


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = "__all__"


class HostelRoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelRoleBinding
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    hostel_code = serializers.CharField(source="hostel.code", read_only=True)
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = Room
        fields = "__all__"


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = "__all__"
        read_only_fields = ("student_user_id", "status", "created_at", "updated_at")


class RoomAllotmentSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)

    class Meta:
        model = RoomAllotment
        fields = "__all__"


class RoomExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomExchange
        fields = "__all__"


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"


class AttendanceBatchRecordSerializer(serializers.Serializer):
    hostel_id = serializers.IntegerField()
    date = serializers.DateField()
    records = serializers.ListField(child=serializers.DictField())


class LeaveRequestSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "student_user_id",
            "status",
            "decision_by_user_id",
            "decision_at",
            "decision_remarks",
            "created_at",
            "updated_at",
        )


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HostelComplaintSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True, allow_null=True)

    class Meta:
        model = HostelComplaint
        fields = "__all__"
        read_only_fields = (
            "student_user_id",
            "status",
            "action_taken",
            "resolved_at",
            "escalated_to_user_id",
            "escalated_at",
            "handled_by_user_id",
            "created_at",
            "updated_at",
        )


class ComplaintUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["resolved", "unresolved", "escalated"])
    action_taken = serializers.CharField(required=False, allow_blank=True, default="")


class GuestRoomBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestRoomBooking
        fields = "__all__"
        read_only_fields = (
            "student_user_id",
            "status",
            "decision_by_user_id",
            "decision_at",
            "decision_remarks",
            "created_at",
            "updated_at",
        )


class GuestRoomDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    room_id = serializers.IntegerField(required=False, allow_null=True)


class ExtendedStayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtendedStayRequest
        fields = "__all__"
        read_only_fields = (
            "student_user_id",
            "status",
            "decision_by_user_id",
            "decision_at",
            "decision_remarks",
            "charge_amount",
            "payment_deadline",
            "compliance_status",
            "created_at",
            "updated_at",
        )


class ExtendedStayDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    charge_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_deadline = serializers.DateField(required=False, allow_null=True)


class HostelFineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelFine
        fields = "__all__"


class HostelInventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelInventoryItem
        fields = "__all__"


class HostelStaffDutyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelStaffDutyLog
        fields = "__all__"


class SecurityGuardShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityGuardShift
        fields = "__all__"


class HostelNoticeSerializer(serializers.ModelSerializer):
    hostel_name = serializers.CharField(source="hostel.name", read_only=True, allow_null=True)

    class Meta:
        model = HostelNotice
        fields = "__all__"
        read_only_fields = ("published_by_user_id", "published_at", "created_at", "updated_at")


class HostelNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelNotification
        fields = "__all__"
