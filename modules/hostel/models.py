"""Hostel Management domain models.

All external person references use plain integer `user_id`s in strict adherence
to ADR-0013 (no cross-module foreign keys).
"""

from django.db import models
from django.db.models import CheckConstraint, F, Index, Q

from core.db.mixins import TimeStampedModel

from .domain.constants import (
    AccommodationRequestStatus,
    AllotmentStatus,
    AttendanceStatus,
    ComplaintCategory,
    ComplaintSeverity,
    ComplaintStatus,
    ComplianceStatus,
    ExtendedStayReason,
    ExtendedStayStatus,
    FineStatus,
    GuestRoomBookingStatus,
    HostelGender,
    InventoryCategory,
    LeaveStatus,
    LeaveType,
    NoticeAudience,
    NotificationEventType,
    RoleBindingType,
    RoomExchangeStatus,
    RoomStatus,
    SecurityShiftType,
    StaffRole,
    StaffShift,
)


class Hostel(TimeStampedModel):
    """CFR-HM-001: Hostel Master entity."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    capacity = models.PositiveIntegerField(default=0)
    gender = models.CharField(
        max_length=10,
        choices=[(g.value, g.name) for g in HostelGender],
        default=HostelGender.BOYS.value,
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            Index(fields=["is_active", "code"], name="hostel_active_code_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class HostelRoleBinding(TimeStampedModel):
    """CFR-HM-002, BR-HM-001, BR-HM-004: Warden/Caretaker role bindings."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=[(r.value, r.name) for r in RoleBindingType],
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["user_id", "is_active"], name="hostel_role_user_active_idx"),
            Index(fields=["hostel", "role", "is_active"], name="hostel_role_binding_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} as {self.role} in {self.hostel.code}"


class Room(TimeStampedModel):
    """CFR-HM-004, CFR-HM-006, BR-HM-010: Room entity with capacity constraints."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    floor = models.IntegerField(default=0)
    capacity = models.PositiveIntegerField(default=2)
    current_occupancy = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in RoomStatus],
        default=RoomStatus.AVAILABLE.value,
        db_index=True,
    )
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["hostel", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "room_number"], name="unique_room_per_hostel"
            ),
            CheckConstraint(
                condition=Q(current_occupancy__lte=F("capacity")),
                name="room_capacity_not_exceeded",
            ),
        ]
        indexes = [
            Index(fields=["hostel", "status"], name="room_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.hostel.code} - Room {self.room_number}"


class AccommodationRequest(TimeStampedModel):
    """CFR-HM-003, BW-HM-01: Student hostel accommodation applications."""

    student_user_id = models.IntegerField(db_index=True)
    preferred_hostel = models.ForeignKey(
        Hostel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accommodation_requests",
    )
    room_type_preference = models.CharField(max_length=50, blank=True, default="")
    academic_year = models.CharField(max_length=20, default="2026-27")
    semester = models.IntegerField(default=1)
    reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in AccommodationRequestStatus],
        default=AccommodationRequestStatus.PENDING.value,
        db_index=True,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="accom_req_student_idx"),
        ]


class RoomAllotment(TimeStampedModel):
    """CFR-HM-004, CFR-HM-005, BR-HM-009: Room Allotment lifecycle and history."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="allotments")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="allotments")
    bed_number = models.CharField(max_length=10, blank=True, default="A")
    allotment_date = models.DateField()
    vacated_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in AllotmentStatus],
        default=AllotmentStatus.ACTIVE.value,
        db_index=True,
    )
    allotted_by_user_id = models.IntegerField(null=True, blank=True)
    vacation_clearance_status = models.BooleanField(default=False)
    vacation_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="allotment_student_status_idx"),
            Index(fields=["hostel", "status"], name="allotment_hostel_status_idx"),
        ]


class RoomExchangeRequest(TimeStampedModel):
    """CFR-HM-007, HM-UC-010: Student room exchange."""

    requester_student_user_id = models.IntegerField(db_index=True)
    target_student_user_id = models.IntegerField(db_index=True)
    from_room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="exchanges_out")
    to_room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="exchanges_in")
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in RoomExchangeStatus],
        default=RoomExchangeStatus.REQUESTED.value,
        db_index=True,
    )
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]


class AttendanceRecord(TimeStampedModel):
    """CFR-HM-009, CFR-HM-010, BR-HM-011: Daily student attendance recording."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in AttendanceStatus],
        default=AttendanceStatus.PRESENT.value,
    )
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "student_user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_user_id", "date"], name="unique_daily_attendance"
            ),
        ]
        indexes = [
            Index(fields=["hostel", "date"], name="attendance_hostel_date_idx"),
        ]


class HostelLeave(TimeStampedModel):
    """CFR-HM-012..014, BR-HM-013, BW-HM-02/03, CW-HM-01: Student leave requests."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.name) for t in LeaveType],
        default=LeaveType.HOME.value,
    )
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.TextField()
    destination = models.CharField(max_length=255, blank=True, default="")
    emergency_contact = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in LeaveStatus],
        default=LeaveStatus.PENDING.value,
        db_index=True,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="leave_student_status_idx"),
            Index(fields=["hostel", "status"], name="leave_hostel_status_idx"),
        ]


