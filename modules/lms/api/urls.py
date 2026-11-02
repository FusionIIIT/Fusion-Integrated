from rest_framework.routers import DefaultRouter

from modules.lms.api.views import (
    AnnouncementViewSet,
    AssignmentViewSet,
    CourseMaterialViewSet,
    CourseMembershipViewSet,
    CourseViewSet,
    FileViewSet,
    GradeViewSet,
    ModuleSectionViewSet,
    ScheduledReleaseViewSet,
    SubmissionViewSet,
)

app_name = "lms"

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"memberships", CourseMembershipViewSet, basename="membership")
router.register(r"sections", ModuleSectionViewSet, basename="section")
router.register(r"materials", CourseMaterialViewSet, basename="material")
router.register(r"announcements", AnnouncementViewSet, basename="announcement")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"submissions", SubmissionViewSet, basename="submission")
router.register(r"grades", GradeViewSet, basename="grade")
router.register(r"scheduled-releases", ScheduledReleaseViewSet, basename="scheduled-release")
router.register(r"files", FileViewSet, basename="file")

urlpatterns = router.urls
