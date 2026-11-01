from celery import shared_task

from modules.lms.services.courses import release_due


@shared_task
def release_scheduled_content():
    return release_due()
