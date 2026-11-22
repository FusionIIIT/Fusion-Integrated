from collections.abc import Iterable


def effective_schedules(schedules: Iterable) -> list:
    enabled = [schedule for schedule in schedules if schedule.enabled]
    local_datasets = {
        schedule.dataset_key
        for schedule in enabled
        if schedule.scope == "local"
    }
    return [
        schedule
        for schedule in enabled
        if schedule.scope == "local"
        or schedule.dataset_key not in local_datasets
    ]
