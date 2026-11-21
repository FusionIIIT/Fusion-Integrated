from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ComplaintViewSet,
    ComplaintFeedbackViewSet,
    ComplaintAnnouncementViewSet,
    CmsRoleAssignmentViewSet,
)

router = DefaultRouter()
router.register(r"complaints", ComplaintViewSet, basename="complaints")
router.register(r"feedback", ComplaintFeedbackViewSet, basename="feedback")
router.register(r"announcements", ComplaintAnnouncementViewSet, basename="announcements")
router.register(r"roles", CmsRoleAssignmentViewSet, basename="roles")

urlpatterns = [
    path("", include(router.urls)),
]
