from django.contrib import admin

from modules.elm.models import (
    AuditEvent,
    CalendarVersion,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRequest,
    WorkflowTask,
    YearEndRun,
)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "category", "start_date", "end_date", "status")
    list_filter = ("category", "status", "kind")
    search_fields = ("user_id", "purpose")
    readonly_fields = (
        "created_at",
        "updated_at",
        "chargeable_days",
        "policy_version_id",
        "calendar_version_id",
    )


for model in (LeavePolicy, CalendarVersion, WorkflowTask, LeaveLedgerEntry, AuditEvent, YearEndRun):
    admin.site.register(model)
