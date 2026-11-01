from django.urls import path
from modules.lms.api import views

app_name = "lms"

urlpatterns = [
    # Courses
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/<int:course_id>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:course_id>/roster/", views.CourseRosterView.as_view(), name="course_roster"),

    # Course Materials
    path("courses/<int:course_id>/materials/", views.CourseMaterialListView.as_view(), name="course_materials"),
    path("materials/<int:material_id>/", views.CourseMaterialDetailView.as_view(), name="material_detail"),

    # Announcements
    path("courses/<int:course_id>/announcements/", views.CourseAnnouncementListView.as_view(), name="course_announcements"),
    path("announcements/<int:announcement_id>/", views.CourseAnnouncementDetailView.as_view(), name="announcement_detail"),
    path("announcements/", views.AllAnnouncementsView.as_view(), name="all_announcements"),

    # Assignments
    path("courses/<int:course_id>/assignments/", views.CourseAssignmentListView.as_view(), name="course_assignments"),
    path("assignments/", views.AllAssignmentsView.as_view(), name="all_assignments"),
    path("assignments/<int:assignment_id>/", views.AssignmentDetailView.as_view(), name="assignment_detail"),
    path("assignments/<int:assignment_id>/publish/", views.AssignmentPublishView.as_view(), name="assignment_publish"),
    path("assignments/<int:assignment_id>/submit/", views.AssignmentSubmitView.as_view(), name="assignment_submit"),
    path("assignments/<int:assignment_id>/my-submission/", views.MyAssignmentSubmissionView.as_view(), name="my_submission"),
    path("assignments/<int:assignment_id>/submissions/", views.AssignmentSubmissionsListView.as_view(), name="assignment_submissions"),

    # Grading & Auditing
    path("submissions/<int:submission_id>/grade/", views.GradeSubmissionView.as_view(), name="grade_submission"),
    path("assignments/<int:assignment_id>/release-grades/", views.ReleaseGradesView.as_view(), name="release_grades"),
    path("grades/my-grades/", views.MyGradesListView.as_view(), name="my_grades"),
    path("grades/<int:grade_id>/audit/", views.GradeAuditListView.as_view(), name="grade_audit"),

    # Scheduled event-triggered releases
    path("process-scheduled-releases/", views.ProcessScheduledReleasesView.as_view(), name="process_releases"),
]
