"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module. Empty until the SLA reminder and
escalation tasks exist.
"""
TASK_ROUTES = {}

BEAT_SCHEDULE = {}
