from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet

router = DefaultRouter()
router.register(r'types', LeaveTypeViewSet, basename='leavetype')
router.register(r'balances', LeaveBalanceViewSet, basename='leavebalance')
router.register(r'requests', LeaveRequestViewSet, basename='leaverequest')

urlpatterns = [
    path('', include(router.urls)),
]