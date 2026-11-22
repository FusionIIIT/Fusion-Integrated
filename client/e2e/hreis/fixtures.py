"""Synthetic fixtures restricted to disposable HR-EIS browser databases."""
# ruff: noqa: E402 -- Standalone fixtures must initialize Django before ORM imports.

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django

django.setup()

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from modules.hreis.models import EmployeeServiceRecord, HRPolicyVersion, HRRequest, LeaveLedgerEntry
from modules.hreis.services.notifications import (
    create_pending_action_reminders,
    create_policy_deadline_notifications,
)

if (
    not settings.DEBUG
    or os.environ.get("HREIS_E2E_SYNTHETIC") != "1"
    or not str(settings.DATABASES["default"]["NAME"]).startswith("hreis_e2e_")
):
    raise SystemExit("Refusing fixtures outside an explicitly disposable hreis_e2e_ database.")

now = timezone.now()
if sys.argv[1] == "seed":
    if HRPolicyVersion.objects.exists() or EmployeeServiceRecord.objects.exists():
        raise SystemExit("Refusing to seed a nonempty HR-EIS database.")
    ids = json.loads(sys.argv[2])
    routes = [{"employee_kind": kind, "department": "CSE",
               "authorities": ["HOD (CSE)", "Registrar"]} for kind in ("staff", "faculty")]
    for family in ("leave", "appraisal", "ltc", "cpda"):
        parameters = {"routes": routes}
        if family == "leave":
            parameters["eligibility"] = {
                kind: {"Casual": True, "Medical": False} for kind in ("staff", "faculty")
            }
            parameters["conditions"] = {
                "pending_reminder_after_hours": 1,
                "reminder_recipients": {"HOD (CSE)": [ids["hrReviewer"]]},
                "policy_notice_at": (now - timedelta(minutes=1)).isoformat(),
                "policy_notice_recipients": [ids["hrEmployee"]],
            }
        if family == "appraisal":
            parameters["submission_window"] = {
                "start": (now - timedelta(days=1)).isoformat(),
                "end": (now + timedelta(days=1)).isoformat(),
            }
        policy = HRPolicyVersion.objects.create(
            family=family, version=1, effective_from=now - timedelta(hours=1),
            parameters=parameters, approved_by_user_id=900099,
            approved_designation="hradmin",
        )
        if family == "leave":
            LeaveLedgerEntry.objects.create(
                user_id=ids["hrEmployee"], leave_type="Casual", quantity="20",
                policy_version=policy, actor_user_id=900099, event_key="synthetic-e2e-opening",
            )
    EmployeeServiceRecord.objects.create(
        user_id=ids["hrEmployee"], department="CSE", designation_snapshot="SYNTHETIC STAFF",
        appointment_details={"source": "disposable synthetic E2E"}, service_history=[],
    )
    call_command("seed_modules", verbosity=0)
    print("Seeded synthetic HR-EIS policies and employee; no institutional defaults.")
elif sys.argv[1] == "events":
    row = HRRequest.objects.get(pk=int(sys.argv[2]), family="leave", state="pending_authority")
    HRRequest.objects.filter(pk=row.pk).update(updated_at=now - timedelta(hours=2))
    state = (row.state, row.version, row.route_step)
    reminders = create_pending_action_reminders()
    notices = create_policy_deadline_notifications()
    assert reminders == 1 and notices == 1, (reminders, notices)
    assert create_pending_action_reminders() == 0
    assert create_policy_deadline_notifications() == 0
    row.refresh_from_db()
    assert (row.state, row.version, row.route_step) == state
    print("Generated one reminder and policy notice; reruns idempotent; workflow unchanged.")
else:
    raise SystemExit("Expected seed or events.")
