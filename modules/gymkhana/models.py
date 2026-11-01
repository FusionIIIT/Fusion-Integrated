"""Gymkhana tables. User ids are IAM ids: plain integers, never foreign keys."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain import CATEGORIES, OPEN


class Club(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=16, choices=[(c, c) for c in CATEGORIES])
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, default=OPEN)
    coordinator_user_id = models.IntegerField()
    co_coordinator_user_id = models.IntegerField()
    faculty_councillor_user_id = models.IntegerField()
    created_by_user_id = models.IntegerField()


class Membership(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, default=OPEN)
    remarks = models.CharField(max_length=300, blank=True)
