"""Task routing and schedule configuration."""
TASK_ROUTES = {'modules.leave_elm.tasks.check_sla_tasks': {'queue': 'default'}, 'modules.leave_elm.tasks.process_year_end_leave_accounts': {'queue': 'default'}}

BEAT_SCHEDULE = {'leave_elm.check_sla_tasks': {'task': 'modules.leave_elm.tasks.check_sla_tasks', 'schedule': 3600.0}, 'leave_elm.process_year_end_leave_accounts': {'task': 'modules.leave_elm.tasks.process_year_end_leave_accounts', 'schedule': 86400.0}}
