from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveApplicationViewSet, LeaveBalanceViewSet,
    OfflineLeaveRecordViewSet, SLAConfigViewSet
)

router = DefaultRouter()
router.register(r'applications', LeaveApplicationViewSet, basename='leave-application')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'offline-records', OfflineLeaveRecordViewSet, basename='offline-record')
router.register(r'sla-configs', SLAConfigViewSet, basename='sla-config')

urlpatterns = [
    path('', include(router.urls)),
]
