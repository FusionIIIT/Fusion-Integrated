from rest_framework.routers import DefaultRouter
from django.urls import path, include
from modules.employee_leave_management.api import LeaveTypeViewSet, LeaveApplicationViewSet

router = DefaultRouter()
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-applications', LeaveApplicationViewSet, basename='leave-application')

urlpatterns = [
    path('', include(router.urls)),
]