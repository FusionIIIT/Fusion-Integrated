
from django.contrib import admin

from .models import (
    EmployeeOfficeAssignment,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Office,
    OfficeApprover,
)


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(EmployeeOfficeAssignment)
class EmployeeOfficeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user_id", "office", "is_active", "updated_at")
    list_filter = ("office", "is_active")
    search_fields = ("user_id", "office__name", "office__code")


@admin.register(OfficeApprover)
class OfficeApproverAdmin(admin.ModelAdmin):
    list_display = ("user_id", "office", "is_active", "updated_at")
    list_filter = ("office", "is_active")
    search_fields = ("user_id", "office__name", "office__code")


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "type_code")
    search_fields = ("name", "type_code")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user_id", "leave_type", "current_balance")
    list_filter = ("leave_type",)
    search_fields = ("user_id",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "office",
        "leave_type",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = ("office", "leave_type", "status")
    search_fields = ("user_id", "approver_id")
