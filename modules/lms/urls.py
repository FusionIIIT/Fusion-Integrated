from django.urls import path
from . import views

urlpatterns = [
    path("courses/", views.course_list, name="lms-course-list"),

    path(
        "courses/<int:course_id>/materials/",
        views.course_materials,
        name="lms-course-materials"
    ),

    path(
        "courses/<int:course_id>/assignments/",
        views.course_assignments,
        name="lms-course-assignments"
    ),
]