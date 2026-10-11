from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.elm.domain import rules
from modules.elm.models import (
    Account, Application, EmployeeConfiguration, HolidayCalendar, Policy, WorkflowTask,
)
from modules.elm.services import workflow as w


def validate_routes(data):
    for category, steps in data["routes"].items():
        if category not in rules.CATEGORIES or not steps:
            raise DomainError("Each route must belong to a supported leave category.")
        stages = [step["stage"] for step in steps]
        director = (data["designation"] == "Director" and len(steps) == 1
                    and steps[0]["user_id"] == data["user_id"] and steps[0]["role"] == "Director")
        expected = ["sanction"] if director else (["unit_head"] if category in ("CL", "RH")
                                                    else ["unit_head", "sanction"])
        if not director and category not in ("CL", "RH") and "establishment" in stages:
            expected = ["unit_head", "establishment", "sanction"]
        if stages != expected:
            raise DomainError("Route stages must follow the applicable Unit Head/Establishment/final sanction path.")
        for step in steps:
            w.employee(step["user_id"])
            if step["user_id"] == data["user_id"] and not director:
                raise DomainError("Only the Director-specific sanction path may assign the applicant.")
            if step["stage"] == "unit_head" and step["role"] != "Unit Head":
                raise DomainError("Unit Head steps require the Unit Head designation.")
            if step["stage"] == "establishment" and step["role"] != "Deputy Registrar (Estt.)":
                raise DomainError("Establishment steps require Deputy Registrar (Estt.).")
            if step["stage"] == "sanction" and step["role"] not in rules.AUTHORITY_ROLES:
                raise DomainError("Configure a competent named sanctioning authority.")
            if step.get("escalation_user_id"):
                w.employee(step["escalation_user_id"])
                if step["escalation_user_id"] == data["user_id"] and not director:
                    raise DomainError("Escalation cannot assign the applicant to process their own leave.")
                if step.get("reassign_on_escalation") and step.get("escalation_role") != step["role"]:
                    raise DomainError("Responsibility escalation must preserve the workflow stage's designation.")
        if category not in data["eligible_categories"]:
            raise DomainError("A route can be configured only for an eligible category.")
    if set(data["eligible_categories"]) != set(data["routes"]):
        raise DomainError("Every eligible category needs a complete route.")


@transaction.atomic
def save_configuration(actor, data):
    # EL-UC-014/018, BR-EL-030/038: current configuration, no policy publication lifecycle.
    w.require(actor, "elm.configuration.manage")
    if "policy" in data:
        values = data["policy"]
        if values["reminder_hours"] >= values["escalation_hours"]:
            raise DomainError("The escalation threshold must exceed the reminder threshold.")
        Policy.objects.update_or_create(pk=1, defaults=values)
    if "employee" in data:
        values = data["employee"]
        w.employee(values["user_id"])
        validate_routes(values)
        EmployeeConfiguration.objects.update_or_create(user_id=values["user_id"], defaults=values)


@transaction.atomic
def save_calendar(actor, data):
    # EL-UC-015, BR-EL-031: only publish replaces an effective calendar.
    w.require(actor, "elm.configuration.manage")
    for values in (data["holidays"], data["restricted_holidays"]):
        if any(date.fromisoformat(day).year != data["year"] for day in values):
            raise DomainError("Every calendar date must belong to its selected year.")
    if data.get("published"):
        # Lock the policy singleton to serialize calendar replacement, including a first publish.
        Policy.objects.select_for_update().get(pk=w.current_policy().pk)
        HolidayCalendar.objects.filter(year=data["year"], published=True).update(published=False)
    return HolidayCalendar.objects.create(**data)


@transaction.atomic
def offline_entry(actor, data):
    # EL-UC-016, BR-EL-029/037: recorded existing sanction; no workflow task created.
    w.require(actor, "elm.record.manage")
    config = w.locked_configuration(data["user_id"])
    if not data["offline_reference"].strip() or not data["unavailability_reason"].strip():
        raise DomainError("Provide the existing sanction reference and why ELM was unavailable.")
    values = {k: v for k, v in data.items() if k not in ("unavailability_reason", "authority_id", "authority_role")}
    app = Application(**values, status="approved", effective_end_date=data["end_date"],
                      final_authority_id=data["authority_id"], final_authority_role=data["authority_role"])
    if not any(step["user_id"] == data["authority_id"] and step["role"] == data["authority_role"]
               for step in w.route_for(app, config) if step["stage"] in ("sanction", "unit_head")):
        raise DomainError("The recorded sanction must identify the configured competent authority.")
    app.days_by_year = w.validate(app, config, check_substitute=False)
    app.save()
    for year, amount in sorted(app.days_by_year.items()):
        w.post(w.account_for(app.user_id, int(year)), app, app.category, -Decimal(amount),
               "offline_sync", f"offline:{app.pk}:{year}")
    w.audit(app, actor, "offline_sync", "not_recorded", data["unavailability_reason"])
    w.notify(app.user_id, app, f"Offline-sanctioned leave #{app.pk} has been recorded.")
    return app


