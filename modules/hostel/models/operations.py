"""Hostel operations models.
Includes attendance, leaves, complaints, fines, notices, inventory, security.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hostel.models.hostels import Hostel


class StudentAttendance(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("ON_LEAVE", "On Leave"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PRESENT")
    marked_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hostel_student_attendance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "date"],
                name="hostel_attendance_user_date_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["hostel", "date"], name="attend_hostel_date_idx"),
            models.Index(fields=["user_id", "date"], name="attend_user_date_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} - {self.date}: {self.status}"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    action_by_user_id = models.IntegerField(null=True, blank=True)
    action_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_user_status_idx"),
            models.Index(fields=["hostel", "status"], name="leave_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave u{self.user_id} ({self.status})"


class HostelComplaint(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("LOGGED", "Logged"),
        ("IN_PROGRESS", "In Progress"),
        ("ESCALATED", "Escalated"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="LOGGED")
    assigned_to_user_id = models.IntegerField(null=True, blank=True)
    resolution_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_complaint"
        indexes = [
            models.Index(fields=["user_id", "status"], name="complaint_user_status_idx"),
            models.Index(fields=["hostel", "status"], name="complaint_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Complaint #{self.pk} u{self.user_id} ({self.status})"


class GuestRoomBooking(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("REQUESTED", "Requested"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_bookings")
    guest_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    check_in = models.DateField()
    check_out = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="REQUESTED")
    action_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_guest_room_booking"
        indexes = [
            models.Index(fields=["user_id", "status"], name="guest_user_status_idx"),
            models.Index(fields=["hostel", "status"], name="guest_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"GuestRoom u{self.user_id} for {self.guest_name} ({self.status})"


class ExtendedStayRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="extended_stays")
    reason = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_compliant = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBMITTED")
    action_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hostel_extended_stay_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="ext_user_status_idx"),
            models.Index(fields=["hostel", "status"], name="ext_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"ExtendedStay u{self.user_id} ({self.status})"


class HostelFine(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("IMPOSED", "Imposed"),
        ("PAID", "Paid"),
        ("WAIVED", "Waived"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="IMPOSED")
    imposed_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hostel_fine"
        indexes = [
            models.Index(fields=["user_id", "status"], name="fine_user_status_idx"),
            models.Index(fields=["hostel", "status"], name="fine_hostel_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Fine u{self.user_id} Rs.{self.amount} ({self.status})"


class HostelInventory(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventories")
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=50, default="Good")

    class Meta:
        db_table = "hostel_inventory"
        indexes = [
            models.Index(fields=["hostel", "item_name"], name="inventory_hostel_item_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.item_name} x{self.quantity} @ {self.hostel.code}"


class SecurityShift(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="security_shifts")
    guard_name = models.CharField(max_length=100)
    shift_time = models.CharField(max_length=50)
    shift_date = models.DateField(db_index=True)

    class Meta:
        db_table = "hostel_security_shift"
        indexes = [
            models.Index(fields=["hostel", "shift_date"], name="shift_hostel_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.guard_name} ({self.shift_time}) @ {self.hostel.code}"


class HostelNotice(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=200)
    body = models.TextField()
    topic = models.CharField(max_length=50, default="general")
    published_by_user_id = models.IntegerField()
    published_by_role = models.CharField(max_length=50)

    class Meta:
        db_table = "hostel_notice"
        indexes = [
            models.Index(fields=["hostel", "-created_at"], name="notice_hostel_recent_idx"),
        ]

    def __str__(self) -> str:
        return f"Notice: {self.title} @ {self.hostel.code}"
