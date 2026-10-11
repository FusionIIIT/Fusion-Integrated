from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LeaveBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_leaves = models.IntegerField(default=30)
    leaves_taken = models.IntegerField(default=0)

    def remaining_leaves(self):
        return self.total_leaves - self.leaves_taken

    def __str__(self):
        return f"{self.user} - Balance: {self.remaining_leaves()}"

class LeaveApplication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20)
    status = models.CharField(max_length=15, default="pending")

    def __str__(self):
        return f"{self.user} - {self.leave_type} ({self.status})"

class SubstituteRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    substitute_user = models.ForeignKey(User, related_name="subs", on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=15, default="pending")

    def __str__(self):
        return f"{self.user} -> {self.substitute_user} ({self.status})"

class HolidayCalendar(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()

    def __str__(self):
        return f"{self.name} on {self.date}"

class LeavePolicy(models.Model):
    leave_type = models.CharField(max_length=20)
    duration = models.IntegerField()

    def __str__(self):
        return f"{self.leave_type}: {self.duration} days"
