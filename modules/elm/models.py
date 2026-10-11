from django.db import models


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]
    CATEGORY_CHOICES = [
        ("cl", "Casual Leave"),
        ("rh", "Restricted Holiday"),
        ("scl", "Special Casual Leave"),
        ("el", "Earned Leave"),
        ("vl", "Faculty Vacation Leave"),
        ("col", "Commuted Leave"),
    ]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    substitute_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} - {self.category} - {self.status}"
