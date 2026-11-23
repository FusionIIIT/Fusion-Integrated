from django.db import models

from core.db.mixins import TimeStampedModel


class StoredFile(TimeStampedModel):
    workspace = models.ForeignKey("lms.CourseWorkspace", on_delete=models.PROTECT)
    owner_user_id = models.IntegerField()
    storage_key = models.CharField(max_length=160, unique=True)
    name = models.CharField(max_length=200)
    mime_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
