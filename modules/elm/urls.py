from django.urls import path, include
from rest_framework import routers
from .views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet

router = routers.DefaultRouter()
router.register(r'leave_types', LeaveTypeViewSet)
router.register(r'leave_balances', LeaveBalanceViewSet)
router.register(r'leave_requests', LeaveRequestViewSet)

urlpatterns = [
    path('', include(router.urls)),
]   

