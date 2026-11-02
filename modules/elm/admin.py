"""Admin interface for ELM models."""
from django.contrib import admin

from modules.elm.models import (
    HolidayCalendar,
    LeaveAccountTransaction,
    LeaveBalance,
    LeaveRequest,
    LeaveTransitionHistory,
)


@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "holiday_type", "year", "is_published")
    list_filter = ("year", "holiday_type", "is_published")
    search_fields = ("name",)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("user_id", "year", "category", "credited_balance", "carried_forward", "availed_balance", "available_balance")
    list_filter = ("year", "category")
    search_fields = ("user_id",)


@admin.register(LeaveAccountTransaction)
class LeaveAccountTransactionAdmin(admin.ModelAdmin):
    list_display = ("user_id", "year", "category", "transaction_type", "days", "created_at")
    list_filter = ("year", "category", "transaction_type")
    search_fields = ("user_id",)


class LeaveTransitionHistoryInline(admin.TabularInline):
    model = LeaveTransitionHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "actor_user_id", "remarks", "created_at")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "category", "start_date", "end_date", "days_calculated", "status", "created_at")
    list_filter = ("status", "category", "is_half_day")
    search_fields = ("user_id", "reason")
    inlines = [LeaveTransitionHistoryInline]
