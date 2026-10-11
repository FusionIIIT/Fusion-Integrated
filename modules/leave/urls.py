from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveApplicationViewSet, LeaveTypeViewSet
LeaveBalanceViewSet

router = DefaultRouter()
router.register(r'leave-applications', LeaveApplicationViewSet)
router.register(r'leave-types', LeaveTypeViewSet)
router.register(r'leave-balances', LeaveBalanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]