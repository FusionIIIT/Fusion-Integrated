from django.db import models
from core.models import TimeStampedModel

class Course(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.title

class Module(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField()

    def __str__(self):
        return self.title

class Lesson(TimeStampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField()

    def __str__(self):
        return self.title
