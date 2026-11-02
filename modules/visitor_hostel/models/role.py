from django.db import models
from .booking import BookingDetail

class VHRoleAssignment(models.Model):
    ROLE_CHOICES = [('Caretaker', 'Caretaker'), ('VH In-Charge', 'VH In-Charge')]

    user = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "vh_role_assignment"

    def __str__(self):
        return f"{self.user} -> {self.role} ({'Active' if self.active else 'Inactive'})"

class StayException(models.Model):
    EXCEPTION_CHOICES = [('No-Show', 'No-Show'), ('Overstay', 'Overstay')]

    booking = models.ForeignKey(BookingDetail, on_delete=models.CASCADE, related_name="exceptions")
    exception_type = models.CharField(max_length=20, choices=EXCEPTION_CHOICES)
    remarks = models.TextField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_stay_exception"

    def __str__(self):
        return f"{self.exception_type} on {self.booking.booking_id}"
