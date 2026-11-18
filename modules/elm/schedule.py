"""What this module needs run on a timer.

ELM currently has no recurring background timers or scheduled tasks.
Exports empty BEAT_SCHEDULE and TASK_ROUTES to satisfy the platform contract.
"""

TASK_ROUTES: dict[str, dict] = {}

BEAT_SCHEDULE: dict[str, dict] = {}
