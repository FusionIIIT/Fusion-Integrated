from datetime import timedelta
from celery.schedules import crontab

BEAT_SCHEDULE = {
    'cms_process_sla': {
        'task': 'modules.complaint_cms.tasks.cms_process_sla',
        'schedule': 900,  # 15 minutes
        'options': {'expires': 8640},  # 24 hours
    },
    'cms_auto_close_resolved': {
        'task': 'modules.complaint_cms.tasks.cms_auto_close_resolved',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
        'options': {'expires': 3600},  # 1 hour
    }
}

TASK_ROUTES = {
    'modules.complaint_cms.tasks.*': {'queue': 'default'}
}