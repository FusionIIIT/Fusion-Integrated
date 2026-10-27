from django.contrib import admin
from .models import LeaveApplication

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "end_date", "leave_type", "status")
    list_filter = ("status", "leave_type")
    search_fields = ("user__username", "reason")
