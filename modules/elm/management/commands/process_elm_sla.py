"""Scheduled SLA threshold processing for ELM (EL-UC-021).

EL-UC-021 is event-triggered: "configured reminder or escalation threshold
reached". Nothing in this codebase delivers a per-task timer event, so the
trigger is realised as a periodic sweep that finds the tasks whose thresholds
have been crossed since the last pass. The decision logic is identical either
way -- `domain/sla.evaluate_task` is given a task and a clock reading -- so
moving to a real scheduler later changes only the caller.

Run it from cron or the platform scheduler:

    python manage.py process_elm_sla
    python manage.py process_elm_sla --dry-run
    python manage.py process_elm_sla --seed-defaults
"""
from django.core.management.base import BaseCommand

from modules.elm.services.sla import (
    load_threshold_map,
    process_sla_thresholds,
    seed_default_thresholds,
)


class Command(BaseCommand):
    help = "Process SLA reminder and escalation thresholds for ELM workflow tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Evaluate and report without sending, rerouting, or logging.",
        )
        parser.add_argument(
            "--seed-defaults",
            action="store_true",
            help="Create seed thresholds for any task kind that has none, then exit.",
        )
        parser.add_argument(
            "--task-id",
            type=int,
            action="append",
            dest="task_ids",
            help="Process only this task id. Repeatable.",
        )

    def handle(self, *args, **options):
        if options["seed_defaults"]:
            created = seed_default_thresholds()
            self.stdout.write(self.style.SUCCESS(f"Seeded {created} SLA configuration row(s)."))
            return

        configured = load_threshold_map()
        if not configured:
            self.stdout.write(
                self.style.WARNING(
                    "No SLA thresholds are configured, so no task can be reminded or escalated. "
                    "Configure them in Leave > SLA Settings, or run with --seed-defaults."
                )
            )
            return

        if options["dry_run"]:
            # Evaluate without side effects by reusing the same code path with
            # logging disabled and a rollback. Kept explicit rather than
            # threading a `dry_run` flag through the service, which would mean
            # the real path and the rehearsal path diverge.
            from django.db import transaction

            try:
                with transaction.atomic():
                    counters = process_sla_thresholds(log_suppressed=False)
                    raise _Rollback(counters)
            except _Rollback as rb:
                counters = rb.counters
            self.stdout.write(f"[dry-run] {counters}")
            return

        counters = process_sla_thresholds(task_ids=options.get("task_ids"))
        self.stdout.write(
            self.style.SUCCESS(
                "SLA pass complete: "
                f"{counters['evaluated']} evaluated, "
                f"{counters['reminded']} reminded, "
                f"{counters['escalated']} escalated "
                f"({counters['rerouted']} rerouted), "
                f"{counters['suppressed']} suppressed."
            )
        )


class _Rollback(Exception):
    """Carries the counters out of the aborted dry-run transaction."""

    def __init__(self, counters):
        super().__init__("dry run rollback")
        self.counters = counters
