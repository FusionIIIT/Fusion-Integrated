"""Hostel Management domain models.

All external identity references are integer IDs (IAM user_ids).
Zero cross-module ForeignKeys (ADR-0013).
"""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    AllotmentStatus,
    AttendanceStatus,
    ComplaintCategory,
    ComplaintStatus,
    ExtendedStayCompliance,
    ExtendedStayStatus,
    FineStatus,
    GuestRoomBookingStatus,
    HostelGender,
    InventoryCondition,
    LeaveStatus,
    LeaveType,
    NoticePriority,
    NotificationEventType,
    RoleBindingType,
    RoomExchangeStatus,
    RoomStatus,
    RoomType,
    SecurityShiftStatus,
    ShiftType,
    StaffDutyRole,
)


class Hostel(TimeStampedModel):
    """Hostel Master entity representing a hostel facility."""

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=32, unique=True)
    gender_type = models.CharField(
        max_length=16,
        choices=[(g.value, g.name) for g in HostelGender],
        default=HostelGender.COED.value,
    )
    total_floors = models.PositiveIntegerField(default=1)
    total_rooms = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_hostel"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class HostelRoleBinding(TimeStampedModel):
    """Hostel-specific Warden and Caretaker role bindings (HM-UC-003, HM-UC-004, BR-HM-001)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(
        max_length=16,
        choices=[(r.value, r.name) for r in RoleBindingType],
    )
    shift = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in ShiftType],
        default=ShiftType.GENERAL.value,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "hostel_role_binding"
        indexes = [
            models.Index(fields=["user_id", "role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.role} @ {self.hostel.code}"


class Room(TimeStampedModel):
    """Hostel room entity (HM-UC-009, BR-HM-010)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=32)
    floor = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(default=2)
    current_occupancy = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in RoomStatus],
        default=RoomStatus.AVAILABLE.value,
    )
    room_type = models.CharField(
        max_length=16,
        choices=[(t.value, t.name) for t in RoomType],
        default=RoomType.STANDARD.value,
    )

    class Meta:
        db_table = "hostel_room"
        unique_together = ("hostel", "room_number")
        ordering = ["hostel", "room_number"]

    def __str__(self) -> str:
        return f"{self.hostel.code} - Room {self.room_number}"


class AccommodationRequest(TimeStampedModel):
    """Student hostel accommodation request (HM-UC-005, BW-HM-01)."""

    student_user_id = models.IntegerField(db_index=True)
    preferred_hostel = models.ForeignKey(
        Hostel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accommodation_requests",
    )
    academic_year = models.CharField(max_length=32, default="2026-2027")
    semester = models.CharField(max_length=32, default="Regular")
    preferences = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in AccommodationRequestStatus],
        default=AccommodationRequestStatus.SUBMITTED.value,
        db_index=True,
    )
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_accommodation_request"
        ordering = ["-created_at"]


class RoomAllotment(TimeStampedModel):
    """Room Allotment & historical tracking (HM-UC-006, HM-UC-007, BR-HM-009)."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="allotments")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="allotments")
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in AllotmentStatus],
        default=AllotmentStatus.ACTIVE.value,
        db_index=True,
    )
    allotted_at = models.DateTimeField(auto_now_add=True)
    allotment_round = models.CharField(max_length=64, blank=True, default="Round 1")
    vacated_at = models.DateTimeField(null=True, blank=True)
    allotted_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_room_allotment"
        ordering = ["-created_at"]


class RoomExchange(TimeStampedModel):
    """Individual room exchange records (HM-UC-010)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="exchanges")
    student_a_user_id = models.IntegerField(db_index=True)
    room_a = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="exchanges_from")
    student_b_user_id = models.IntegerField(db_index=True)
    room_b = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="exchanges_to")
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in RoomExchangeStatus],
        default=RoomExchangeStatus.COMPLETED.value,
    )
    reason = models.TextField(blank=True, default="")
    processed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_room_exchange"


class AttendanceRecord(TimeStampedModel):
    """Hostel student attendance records (HM-UC-012, BR-HM-011)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendance_records")
    student_user_id = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in AttendanceStatus],
        default=AttendanceStatus.PRESENT.value,
    )
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "hostel_attendance_record"
        unique_together = ("student_user_id", "date")
        ordering = ["-date"]


class LeaveRequest(TimeStampedModel):
    """Student leave requests (HM-UC-014, HM-UC-015, CW-HM-01, BR-HM-013)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leave_requests")
    student_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(
        max_length=16,
        choices=[(t.value, t.name) for t in LeaveType],
        default=LeaveType.HOME.value,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    destination = models.CharField(max_length=255, blank=True, default="")
    supporting_document = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in LeaveStatus],
        default=LeaveStatus.SUBMITTED.value,
        db_index=True,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_leave_request"
        ordering = ["-created_at"]


