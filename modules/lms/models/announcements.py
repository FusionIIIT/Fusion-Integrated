from django.db import models

from core.db.mixins import TimeStampedModel


class Announcement(TimeStampedModel):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    content = models.TextField()
    author_user_id = models.IntegerField()
