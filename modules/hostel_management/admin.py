from django.contrib import admin
from .models import Hostel, Room, StudentAllocation, LeaveRequest

admin.site.register(Hostel)
admin.site.register(Room)
admin.site.register(StudentAllocation)
admin.site.register(LeaveRequest)
