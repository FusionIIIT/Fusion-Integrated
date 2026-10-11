from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from ..models import LeaveApplication
from .serializers import (
    LeavePolicySerializer,
    HolidayCalendarSerializer,
)


class LeavePolicyViewSet(ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer


class HolidayCalendarViewSet(ModelViewSet):
    queryset = HolidayCalendar.objects.all().order_by("start_date")
    serializer_class = HolidayCalendarSerializer


class LeaveApplicationViewSet(ModelViewSet):
    """Leave application viewset."""

    queryset = LeaveApplication.objects.select_related(
        "employee",
        "unit_head",
        "substitute",
        "approver_chain",
        "latest_decision",
    ).order_by("-created_at")
    serializer_class = None  # Override in router
