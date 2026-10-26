from django.contrib import admin

from modules.elm.models import (
    LeaveApprovalTask,
    LeaveAuthorityRule,
    LeaveBalance,
    LeaveBalanceEvent,
    LeaveCalendar,
    LeaveCalendarDate,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestEvent,
)


class LeaveCalendarDateInline(admin.TabularInline):
    model = LeaveCalendarDate
    extra = 0


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "leave_type_code", "employee_kinds", "annual_entitlement",
        "day_counting", "carries_forward", "is_active",
    )
    list_filter = ("is_active", "day_counting", "carries_forward")
    search_fields = ("leave_type_code",)


@admin.register(LeaveCalendar)
class LeaveCalendarAdmin(admin.ModelAdmin):
    list_display = (
        "label", "kind", "year", "revision", "status",
        "effective_from", "effective_through",
    )
    list_filter = ("kind", "year", "status")
    inlines = (LeaveCalendarDateInline,)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "user_id", "leave_type_code", "year", "opening_balance",
        "annual_credit", "used_days", "reserved_days", "available_days",
    )
    list_filter = ("year", "leave_type_code")
    search_fields = ("user_id",)


@admin.register(LeaveBalanceEvent)
class LeaveBalanceEventAdmin(admin.ModelAdmin):
    list_display = (
        "balance", "request", "event_type", "amount",
        "actor_user_id", "created_at",
    )
    list_filter = ("event_type", "created_at")
    readonly_fields = (
        "balance", "request", "event_type", "amount",
        "actor_user_id", "note", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user_id", "leave_type_code", "requested_start_date",
        "requested_end_date", "status", "submitted_at",
    )
    list_filter = ("leave_type_code", "status")
    search_fields = ("user_id",)
    readonly_fields = (
        "user_id", "leave_type_code", "requested_start_date",
        "requested_end_date", "day_part", "total_days", "status",
        "submitted_at", "updated_at", "approved_by_user_id",
        "approved_at", "rejection_reason",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LeaveRequestEvent)
class LeaveRequestEventAdmin(admin.ModelAdmin):
    list_display = (
        "request", "event_type", "from_status", "to_status",
        "actor_user_id", "created_at",
    )
    list_filter = ("event_type", "to_status", "created_at")
    search_fields = ("request_id", "actor_user_id")
    readonly_fields = (
        "request", "event_type", "from_status", "to_status",
        "actor_user_id", "note", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LeaveAuthorityRule)
class LeaveAuthorityRuleAdmin(admin.ModelAdmin):
    list_display = (
        "department",
        "leave_type_code",
        "applicant_role",
        "for_director",
        "step_order",
        "stage",
        "decision_mode",
        "approver_user_id",
        "is_self_sanction",
        "is_active",
    )
    list_filter = ("department", "leave_type_code", "stage", "is_active")
    search_fields = ("department", "applicant_role", "approver_user_id")


@admin.register(LeaveApprovalTask)
class LeaveApprovalTaskAdmin(admin.ModelAdmin):
    list_display = (
        "request",
        "step_order",
        "stage",
        "assignee_user_id",
        "status",
        "assigned_at",
        "decided_at",
    )
    list_filter = ("stage", "status", "assigned_at")
    search_fields = ("request_id", "assignee_user_id")
    readonly_fields = (
        "request",
        "rule",
        "step_order",
        "stage",
        "decision_mode",
        "assignee_user_id",
        "status",
        "assigned_at",
        "decided_at",
        "decision_note",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