class HostelComplaint(TimeStampedModel):
    """CFR-HM-015..018, BR-HM-015..017, BW-HM-04/05, CW-HM-02: Complaints & Escalation."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(
        max_length=20,
        choices=[(c.value, c.name) for c in ComplaintCategory],
        default=ComplaintCategory.ELECTRICAL.value,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=150)
    severity = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ComplaintSeverity],
        default=ComplaintSeverity.MEDIUM.value,
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ComplaintStatus],
        default=ComplaintStatus.OPEN.value,
        db_index=True,
    )
    assigned_worker = models.CharField(max_length=100, blank=True, default="")
    resolution_notes = models.TextField(blank=True, default="")
    escalated_to_warden = models.BooleanField(default=False, db_index=True)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["hostel", "status"], name="complaint_hostel_status_idx"),
            Index(fields=["student_user_id", "status"], name="complaint_student_idx"),
        ]


class GuestRoomBooking(TimeStampedModel):
    """CFR-HM-019..021, BR-HM-018, BW-HM-06/07, CW-HM-03: Guest room booking requests."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_room_bookings")
    guest_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    num_guests = models.PositiveIntegerField(default=1)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in GuestRoomBookingStatus],
        default=GuestRoomBookingStatus.PENDING.value,
        db_index=True,
    )
    allocated_room_number = models.CharField(max_length=20, blank=True, default="")
    charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="guest_booking_student_idx"),
            Index(fields=["hostel", "status"], name="guest_booking_hostel_idx"),
        ]


class ExtendedStayRequest(TimeStampedModel):
    """CFR-HM-022..024, BR-HM-020..024, BW-HM-08/09, CW-HM-04: Extended stay handling."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(
        Hostel, on_delete=models.CASCADE, related_name="extended_stay_requests"
    )
    from_date = models.DateField()
    to_date = models.DateField()
    reason_type = models.CharField(
        max_length=20,
        choices=[(r.value, r.name) for r in ExtendedStayReason],
        default=ExtendedStayReason.INTERNSHIP.value,
    )
    reason_details = models.TextField()
    supporting_document_url = models.CharField(max_length=500, blank=True, default="")
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_deadline = models.DateField(null=True, blank=True)
    compliance_status = models.CharField(
        max_length=20,
        choices=[(c.value, c.name) for c in ComplianceStatus],
        default=ComplianceStatus.PENDING.value,
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in ExtendedStayStatus],
        default=ExtendedStayStatus.PENDING.value,
        db_index=True,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="ext_stay_student_idx"),
            Index(fields=["hostel", "status"], name="ext_stay_hostel_idx"),
        ]


class HostelFine(TimeStampedModel):
    """CFR-HM-025..027, BR-HM-025, 026: Disciplinary fine recording."""

    student_user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    issued_date = models.DateField(db_index=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in FineStatus],
        default=FineStatus.PENDING.value,
        db_index=True,
    )
    imposed_by_user_id = models.IntegerField(null=True, blank=True)
    receipt_reference = models.CharField(max_length=100, blank=True, default="")
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issued_date"]
        indexes = [
            Index(fields=["student_user_id", "status"], name="fine_student_status_idx"),
            Index(fields=["hostel", "status"], name="fine_hostel_status_idx"),
        ]


class HostelInventory(TimeStampedModel):
    """CFR-HM-028, BR-HM-027: Hostel operational inventory."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventory_items")
    item_name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=[(c.value, c.name) for c in InventoryCategory],
        default=InventoryCategory.FURNITURE.value,
    )
    quantity_total = models.PositiveIntegerField(default=0)
    quantity_functional = models.PositiveIntegerField(default=0)
    quantity_damaged = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=100, blank=True, default="")
    last_inspected_at = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["hostel", "item_name"]


class HostelStaff(TimeStampedModel):
    """CFR-HM-028, HM-UC-029: Hostel operational staff coordination."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="staff_members")
    name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=[(r.value, r.name) for r in StaffRole],
        default=StaffRole.CLEANER.value,
    )
    phone_number = models.CharField(max_length=20, blank=True, default="")
    shift = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in StaffShift],
        default=StaffShift.MORNING.value,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["hostel", "name"]


class SecurityShift(TimeStampedModel):
    """CFR-HM-029, BR-HM-028: Security guard shift scheduling."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="security_shifts")
    guard_name = models.CharField(max_length=100)
    shift_date = models.DateField(db_index=True)
    shift_type = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in SecurityShiftType],
        default=SecurityShiftType.MORNING.value,
    )
    gate_location = models.CharField(max_length=100, default="Main Gate")
    status = models.CharField(max_length=20, default="scheduled")

    class Meta:
        ordering = ["-shift_date", "hostel"]


class HostelNotice(TimeStampedModel):
    """CFR-HM-030, BR-HM-029..031: Notices and announcement board."""

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(
        max_length=20,
        choices=[(a.value, a.name) for a in NoticeAudience],
        default=NoticeAudience.ALL.value,
    )
    published_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["hostel", "is_active"], name="notice_hostel_active_idx"),
        ]


class HostelNotification(TimeStampedModel):
    """CFR-HM-033, BR-HM-034: Event-triggered status updates and alerts."""

    recipient_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    event_type = models.CharField(
        max_length=50,
        choices=[(e.value, e.name) for e in NotificationEventType],
    )
    is_read = models.BooleanField(default=False, db_index=True)
    link = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["recipient_user_id", "is_read"], name="notification_user_read_idx"),
        ]
