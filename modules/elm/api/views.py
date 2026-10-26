from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import HolidayCalendar, LeaveApplication, LeavePolicy
from .serializers import (
    HolidayCalendarSerializer,
    LeaveApplicationSerializer,
    LeaveApplicationWriteSerializer,
    LeavePolicySerializer,
)


class LeavePolicyViewSet(ModelViewSet):
    queryset = LeavePolicy.objects.filter(is_active=True).order_by("leave_type", "effective_from")
    serializer_class = LeavePolicySerializer


class HolidayCalendarViewSet(ModelViewSet):
    queryset = HolidayCalendar.objects.all().order_by("holiday_date")
    serializer_class = HolidayCalendarSerializer


class LeaveApplicationViewSet(ModelViewSet):
    """Leave application viewset."""

    queryset = LeaveApplication.objects.select_related("unit").order_by("-created_at")
    serializer_class = LeaveApplicationSerializer

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return LeaveApplicationWriteSerializer
        return LeaveApplicationSerializer

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request, *args, **kwargs):
        counts = self.get_queryset().aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
            approved=Count("id", filter=Q(status="approved")),
            rejected=Count("id", filter=Q(status="rejected")),
        )
        return Response({
            "total": counts["total"] or 0,
            "pending": counts["pending"] or 0,
            "approved": counts["approved"] or 0,
            "rejected": counts["rejected"] or 0,
        })
