from django.db import models
from django.contrib.auth.models import User

class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class EmployeeLeave(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date}"

class LeaveRequest(models.Model):
    employee = models.ForeignKey(EmployeeLeave, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    request_date = models.DateField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.employee.user.username} - {self.leave_type.name} - {self.request_date}"

class LeaveApproval(models.Model):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE)
    approval_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.leave_request.employee.user.username} - {self.leave_request.leave_type.name} - {self.approval_date}"