class HostelComplaint(TimeStampedModel):
    """Hostel-related complaints (HM-UC-017, HM-UC-018, CW-HM-02, BR-HM-015, BR-HM-016)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    student_user_id = models.IntegerField(db_index=True)
    category = models.CharField(
        max_length=32,
        choices=[(c.value, c.name) for c in ComplaintCategory],
    )
    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints"
    )
    description = models.TextField()
    attachment = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in ComplaintStatus],
        default=ComplaintStatus.SUBMITTED.value,
        db_index=True,
    )
    action_taken = models.TextField(blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_to_user_id = models.IntegerField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    handled_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_complaint"
        ordering = ["-created_at"]


class GuestRoomBooking(TimeStampedModel):
    """Guest-room booking request (HM-UC-020, HM-UC-021, CW-HM-03, BR-HM-018)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_bookings")
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="guest_bookings", null=True, blank=True
    )
    student_user_id = models.IntegerField(db_index=True)
    guest_name = models.CharField(max_length=128)
    guest_relation = models.CharField(max_length=64)
    guest_contact = models.CharField(max_length=32)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in GuestRoomBookingStatus],
        default=GuestRoomBookingStatus.SUBMITTED.value,
        db_index=True,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_guest_room_booking"
        ordering = ["-created_at"]


class ExtendedStayRequest(TimeStampedModel):
    """Extended-stay requests during vacations/breaks (HM-UC-023..024, CW-HM-04, BR-HM-020)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="extended_stays")
    student_user_id = models.IntegerField(db_index=True)
    stay_reason = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in ExtendedStayStatus],
        default=ExtendedStayStatus.SUBMITTED.value,
        db_index=True,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_deadline = models.DateField(null=True, blank=True)
    compliance_status = models.CharField(
        max_length=16,
        choices=[(c.value, c.name) for c in ExtendedStayCompliance],
        default=ExtendedStayCompliance.PENDING.value,
    )

    class Meta:
        db_table = "hostel_extended_stay"
        ordering = ["-created_at"]


class HostelFine(TimeStampedModel):
    """Hostel disciplinary fines (HM-UC-026, BR-HM-025, BR-HM-026)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    student_user_id = models.IntegerField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    imposed_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in FineStatus],
        default=FineStatus.RECORDED.value,
    )
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_fine"
        ordering = ["-imposed_date"]


class HostelInventoryItem(TimeStampedModel):
    """Hostel operational inventory (HM-UC-028, BR-HM-027)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventory_items")
    item_name = models.CharField(max_length=128)
    category = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(
        max_length=16,
        choices=[(c.value, c.name) for c in InventoryCondition],
        default=InventoryCondition.WORKING.value,
    )
    location = models.CharField(max_length=128, blank=True, default="")
    last_inspected_date = models.DateField(null=True, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_inventory_item"
        ordering = ["item_name"]


class HostelStaffDutyLog(TimeStampedModel):
    """Hostel staff duty coordination log (HM-UC-029, BR-HM-027)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="staff_logs")
    staff_name = models.CharField(max_length=128)
    role = models.CharField(
        max_length=16,
        choices=[(r.value, r.name) for r in StaffDutyRole],
        default=StaffDutyRole.OTHER.value,
    )
    shift = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in ShiftType],
        default=ShiftType.GENERAL.value,
    )
    date = models.DateField(db_index=True)
    duty_notes = models.TextField(blank=True, default="")
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_staff_duty_log"
        ordering = ["-date"]


class SecurityGuardShift(TimeStampedModel):
    """Security guard shift schedule (HM-UC-030, BR-HM-028)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="security_shifts")
    guard_name = models.CharField(max_length=128)
    shift = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in ShiftType],
        default=ShiftType.MORNING.value,
    )
    shift_date = models.DateField(db_index=True)
    gate_post = models.CharField(max_length=64, default="Main Gate")
    status = models.CharField(
        max_length=16,
        choices=[(s.value, s.name) for s in SecurityShiftStatus],
        default=SecurityShiftStatus.SCHEDULED.value,
    )
    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "hostel_security_guard_shift"
        ordering = ["-shift_date"]


class HostelNotice(TimeStampedModel):
    """Hostel notices and announcements (HM-UC-031, HM-UC-032, BR-HM-029, BR-HM-030, BR-HM-031)."""

    hostel = models.ForeignKey(
        Hostel, on_delete=models.CASCADE, null=True, blank=True, related_name="notices"
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(
        max_length=16,
        choices=[(p.value, p.name) for p in NoticePriority],
        default=NoticePriority.NORMAL.value,
    )
    published_by_user_id = models.IntegerField(db_index=True)
    published_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "hostel_notice"
        ordering = ["-published_at"]


class HostelNotification(TimeStampedModel):
    """HM system notifications and status updates (HM-UC-034, BR-HM-034)."""

    recipient_user_id = models.IntegerField(db_index=True)
    event_type = models.CharField(
        max_length=32,
        choices=[(e.value, e.name) for e in NotificationEventType],
        default=NotificationEventType.GENERAL.value,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "hostel_notification"
        ordering = ["-created_at"]
