from django.urls import path, include
from .views import LeavePolicyViewSet, HolidayCalendarViewSet


urlpatterns = [
    path("policies/", LeavePolicyViewSet.as_view(), name="policies"),
    path("holidays/", HolidayCalendarViewSet.as_view(), name="holidays"),
]
