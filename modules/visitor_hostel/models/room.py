from django.db import models

class RoomDetail(models.Model):
    ROOM_TYPE_CHOICES = [('Single', 'Single'), ('Double', 'Double'), ('Suite', 'Suite'), ('Non-suite', 'Non-suite')]
    STATUS_CHOICES = [('Available', 'Available'), ('Occupied', 'Occupied'), ('Maintenance', 'Maintenance'), ('Blocked', 'Blocked')]

    room_number = models.CharField(max_length=20, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='Single')
    capacity = models.PositiveIntegerField(default=1)
    floor = models.IntegerField(default=1)
    is_operational = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "vh_room_detail"
        ordering = ["room_number"]

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type} - {self.status})"
