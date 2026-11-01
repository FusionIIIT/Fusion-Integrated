from django.contrib import admin

from modules.elm.models import LeaveCategory, EmployeeLeaveBalance, LeaveApplication, LeaveApplicationTransition, SubstituteNomination


@admin.register(LeaveCategory)
class LeaveCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "entitlement_days", "carry_forward", "continuous_counting"]
    search_fields = ["code", "label"]
    ordering = ["code"]


@admin.register(EmployeeLeaveBalance)
class EmployeeLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["user_id", "leave_category", "remaining_days", "used_days"]
    search_fields = ["user_id", "leave_category__code"]
    list_filter = ["leave_category"]
    ordering = ["user_id", "leave_category__code"]


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user_id", "leave_category", "requested_start",
        "requested_end", "status", "substitute_accepted"
    ]
    list_filter = ["status", "leave_category"]
    search_fields = ["user_id", "leave_category__code", "purpose"]
    ordering = ["-created_at"]


@admin.register(LeaveApplicationTransition)
class LeaveApplicationTransitionAdmin(admin.ModelAdmin):
    list_display = ["application", "from_status", "to_status", "actor_label", "at"]
    list_filter = ["from_status", "to_status", "at"]
    search_fields = ["application__id", "actor_label"]
    ordering = ["-at"]


@admin.register(SubstituteNomination)
class SubstituteNominationAdmin(admin.ModelAdmin):
    list_display = ["application", "substitute_user_id", "accepted", "accepted_at"]
    list_filter = ["accepted"]
    search_fields = ["application__id", "substitute_user_id"]
    ordering = ["-created_at"]