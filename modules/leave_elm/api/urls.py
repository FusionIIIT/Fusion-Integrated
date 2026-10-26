from django.urls import path
from rest_framework.routers import DefaultRouter
from modules.leave_elm.api.views import (
    LeaveTypeViewSet,
    LeaveBalanceViewSet,
    LeaveApplicationViewSet,
    HolidayCalendarViewSet,
    YearEndConversionView,
)

router = DefaultRouter()
router.register(r'types', LeaveTypeViewSet, basename='leave-type')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'applications', LeaveApplicationViewSet, basename='leave-application')
router.register(r'holidays', HolidayCalendarViewSet, basename='holiday-calendar')

urlpatterns = [
    *router.urls,
    path('convert-vl-to-el/', YearEndConversionView.as_view(), name='convert-vl-to-el'),
]
