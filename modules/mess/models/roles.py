from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class MessRoleAssignment(TimeStampedModel, UserScopedModel):
    ROLE_CHOICES = [
        ("CARETAKER", "Caretaker"),
        ("WARDEN", "Warden"),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    employee_user_id = models.IntegerField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mess_role_assignment"
        constraints = [
            models.CheckConstraint(check=Q(ends_at__gt=F('starts_at')), name='ends_at_greater_than_starts_at'),
            models.Index(name='mess_role_assignment_role_starts_at', fields=['role', 'starts_at'])
        ]

    def __str__(self):
        return f"MessRoleAssignment for {self.role} by {self.assigned_by_user_id} on {self.starts_at}"
