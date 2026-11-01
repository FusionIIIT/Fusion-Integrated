
from django.db import models

from core.db.mixins import TimeStampedModel





class LeaveType(models.Model):

    name = models.CharField(max_length=100)

    description = models.TextField()



    def __str__(self):

        return self.name





class LeaveRequest(TimeStampedModel):

    applicant_user_id = models.IntegerField(db_index=True)

    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(max_length=50, default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):

        return f"{self.applicant_user_id} - {self.leave_type} - {self.status}"





class LeaveBalance(TimeStampedModel):

    user_id = models.IntegerField(db_index=True)

    calendar_year = models.IntegerField()

    category = models.CharField(max_length=10, choices=[

        ('CL', 'Casual Leave'), ('RH', 'Recess Holiday'), ('SCL', 'Special Casual Leave'),

        ('EL', 'Earned Leave'), ('VL', 'Vacation Leave'), ('COL', 'Compensatory Off Leave')

    ])

    credited = models.IntegerField(default=0)

    availed = models.IntegerField(default=0)



    def __str__(self):

        return f"{self.user_id} - {self.calendar_year} - {self.category}"





class SubstituteAssignment(TimeStampedModel):

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)

    substitute_user_id = models.IntegerField()

    status = models.CharField(max_length=20, choices=[

        ('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')

    ])



    def __str__(self):

        return f"{self.leave_request} - {self.substitute_user_id} - {self.status}"





class LeaveAuditTrail(TimeStampedModel):

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)

    actor_user_id = models.IntegerField()

    from_status = models.CharField(max_length=50)

    to_status = models.CharField(max_length=50)

    action = models.CharField(max_length=100)

    comments = models.TextField()



    def __str__(self):

        return f"{self.leave_request} - {self.from_status} -> {self.to_status}"