@transaction.atomic
def correct_reference(actor, application_id, reason, reference):
    # EL-UC-017/BR-EL-037: narrow metadata correction cannot alter sanction or balances.
    w.require(actor, "elm.record.manage")
    app = w.locked_application(actor, application_id)
    if not reason.strip() or not app.offline_reference:
        raise DomainError("A correction reason and an existing offline record are required.")
    app.offline_reference = reference
    app.save()
    w.audit(app, actor, "correct_reference", app.status, reason)
    return app


@transaction.atomic
def process_account_year(user_id, year):
    # EL-UC-020, BR-EL-002–009: each account's rollover is atomic and replay-safe.
    w.locked_configuration(user_id)
    account = Account.objects.select_for_update().filter(user_id=user_id, year=year).first()
    if account is None or account.year_end_processed:
        return False
    if timezone.localdate().year <= year:
        raise ConflictError("The calendar year has not ended.")
    pending = Application.objects.filter(user_id=user_id, start_date__year__lte=year,
                                         status__in=rules.PENDING).exists()
    unreviewed = Application.objects.filter(user_id=user_id, kind="leave", status="approved",
                                            category__in=rules.CONTINUOUS, resumption_reviewed=False,
                                            start_date__year__lte=year).exists()
    if pending or unreviewed:
        raise ConflictError("Resolve pending requests and review resumptions before closing this account.")
    next_account = w.account_for(user_id, year + 1)
    for category in ("EL", "COL"):
        amount = getattr(account, category.lower())
        if amount:
            w.post(next_account, None, category, amount, "carry_forward", f"carry:{account.pk}:{category}")
    if account.employee_kind == "faculty" and account.vl:
        w.post(next_account, None, "EL", account.vl / 2, "vl_conversion", f"vl_convert:{account.pk}")
    for category in rules.CATEGORIES:
        amount = getattr(account, category.lower())
        if amount:
            w.post(account, None, category, -amount, "year_end", f"close:{account.pk}:{category}")
    account.year_end_processed = True
    account.save()
    return True


def process_year_end(year):
    result = {"processed": 0, "exceptions": []}
    for user_id in Account.objects.filter(year=year, year_end_processed=False).values_list("user_id", flat=True):
        try:
            result["processed"] += int(process_account_year(user_id, year))
        except DomainError as exc:
            result["exceptions"].append({"account_user_id": user_id, "code": exc.code, "message": str(exc)})
    return result


@transaction.atomic
def process_task_sla(task_id, now):
    observed = WorkflowTask.objects.filter(pk=task_id).values("application_id").first()
    if observed is None:
        return 0
    app = Application.objects.get(pk=observed["application_id"])
    w.locked_configuration(app.user_id, app.substitute_id)
    app = Application.objects.select_for_update().get(pk=app.pk)
    task = WorkflowTask.objects.select_for_update().get(pk=task_id)
    if not task.pending or app.status not in rules.PENDING:
        return 0
    policy = w.current_policy()
    age_hours = (now - task.created_at).total_seconds() / 3600
    issued = 0
    if age_hours >= policy.reminder_hours and task.reminded_at is None:
        w.notify(task.user_id, app, f"Reminder: request #{app.pk} awaits your action.")
        task.reminded_at = now
        w.audit(app, None, "sla_reminder", app.status)
        issued += 1
    if age_hours >= policy.escalation_hours and task.escalated_at is None and task.escalation_user_id:
        w.notify(task.escalation_user_id, app, f"SLA escalation: request #{app.pk} awaits action.")
        if task.reassign_on_escalation:
            task.user_id = task.escalation_user_id
            task.role = task.escalation_role
            app.revision += 1
            app.save()
            w.notify(task.user_id, app, f"Request #{app.pk} is now assigned to you after escalation.")
        task.escalated_at = now
        w.audit(app, None, "sla_escalation", app.status)
        issued += 1
    task.save()
    return issued


def process_sla(now=None):
    # EL-UC-021, BR-EL-032/033: recheck pending under locks at each threshold.
    now = now or timezone.now()
    return sum(process_task_sla(i, now) for i in WorkflowTask.objects.filter(pending=True)
               .values_list("pk", flat=True))
