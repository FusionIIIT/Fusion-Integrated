"""URLs for the LMS module."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.lms.api.views import (
    AnnouncementViewSet,
    AssignmentViewSet,
    CourseMaterialViewSet,
    CourseWorkspaceView,
    GradeSubmissionView,
    MyGradeView,
    MySubmissionView,
    PublishAssignmentView,
    ReleaseGradeView,
    SubmitAssignmentView,
)

router = DefaultRouter()
router.register(
    r"courses/(?P<course_id>[^/.]+)/materials", CourseMaterialViewSet,
    basename="material",
)
router.register(
    r"courses/(?P<course_id>[^/.]+)/announcements", AnnouncementViewSet,
    basename="announcement",
)
router.register(
    r"courses/(?P<course_id>[^/.]+)/assignments", AssignmentViewSet,
    basename="assignment",
)

urlpatterns = [
    path("courses/<int:course_id>/", CourseWorkspaceView.as_view(), name="course-workspace"),
    path("courses/<int:course_id>/assignments/<int:aid>/publish/",
         PublishAssignmentView.as_view(), name="assignment-publish"),
    path("courses/<int:course_id>/assignments/<int:aid>/submit/",
         SubmitAssignmentView.as_view(), name="assignment-submit"),
    path("courses/<int:course_id>/assignments/<int:aid>/my-submission/",
         MySubmissionView.as_view(), name="my-submission"),
    path("courses/<int:course_id>/assignments/<int:aid>/submissions/<int:sid>/grade/",
         GradeSubmissionView.as_view(), name="grade-submission"),
    path("courses/<int:course_id>/assignments/<int:aid>/submissions/<int:sid>/release-grade/",
         ReleaseGradeView.as_view(), name="release-grade"),
    path("courses/<int:course_id>/assignments/<int:aid>/my-grade/",
         MyGradeView.as_view(), name="my-grade"),
    path("", include(router.urls)),
]
