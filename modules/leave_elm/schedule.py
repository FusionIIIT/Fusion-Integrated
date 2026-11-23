from celery.schedules import crontab

BEAT_SCHEDULE = {
    'elm-year-end-rollover': {
        'task': 'modules.leave_elm.tasks.elm_year_end_rollover',
        'schedule': crontab(month_of_year=1, day_of_month=1, hour=0, minute=0)
    },
    'elm-task-sla': {
        'task': 'modules.leave_elm.tasks.elm_task_sla',
        'schedule': crontab(minute='*/15')
    }
}

TASK_ROUTES = {
    'modules.leave_elm.tasks.*': {'queue': 'default'}
}