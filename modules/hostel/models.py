"""Hostel Management database models."""

from django.db import models
from core.db.mixins import TimeStampedModel
from .domain.constants import (
    AccommodationStatus,
    AttendanceStatus,
    ComplaintCategory,
    ComplaintStatus,
    ExtendedStayReason,
    ExtendedStayStatus,
    FineType,
    GenderPolicy,
    GuestRoomStatus,
    HostelRole,
    InventoryCategory,
    InventoryCondition,
    LeaveStatus,
    LeaveType,
    NoticeCategory,
    PaymentComplianceStatus,
    RoomType,
    ShiftType,
    StaffRole,
)


class Hostel(TimeStampedModel):
    """Hostel Master Record (3.0 Hostel Master Administration, CFR-HM-001)."""

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    gender_policy = models.CharField(
        max_length=20,
        choices=[(p.value, p.name) for p in GenderPolicy],
        default=GenderPolicy.COED.value,
    )
    capacity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_master"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class HostelRoleBinding(TimeStampedModel):
    """Hostel-specific Warden and Caretaker role bindings (3.0 & 3.14, CFR-HM-002, BR-HM-001)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(
        max_length=30,
        choices=[(r.value, r.name) for r in HostelRole],
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_role_binding"
        indexes = [
            models.Index(fields=["user_id", "is_active"], name="hostel_role_user_idx"),
            models.Index(fields=["hostel", "role", "is_active"], name="hostel_role_hostel_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} as {self.role} in {self.hostel.name}"


class Room(TimeStampedModel):
    """Room Master and Availability (3.1 & 3.2, CFR-HM-004, BR-HM-010)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    floor = models.IntegerField(default=1)
    capacity = models.IntegerField(default=1)
    current_occupancy = models.IntegerField(default=0)
    room_type = models.CharField(
        max_length=20,
        choices=[(r.value, r.name) for r in RoomType],
        default=RoomType.DOUBLE.value,
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = "hostel_room"
        unique_together = ("hostel", "room_number")
        ordering = ["hostel", "room_number"]

    def __str__(self) -> str:
        return f"{self.hostel.code}-{self.room_number}"


class AccommodationRequest(TimeStampedModel):
    """Hostel Accommodation Request (3.1, CFR-HM-003, BW-HM-01)."""

    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    requested_hostel = models.ForeignKey(Hostel, null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=[(s.value, s.name) for s in AccommodationStatus],
        default=AccommodationStatus.SUBMITTED.value,
    )

    class Meta:
        db_table = "hostel_accommodation_request"
        ordering = ["-created_at"]


class RoomAllotment(TimeStampedModel):
    """Room Allotment & Occupancy record (3.1 & 3.2, CFR-HM-004, BR-HM-008)."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="allotments")
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="allotments")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    allotted_at = models.DateTimeField(auto_now_add=True)
    allotted_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)
    vacated_at = models.DateTimeField(null=True, blank=True)
    vacation_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "hostel_room_allotment"
        indexes = [
            models.Index(fields=["student_user_id", "is_active"], name="allotment_student_idx"),
            models.Index(fields=["room", "is_active"], name="allotment_room_idx"),
        ]


class RoomAssignmentHistory(models.Model):
    """Room assignment historical audit trail (3.1 & 3.2, BR-HM-009)."""

    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    from_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="history_from")
    to_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="history_to")
    action_type = models.CharField(max_length=40)  # 'allotment', 're_allotment', 'exchange', 'vacation'
    performed_by_user_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_room_history"
        ordering = ["-timestamp"]


class AttendanceRecord(TimeStampedModel):
    """Hostel Attendance Record (3.3, CFR-HM-008, BR-HM-011)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendance_records")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in AttendanceStatus],
        default=AttendanceStatus.PRESENT.value,
    )
    marked_by_user_id = models.IntegerField()
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "hostel_attendance"
        unique_together = ("hostel", "student_user_id", "date")
        ordering = ["-date", "student_roll_number"]


class LeaveRequest(TimeStampedModel):
    """Hostel Student Leave Request (3.4, CFR-HM-011, BR-HM-013, CW-HM-01)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leave_requests")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    leave_type = models.CharField(
        max_length=30,
        choices=[(t.value, t.name) for t in LeaveType],
        default=LeaveType.HOME.value,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    address_during_leave = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=50, blank=True)
    supporting_document = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in LeaveStatus],
        default=LeaveStatus.SUBMITTED.value,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_leave_request"
        ordering = ["-created_at"]


class HostelComplaint(TimeStampedModel):
    """Hostel-related Complaint (3.5, CFR-HM-014, BR-HM-015, CW-HM-02)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    room_number = models.CharField(max_length=20, blank=True)
    category = models.CharField(
        max_length=30,
        choices=[(c.value, c.name) for c in ComplaintCategory],
        default=ComplaintCategory.OTHER.value,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    attachment_url = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ComplaintStatus],
        default=ComplaintStatus.SUBMITTED.value,
    )
    action_taken = models.TextField(blank=True)
    caretaker_user_id = models.IntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_to_warden = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_complaint"
        ordering = ["-created_at"]


