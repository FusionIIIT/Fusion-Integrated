from django.db import models


class LeaveType(models.Model):
    LEAVE_TYPE_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Recreational Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("VL", "Vacation Leave"),
        ("COL", "Compensatory Off Leave"),
    ]
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self) -> str:
        return self.leave_type


class LeaveBalance(models.Model):
    employee_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField()

    class Meta:
        db_table = "elm_leave_balance"

    def __str__(self) -> str:
        return f"Employee {self.employee_id} - {self.leave_type.leave_type} Balance: {self.balance}"


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Consent"),
        ("AWAITING_APPROVAL", "Awaiting Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    ]
    applicant_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    station_leave_details = models.TextField(blank=True, default="")
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="AWAITING_APPROVAL")

    class Meta:
        db_table = "elm_leave_application"

    def __str__(self) -> str:
        return f"Applicant {self.applicant_id} - {self.leave_type.leave_type} Application"


class SubstituteNomination(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending Consent"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_id = models.IntegerField(db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    decline_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_substitute_nomination"

    def __str__(self) -> str:
        return (
            f"Applicant {self.leave_application.applicant_id} - "
            f"{self.leave_application.leave_type.leave_type} Substitute Nomination"
        )
