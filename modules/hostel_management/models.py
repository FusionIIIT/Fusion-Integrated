from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True
        app_label = "hostel_management"


class Hostel(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    total_capacity = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class HostelRoleBinding(BaseModel):
    ROLES = [("warden", "Warden"), ("caretaker", "Caretaker")]
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField()  # IAM reference
    role = models.CharField(max_length=20, choices=ROLES)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Room(BaseModel):
    STATUS_CHOICES = [("available", "Available"), ("full", "Full"), ("maintenance", "Maintenance")]
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(default=2)
    current_occupancy = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")

    def __str__(self):
        return f"{self.hostel.code} - Room {self.room_number}"


class AccommodationRequest(BaseModel):
    STATUS_CHOICES = [("submitted", "Submitted"), ("allotted", "Allotted"), ("rejected", "Rejected")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="accommodation_requests")
    preferred_room_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    allotted_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    application_date = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class RoomAllocationHistory(BaseModel):
    ACTIONS = [("allotment", "Allotment"), ("reallotment", "Re-allotment"), ("exchange", "Exchange"), ("vacation", "Vacation")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTIONS)
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AttendanceRecord(BaseModel):
    STATUS = [("present", "Present"), ("absent", "Absent")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS)
    marked_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class LeaveRequest(BaseModel):
    STATUS = [("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    supporting_info = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="submitted")
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class HostelComplaint(BaseModel):
    STATUS = [("submitted", "Submitted"), ("resolved", "Resolved"), ("escalated_to_warden", "Escalated to Warden")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(max_length=50)
    description = models.TextField()
    attachment_url = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default="submitted")
    action_taken = models.TextField(blank=True)
    updated_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GuestRoomBooking(BaseModel):
    STATUS = [("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guest_bookings")
    guest_name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS, default="submitted")
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ExtendedStayRequest(BaseModel):
    STATUS = [("submitted", "Submitted"), ("approved", "Approved"), ("rejected", "Rejected")]
    COMPLIANCE = [("pending", "Pending"), ("compliant", "Compliant"), ("non_compliant", "Non-compliant")]
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="extended_stays")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    payment_deadline = models.DateField(null=True, blank=True)
    compliance_status = models.CharField(max_length=20, choices=COMPLIANCE, default="pending")
    status = models.CharField(max_length=20, choices=STATUS, default="submitted")
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class HostelFine(BaseModel):
    student_id = models.IntegerField()
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="fines")
    reason = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField()
    imposed_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class HostelInventory(BaseModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="inventory_items")
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    condition = models.CharField(max_length=50, default="good")
    last_updated_by_id = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)


class InventoryLog(BaseModel):
    inventory = models.ForeignKey(HostelInventory, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=50)
    quantity_change = models.IntegerField()
    logged_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class SecurityGuardShift(BaseModel):
    SHIFTS = [("morning", "Morning"), ("evening", "Evening"), ("night", "Night")]
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="guard_shifts")
    guard_name = models.CharField(max_length=100)
    shift = models.CharField(max_length=20, choices=SHIFTS)
    date = models.DateField()
    assigned_by_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class HostelNotice(BaseModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by_id = models.IntegerField()
    posted_by_role = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(BaseModel):
    recipient_id = models.IntegerField()
    event_type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
