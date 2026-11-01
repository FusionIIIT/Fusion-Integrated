from django.contrib import admin
from .models import (
    Course,
    CourseMembership,
    CourseMaterial,
    Announcement,
    Assignment,
    Submission,
    Grade,
)

admin.site.register(Course)
admin.site.register(CourseMembership)
admin.site.register(CourseMaterial)
admin.site.register(Announcement)
admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(Grade)