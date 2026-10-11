from django.db import models

class Employee(models.Model):
    """
    Model representing an Employee
    """
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class LeaveType(models.Model):
    """
    Model representing Leave Types
    """
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=200)

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    """
    Model representing Leave Balances
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"

class LeaveApplication(models.Model):
    """
    Model representing Leave Applications
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')])
    approver = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='approver_set')
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} - {self.status}"

    class Meta:
        verbose_name_plural = 'Leave Applications'