# entire file content 
from django.contrib import admin
from .models import LeaveApplication

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'leave_type', 'status')
    # ... rest of code
