"""Hostel Management models.

Operational HM data belongs in fusion_integrated.
Stores people only as integer user_id. No cross-module foreign keys.
Occupancy source of truth: derived from active RoomAssignment rows.
"""
from django.db import models
from django.utils import timezone


class Hostel(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_hostel"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class HostelRoleBinding(models.Model):
    ROLE_KINDS = (
        ("warden", "Warden"),
        ("caretaker", "Caretaker"),
    )

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField(db_index=True)
    role_kind = models.CharField(max_length=20, choices=ROLE_KINDS, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_hostel_role_binding"
        ordering = ["-created_at"]


class Room(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_room"
        unique_together = ("hostel", "room_number")
        ordering = ["hostel", "room_number"]

    def __str__(self) -> str:
        return f"{self.hostel.code}-{self.room_number}"

    @property
    def occupied_count(self) -> int:
        return self.assignments.filter(status="active").count()

    @property
    def available_capacity(self) -> int:
        return max(0, self.capacity - self.occupied_count)


class AccommodationRequest(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("allotted", "Allotted"),
        ("cancelled", "Cancelled"),
    )

    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True, related_name="accommodation_requests")
    preferred_room_type = models.CharField(max_length=50, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_accommodation_request"
        ordering = ["-created_at"]


class RoomAssignment(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("vacated", "Vacated"),
        ("exchanged", "Exchanged"),
    )

    user_id = models.IntegerField(db_index=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_room_assignment"
        ordering = ["-created_at"]


class AttendanceRecord(models.Model):
    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(db_index=True)
    is_present = models.BooleanField(default=True)
    recorded_by_user_id = models.IntegerField()
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hm_attendance_record"
        ordering = ["-date", "-created_at"]


class LeaveRequest(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    )

    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_leave_request"
        ordering = ["-created_at"]


class Complaint(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("updated", "Updated"),
        ("escalated", "Escalated"),
        ("resolved", "Resolved"),
    )

    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_complaint"
        ordering = ["-created_at"]


class ComplaintEvent(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="events")
    actor_user_id = models.IntegerField()
    actor_kind = models.CharField(max_length=20)
    event = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hm_complaint_event"
        ordering = ["created_at"]


class GuestBooking(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    )

    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_bookings")
    guest_name = models.CharField(max_length=100)
    relation = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_guest_booking"
        ordering = ["-created_at"]


class ExtendedStayRequest(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    )

    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="extended_stay_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_extended_stay_request"
        ordering = ["-created_at"]


class FineRecord(models.Model):
    user_id = models.IntegerField(db_index=True)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    imposed_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hm_fine_record"
        ordering = ["-created_at"]


class InventoryItem(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventory_items")
    name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    description = models.TextField(blank=True, default="")
    updated_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_inventory_item"
        ordering = ["name"]


class InventoryEvent(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="events")
    quantity_change = models.IntegerField()
    reason = models.TextField(blank=True, default="")
    recorded_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "hm_inventory_event"
        ordering = ["-created_at"]


class GuardShift(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guard_shifts")
    guard_name = models.CharField(max_length=100)
    shift_date = models.DateField(db_index=True)
    shift_type = models.CharField(max_length=50)  # e.g., Day / Night
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_guard_shift"
        ordering = ["-shift_date"]


class Notice(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("withdrawn", "Withdrawn"),
    )

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hm_notice"
        ordering = ["-created_at"]
