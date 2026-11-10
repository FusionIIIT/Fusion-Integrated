"""Celery discovers tasks here. Each lane defines its tasks in
`modules/vms/jobs/<lane>.py`; importing them registers them."""
from modules.vms.schedule import job_modules

JOB_MODULES = job_modules()
