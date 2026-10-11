"""Employee Leave Management Models."""


from django.db import models

class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    is_authorized = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    user = models.ForeignKey("directory.User", on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"{self.user} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

class Approval(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    approver = models.ForeignKey("directory.User", on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.approver} approved {self.request}"