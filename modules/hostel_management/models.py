from django.db import models
from django.contrib.auth.models import User

class Hostel(models.Model):
    hostel_name = models.CharField(max_length=100)
    total_capacity = models.IntegerField()
    caretaker = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.hostel_name

class Room(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=50)
    room_capacity = models.IntegerField()
    vacant_beds = models.IntegerField()

    def __str__(self):
        return f"{self.hostel.hostel_name} - {self.room_number}"

class StudentAllocation(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    allocation_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.username} - {self.room.room_number}"

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.student.username} - {self.start_date} to {self.end_date}"
