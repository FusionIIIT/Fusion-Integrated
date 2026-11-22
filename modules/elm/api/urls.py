# ELM API URL configuration
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from modules.elm.views import (
    LeaveTypeViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeavePolicyViewSet,
)

router = DefaultRouter()
router.register(r'types', LeaveTypeViewSet)
router.register(r'balances', LeaveBalanceViewSet)
router.register(r'requests', LeaveRequestViewSet)
router.register(r'policies', LeavePolicyViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
