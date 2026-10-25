from django.contrib import admin

from modules.leave.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveResumption,
    LeaveSLAConfig,
    LeaveType,
    RestrictedHoliday,
)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "max_days_per_year", "requires_attachment", "is_active")
    search_fields = ("code", "name")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user_id", "leave_type", "year", "allocated_days", "used_days")
    list_filter = ("year", "leave_type")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_id",
        "leave_type",
        "start_date",
        "end_date",
        "status",
        "approver_user_id",
    )
    list_filter = ("status", "leave_type")
    search_fields = ("reason",)


@admin.register(RestrictedHoliday)
class RestrictedHolidayAdmin(admin.ModelAdmin):
    list_display = ("year", "date", "name", "is_published")
    list_filter = ("year", "is_published")


@admin.register(LeaveResumption)
class LeaveResumptionAdmin(admin.ModelAdmin):
    list_display = ("id", "leave_request", "actual_resumption_date", "status", "adjustment_days")


@admin.register(LeaveSLAConfig)
class LeaveSLAConfigAdmin(admin.ModelAdmin):
    list_display = ("reminder_days", "escalation_days", "is_active")
