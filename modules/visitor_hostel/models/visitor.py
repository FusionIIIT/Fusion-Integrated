from django.db import models

class VisitorDetail(models.Model):
    CATEGORY_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    designation = models.CharField(max_length=100, blank=True, null=True)
    organization = models.CharField(max_length=150, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES, default='B')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_visitor_detail"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.category})"
