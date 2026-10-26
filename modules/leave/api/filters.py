"""API filters for Leave Management."""
import django_filters
from ..models import (
    EmployeeType,
    HolidayCalendar,
    LeaveBalance,
    LeaveCategory,
    LeavePolicy,
    LeaveRequest,
    LeaveStatus,
    OfflineLeaveEntry,
    SubstituteRequest,
)


class LeaveRequestFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter()
    category = django_filters.ChoiceFilter(choices=LeaveCategory.choices)
    status = django_filters.ChoiceFilter(choices=LeaveStatus.choices)
    start_date_after = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_date_before = django_filters.DateFilter(field_name="start_date", lookup_expr="lte")
    end_date_after = django_filters.DateFilter(field_name="end_date", lookup_expr="gte")
    end_date_before = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")
    substitute_id = django_filters.NumberFilter()
    year = django_filters.NumberFilter(field_name="start_date", lookup_expr="year")

    class Meta:
        model = LeaveRequest
        fields = ["user_id", "category", "status", "substitute_id"]


class LeaveBalanceFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter()
    category = django_filters.ChoiceFilter(choices=LeaveCategory.choices)
    year = django_filters.NumberFilter()

    class Meta:
        model = LeaveBalance
        fields = ["user_id", "category", "year"]


class SubstituteRequestFilter(django_filters.FilterSet):
    substitute_id = django_filters.NumberFilter()
    status = django_filters.ChoiceFilter(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")])

    class Meta:
        model = SubstituteRequest
        fields = ["substitute_id", "status"]


class HolidayCalendarFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter()
    is_restricted = django_filters.BooleanFilter()
    date_after = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_before = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = HolidayCalendar
        fields = ["year", "is_restricted"]


class LeavePolicyFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=LeaveCategory.choices)
    employee_type = django_filters.ChoiceFilter(choices=EmployeeType.choices)
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = LeavePolicy
        fields = ["category", "employee_type", "is_active"]


class OfflineLeaveEntryFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter()
    category = django_filters.ChoiceFilter(choices=LeaveCategory.choices)
    year = django_filters.NumberFilter(field_name="start_date", lookup_expr="year")

    class Meta:
        model = OfflineLeaveEntry
        fields = ["user_id", "category"]