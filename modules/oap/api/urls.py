from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentLeaveViewSet,
    BonafideRequestViewSet,
    NoDuesRequestViewSet,
    ThesisSupervisorAssignmentViewSet,
    TAAssignmentViewSet,
    AssistantshipClaimViewSet,
    GraduateSeminarRequestViewSet,
    OAPNotificationViewSet,
    OAPAuditTrailViewSet,
)

router = DefaultRouter()
router.register(r'leaves', StudentLeaveViewSet)
router.register(r'bonafides', BonafideRequestViewSet)
router.register(r'no-dues', NoDuesRequestViewSet)
router.register(r'thesis-supervisors', ThesisSupervisorAssignmentViewSet)
router.register(r'ta-assignments', TAAssignmentViewSet)
router.register(r'assistantship-claims', AssistantshipClaimViewSet)
router.register(r'seminars', GraduateSeminarRequestViewSet)
router.register(r'notifications', OAPNotificationViewSet)
router.register(r'audit-trails', OAPAuditTrailViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
