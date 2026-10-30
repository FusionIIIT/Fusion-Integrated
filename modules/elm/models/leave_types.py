from django.db import models


class LeaveType(models.Model):
    code = models.CharField(max_length=10, primary_key=True)  # CL, RH, SCL, EL, COL, VL
    name = models.CharField(max_length=50)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=2)
    carry_forward = models.BooleanField(default=False)
    continuous_counting = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(models.Model):
    user_id = models.IntegerField()  # Maps to Principal.user_id
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    balance = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ("user_id", "leave_type", "year")

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type.code} - {self.year}: {self.balance}"


class HolidayCalendar(models.Model):
    date = models.DateField(unique=True)
    is_holiday = models.BooleanField(default=False)
    rh_type = models.CharField(max_length=20, blank=True, default="")  # e.g., 'RH', 'PUBLIC'

    def __str__(self):
        return f"{self.date} - {self.is_holiday} ({self.rh_type})"
