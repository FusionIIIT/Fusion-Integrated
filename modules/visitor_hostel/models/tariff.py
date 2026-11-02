from django.db import models

class Tariff(models.Model):
    CATEGORY_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    ROOM_TYPE_CHOICES = [('Single', 'Single'), ('Double', 'Double'), ('Suite', 'Suite'), ('Non-suite', 'Non-suite')]

    category = models.CharField(max_length=2, choices=CATEGORY_CHOICES)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "vh_tariff"
        unique_together = ('category', 'room_type', 'effective_from')
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.category} - {self.room_type}: {self.rate} from {self.effective_from}"
