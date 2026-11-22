from django.urls import path

from . import views as v

app_name = "lms"
urlpatterns = [
    path("courses/", v.Courses.as_view(), name="courses"),
    path("courses/<int:pk>/", v.CourseDetail.as_view(), name="course"),
    path("courses/<int:pk>/policy/", v.Policy.as_view(), name="policy"),
    path("courses/<int:pk>/policy-versions/", v.PolicyVersions.as_view(), name="policy-versions"),
    path("courses/<int:pk>/sections/", v.Sections.as_view(), name="sections"),
    path("sections/<int:pk>/", v.SectionDetail.as_view(), name="section"),
    path("courses/<int:pk>/materials/", v.Materials.as_view(), name="materials"),
    path("materials/<int:pk>/", v.MaterialDetail.as_view(), name="material"),
    path("materials/<int:pk>/publish/", v.MaterialPublish.as_view(), name="material-publish"),
    path("materials/<int:pk>/withdraw/", v.MaterialWithdraw.as_view(), name="material-withdraw"),
    path("materials/<int:pk>/download/", v.MaterialDownload.as_view(), name="material-download"),
    path("courses/<int:pk>/announcements/", v.Announcements.as_view(), name="announcements"),
    path("courses/<int:pk>/assignments/", v.Assignments.as_view(), name="assignments"),
    path("assignments/<int:pk>/", v.AssignmentDetail.as_view(), name="assignment"),
    path("assignments/<int:pk>/publish/", v.AssignmentPublish.as_view(), name="assignment-publish"),
    path(
        "assignments/<int:pk>/withdraw/", v.AssignmentWithdraw.as_view(), name="assignment-withdraw"
    ),
    path(
        "assignments/<int:pk>/download/", v.AssignmentDownload.as_view(), name="assignment-download"
    ),
    path("assignments/<int:pk>/submissions/", v.Submissions.as_view(), name="submissions"),
    path("submissions/<int:pk>/", v.SubmissionDetail.as_view(), name="submission"),
    path(
        "submissions/<int:pk>/download/", v.SubmissionDownload.as_view(), name="submission-download"
    ),
    path("submissions/<int:pk>/grade/", v.SubmissionGrade.as_view(), name="submission-grade"),
    path("submissions/<int:pk>/grade/release/", v.GradeRelease.as_view(), name="grade-release"),
    path("courses/<int:pk>/grades/", v.Grades.as_view(), name="grades"),
]
