from django.db import models

class BookingDetail(models.Model):
    BILLING_CHOICES = [('Visitor', 'Visitor'), ('Indenter', 'Indenter'), ('Institute', 'Institute'), ('Project', 'Project')]
    STATUS_CHOICES = [
        ('DRAFT', 'DRAFT'), ('PENDING', 'PENDING'), ('FORWARDED', 'FORWARDED'),
        ('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED'), ('ROOM_ALLOTTED', 'ROOM_ALLOTTED'),
        ('CHECKED_IN', 'CHECKED_IN'), ('CHECKED_OUT', 'CHECKED_OUT'),
        ('CANCELLATION_REQUESTED', 'CANCELLATION_REQUESTED'), ('CANCELLED', 'CANCELLED'),
    ]

    booking_id = models.CharField(max_length=32, unique=True, db_index=True)
    indenter = models.CharField(max_length=100)
    visitor = models.ForeignKey('VisitorDetail', on_delete=models.CASCADE, related_name="bookings")
    booking_from = models.DateField()
    booking_to = models.DateField()
    category = models.CharField(max_length=2, default='B')
    billing_responsibility = models.CharField(max_length=20, choices=BILLING_CHOICES, default='Visitor')
    project_code = models.CharField(max_length=50, blank=True, null=True)
    purpose = models.TextField()
    is_offline = models.BooleanField(default=False)
    offline_contact_person = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vh_booking_detail"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_id} - {self.indenter} ({self.status})"

class RoomAllotment(models.Model):
    booking = models.ForeignKey(BookingDetail, on_delete=models.CASCADE, related_name="allotments")
    room = models.ForeignKey('RoomDetail', on_delete=models.PROTECT, related_name="allotments")
    allotted_from = models.DateField()
    allotted_to = models.DateField()
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_room_allotment"

    def __str__(self):
        return f"{self.booking.booking_id} -> Room {self.room.room_number}"
