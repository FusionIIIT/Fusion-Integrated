from rest_framework import serializers
try:
    from hostel_management.models import (
        Hostel, HostelRoleBinding, Room, AccommodationRequest,
        AttendanceRecord, LeaveRequest, HostelComplaint,
        GuestRoomBooking, ExtendedStayRequest, HostelFine,
        HostelInventory, SecurityGuardShift, HostelNotice, Notification
    )
except ImportError:
    from .models import (
        Hostel, HostelRoleBinding, Room, AccommodationRequest,
        AttendanceRecord, LeaveRequest, HostelComplaint,
        GuestRoomBooking, ExtendedStayRequest, HostelFine,
        HostelInventory, SecurityGuardShift, HostelNotice, Notification
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
    class Meta:
        model = Room
        fields = "__all__"


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = "__all__"


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"


class HostelComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelComplaint
        fields = "__all__"


class GuestRoomBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestRoomBooking
        fields = "__all__"


class ExtendedStayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtendedStayRequest
        fields = "__all__"


class HostelFineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelFine
        fields = "__all__"


class HostelInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelInventory
        fields = "__all__"


class SecurityGuardShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityGuardShift
        fields = "__all__"


class HostelNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelNotice
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