class GuestRoomBooking(TimeStampedModel):
    """Guest Room Booking Request (3.6, CFR-HM-017, BR-HM-018, CW-HM-03)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_bookings")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    guest_name = models.CharField(max_length=120)
    guest_relation = models.CharField(max_length=60)
    guest_gender = models.CharField(max_length=20)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    number_of_guests = models.IntegerField(default=1)
    assigned_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in GuestRoomStatus],
        default=GuestRoomStatus.REQUESTED.value,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_guest_room_booking"
        ordering = ["-created_at"]


class ExtendedStayRequest(TimeStampedModel):
    """Vacation Extended-Stay Request (3.7, CFR-HM-020, BR-HM-020..024, CW-HM-04)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="extended_stays")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    stay_reason = models.CharField(
        max_length=30,
        choices=[(r.value, r.name) for r in ExtendedStayReason],
        default=ExtendedStayReason.ACADEMIC.value,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    remarks = models.TextField(blank=True)
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=30,
        choices=[(p.value, p.name) for p in PaymentComplianceStatus],
        default=PaymentComplianceStatus.PENDING.value,
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ExtendedStayStatus],
        default=ExtendedStayStatus.SUBMITTED.value,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_extended_stay"
        ordering = ["-created_at"]


class HostelFine(TimeStampedModel):
    """Hostel Disciplinary and Damage Fine (3.8, CFR-HM-024, BR-HM-025, BR-HM-026)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    student_user_id = models.IntegerField(db_index=True)
    student_roll_number = models.CharField(max_length=30)
    student_name = models.CharField(max_length=120)
    reason = models.TextField()  # mandatory
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # mandatory
    date = models.DateField()  # mandatory
    fine_type = models.CharField(
        max_length=30,
        choices=[(f.value, f.name) for f in FineType],
        default=FineType.RULE_VIOLATION.value,
    )
    is_paid = models.BooleanField(default=False)
    imposed_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hostel_fine"
        ordering = ["-date"]


class HostelInventoryItem(TimeStampedModel):
    """Hostel Operational Inventory Record (3.9, CFR-HM-027, BR-HM-027)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventory_items")
    item_name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=30,
        choices=[(c.value, c.name) for c in InventoryCategory],
        default=InventoryCategory.FURNITURE.value,
    )
    total_quantity = models.IntegerField(default=1)
    in_use_quantity = models.IntegerField(default=0)
    available_quantity = models.IntegerField(default=1)
    condition = models.CharField(
        max_length=30,
        choices=[(c.value, c.name) for c in InventoryCondition],
        default=InventoryCondition.GOOD.value,
    )
    location = models.CharField(max_length=120, default="Store Room")
    last_updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_inventory"
        ordering = ["item_name"]


class InventoryAuditLog(models.Model):
    """Accountability Audit Log for Inventory changes (3.9, BR-HM-027)."""

    item = models.ForeignKey(HostelInventoryItem, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    performed_by_user_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hostel_inventory_audit"
        ordering = ["-timestamp"]


class StaffAssignment(TimeStampedModel):
    """Hostel Operational Staff Coordination (3.9, CFR-HM-028)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="staff_assignments")
    staff_name = models.CharField(max_length=120)
    role_designation = models.CharField(
        max_length=40,
        choices=[(r.value, r.name) for r in StaffRole],
        default=StaffRole.ATTENDANT.value,
    )
    shift = models.CharField(
        max_length=30,
        choices=[(s.value, s.name) for s in ShiftType],
        default=ShiftType.GENERAL.value,
    )
    contact_number = models.CharField(max_length=30, blank=True)
    duty_location = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hostel_staff_assignment"
        ordering = ["staff_name"]


class SecurityGuardShift(TimeStampedModel):
    """Security Guard Shift Schedule (3.10, CFR-HM-030, BR-HM-028)."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="security_shifts")
    guard_name = models.CharField(max_length=120)
    agency_or_badge_number = models.CharField(max_length=60, blank=True)
    shift_type = models.CharField(
        max_length=30,
        choices=[(s.value, s.name) for s in ShiftType],
        default=ShiftType.NIGHT.value,
    )
    shift_date = models.DateField(db_index=True)
    gate_or_post = models.CharField(max_length=100, default="Main Gate")
    contact_number = models.CharField(max_length=30, blank=True)
    supervisor_name = models.CharField(max_length=120, blank=True)
    is_verified = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hostel_security_shift"
        ordering = ["-shift_date", "shift_type"]


class HostelNotice(TimeStampedModel):
    """Hostel Notices & Announcements (3.11, CFR-HM-032, BR-HM-029..031)."""

    hostel = models.ForeignKey(Hostel, null=True, blank=True, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=[(c.value, c.name) for c in NoticeCategory],
        default=NoticeCategory.GENERAL.value,
    )
    is_pinned = models.BooleanField(default=False)
    published_by_user_id = models.IntegerField()
    published_by_role = models.CharField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hostel_notice"
        ordering = ["-is_pinned", "-created_at"]


class NotificationRecord(models.Model):
    """Hostel In-App Notifications (3.13, CFR-HM-038, BR-HM-034)."""

    recipient_user_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    message = models.TextField()
    reference_id = models.CharField(max_length=60, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hostel_notification"
        ordering = ["-created_at"]
