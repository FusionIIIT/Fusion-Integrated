"""Celery tasks for LMS scheduled releases."""
from celery import shared_task

from modules.lms.services import (
    release_scheduled_assignments,
    release_scheduled_materials,
)


@shared_task
def release_scheduled_materials_task():
    return release_scheduled_materials()


@shared_task
def release_scheduled_assignments_task():
    return release_scheduled_assignments()
