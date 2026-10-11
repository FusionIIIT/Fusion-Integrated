from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.elm.domain import rules
from modules.elm.models import (
    Account, Application, AttendanceOutbox, AuditEntry, EmployeeConfiguration,
    HolidayCalendar, LedgerEntry, Notification, Policy, WorkflowTask,
)
from modules.elm.selectors.queries import applications_for


def require(actor, permission):
    # BR-EL-036, including callers outside HTTP.
    if actor is None or not actor.has_module("elm") or not actor.has_permission(permission):
        raise PermissionDeniedError()


def employee(user_id):
    person = directory.get_users([user_id]).get(user_id)
    if person is None or person.kind not in ("faculty", "staff"):
        raise DomainError("An active faculty or staff IAM employee is required.", code="not_employee")
    return person


def current_policy():
    policy = Policy.objects.first()
    if policy is None:
        raise DomainError("A Leave Administrator must configure the current policy first.", code="policy_missing")
    return policy


def configuration_for(user_id):
    config = EmployeeConfiguration.objects.filter(user_id=user_id).first()
    if config is None:
        raise DomainError("Configure the employee's leave eligibility and hierarchy first.", code="hierarchy_missing")
    return config


def locked_configuration(user_id, substitute_id=None):
    ids = sorted({i for i in (user_id, substitute_id) if i is not None})
    configs = {r.user_id: r for r in EmployeeConfiguration.objects.select_for_update()
               .filter(user_id__in=ids).order_by("user_id")}
    if any(i not in configs for i in ids):
        raise DomainError("Configure each employee's leave eligibility and hierarchy first.", code="hierarchy_missing")
    return configs[user_id]


def account_for(user_id, year):
    person = employee(user_id)
    account, _ = Account.objects.get_or_create(
        user_id=user_id, year=year,
        defaults={"employee_kind": person.kind,
                  **{c.lower(): v for c, v in rules.entitlements(person.kind).items()}},
    )
    return Account.objects.select_for_update().get(pk=account.pk)


def calendars_for(start, end):
    return {r.year: {"holidays": r.holidays, "restricted_holidays": r.restricted_holidays}
            for r in HolidayCalendar.objects.filter(year__gte=start.year, year__lte=end.year,
                                                     published=True)}


def count(category, start, end, half="full"):
    try:
        return rules.count_days(category, start, end, half, calendars_for(start, end),
                                current_policy().non_working_weekdays)
    except rules.RuleViolation as exc:
        raise DomainError(str(exc), code=exc.code) from exc


def check_overlap(user_id, start, end, half="full", exclude_ids=()):
    # BR-EL-012/014: pending extensions also reserve their incremental intervals.
    rows = Application.objects.filter(user_id=user_id, kind__in=("leave", "extension"),
                                      status__in=(*rules.PENDING, "approved"),
                                      start_date__lte=end, effective_end_date__gte=start)
    rows = rows.exclude(pk__in=exclude_ids)
    for row in rows:
        if rules.overlaps(start, end, half, row.start_date, row.effective_end_date, row.half):
            raise ConflictError("The employee has overlapping pending or approved leave.", code="leave_overlap")


def validate(application, config, *, exclude_ids=(), check_substitute=True):
    # BR-EL-001, BR-EL-006, BR-EL-009, BR-EL-013–015, BR-EL-030.
    person = employee(application.user_id)
    policy = current_policy()
    if application.category not in config.eligible_categories:
        raise DomainError("This category is not enabled for this employee.", code="category_ineligible")
    if application.category == "VL":
        if person.kind != "faculty":
            raise DomainError("VL is available only to faculty.", code="category_ineligible")
        provider = getattr(settings, "ELM_VACATION_PERIODS_PROVIDER", "")
        if not provider:
            raise DomainError("The Academic Calendar vacation provider is unavailable.", code="vacation_calendar_unavailable")
        periods = import_string(provider)([application.user_id], application.start_date, application.end_date)
        if not all(any(a <= day <= b for a, b in periods.get(application.user_id, []))
                   for day in rules.dates(application.start_date, application.end_date)):
            raise DomainError("VL must fall within Academic Calendar vacation periods.", code="outside_vacation")
    if application.category == "COL" and policy.require_col_evidence and not application.medical_reference:
        raise DomainError("Provide the required medical evidence reference.", code="medical_evidence_required")
    if not application.reason.strip() or (application.station_leave and not application.station_details.strip()):
        raise DomainError("Provide a reason and station details when outside Jabalpur.", code="details_required")
    amounts = count(application.category, application.start_date, application.end_date, application.half)
    check_overlap(application.user_id, application.start_date, application.end_date, application.half, exclude_ids)
    for year, amount in sorted(amounts.items()):
        account = account_for(application.user_id, year)
        if getattr(account, application.category.lower()) < amount:
            raise DomainError(f"Insufficient {application.category} balance for {year}.", code="insufficient_balance")
    if config.coverage_required and check_substitute:
        validate_substitute(application)
    return {str(y): str(v) for y, v in amounts.items()}


def validate_substitute(application):
    if not application.substitute_id or application.substitute_id == application.user_id:
        raise DomainError("Nominate exactly one other employee as substitute.", code="invalid_substitute")
    employee(application.substitute_id)
    configuration_for(application.substitute_id)
    check_overlap(application.substitute_id, application.start_date, application.end_date)


def notify(user_id, application, message):
    Notification.objects.create(user_id=user_id, application=application, message=message)


def audit(application, actor, action, previous, reason=""):
    AuditEntry.objects.create(application=application, actor_id=getattr(actor, "user_id", None),
                              action=action, reason=reason, from_status=previous, to_status=application.status)


def assign(application, step):
    # BR-EL-035: durable in-app assignment notification in the same transaction.
    task = WorkflowTask.objects.create(
        application=application, user_id=step["user_id"], role=step["role"], stage=step["stage"],
        escalation_user_id=step.get("escalation_user_id"), escalation_role=step.get("escalation_role", ""),
        reassign_on_escalation=step.get("reassign_on_escalation", False),
    )
    application.status = task.stage
    application.save()
    notify(task.user_id, application, f"Leave request #{application.pk}: a {task.stage} task is assigned to you.")


def route_for(application, config):
    # BR-EL-016–020, BR-EL-030: route selected from current per-employee configuration.
    route = config.routes.get(application.category, [])
    if not route:
        raise DomainError("Configure the applicable sanctioning route.", code="hierarchy_missing")
    return route


def begin_route(application, config):
    application.route = route_for(application, config)
    application.route_index = 0
    assign(application, application.route[0])


@transaction.atomic
def submit(*, actor, data):
    require(actor, "elm.application.self")
    config = locked_configuration(actor.user_id, data.get("substitute_id"))
    app = Application(user_id=actor.user_id, effective_end_date=data["end_date"], **data)
    app.days_by_year = validate(app, config)
    app.route = route_for(app, config)
    app.save()
    if config.coverage_required:
        substitute = employee(app.substitute_id)
        assign(app, {"stage": "substitute", "user_id": app.substitute_id, "role": substitute.kind})
    else:
        begin_route(app, config)
    audit(app, actor, "submit", "not_submitted")
    return app


def locked_application(actor, application_id):
    # Scope first gives the same 404 for nonexistent and foreign IDs.
    app = applications_for(actor).filter(pk=application_id).first()
    if app is None:
        raise NotFoundError()
    locked_configuration(app.user_id, app.substitute_id)
    return Application.objects.select_for_update().get(pk=app.pk)


def post(account, application, category, delta, operation, event_key):
    # Unique ledger keys plus row locks prevent duplicate deductions/refunds.
    if LedgerEntry.objects.filter(event_key=event_key).exists():
        return
    field = category.lower()
    amount = getattr(account, field) + delta
    if amount < 0:
        raise DomainError("The leave account cannot cover this adjustment.", code="insufficient_balance")
    setattr(account, field, amount)
    account.save(update_fields=[field, "updated_at"])
    LedgerEntry.objects.create(account=account, application=application, category=category,
                               delta=delta, operation=operation, event_key=event_key)


def apply_final(app, task):
    previous = None
    if app.kind in ("cancellation", "extension", "resumption"):
        previous = Application.objects.select_for_update().get(pk=app.parent_id)
        if previous.status != "approved":
            raise ConflictError("The original leave is no longer approved.")
    if app.kind == "cancellation":
        # BR-EL-023: eligibility rechecked at final decision, not just at creation.
        if timezone.localdate() >= previous.start_date:
            raise ConflictError("Cancellation is available only before leave begins.", code="leave_started")
        entries = LedgerEntry.objects.filter(application__in=[previous, *previous.changes.filter(kind="extension", status="approved")])
        totals = {}
        for entry in entries:
            key = (entry.account_id, entry.category)
            totals[key] = totals.get(key, Decimal("0")) + entry.delta
        for (account_id, category), delta in sorted(totals.items()):
            account = Account.objects.select_for_update().get(pk=account_id)
            post(account, app, category, -delta, "cancellation", f"cancellation:{app.pk}:{account_id}:{category}")
        previous.status = "cancelled"
        previous.save()
    elif app.kind == "resumption":
        # BR-EL-028: the supplied baseline explicitly compares to the approved end date.
        old = count(previous.category, previous.start_date, previous.effective_end_date, previous.half)
        new = count(previous.category, previous.start_date, app.end_date, previous.half)
        check_overlap(app.user_id, previous.start_date, app.end_date, previous.half,
                      [previous.pk, *previous.changes.values_list("pk", flat=True)])
        for year in sorted(set(old) | set(new)):
            account = account_for(app.user_id, year)
            delta = old.get(year, Decimal("0")) - new.get(year, Decimal("0"))
            if delta:
                post(account, app, app.category, delta, "resumption", f"resumption:{app.pk}:{year}")
        previous.effective_end_date = app.end_date
        previous.resumption_reviewed = True
        previous.save()
        AttendanceOutbox.objects.create(application=app, payload={
            "event": "elm.resumption.reviewed", "user_id": app.user_id,
            "leave_id": previous.pk, "start_date": previous.start_date.isoformat(),
            "actual_end_date": app.end_date.isoformat(),
        })
    else:
        excludes = [app.pk]
        if previous:
            if previous.resumption_reviewed:
                raise ConflictError("Leave with reviewed resumption cannot be extended.")
            if app.start_date != previous.effective_end_date + timedelta(days=1):
                raise ConflictError("The extension must begin after the current approved end.", code="invalid_extension")
            excludes.append(previous.pk)
        app.days_by_year = validate(app, configuration_for(app.user_id), exclude_ids=excludes)
        for year, amount in sorted(app.days_by_year.items()):
            post(account_for(app.user_id, int(year)), app, app.category, -Decimal(amount),
                 "approval", f"approval:{app.pk}:{year}")
        if previous:
            previous.effective_end_date = app.end_date
            previous.save()
    app.final_authority_id = task.user_id
    app.final_authority_role = task.role


@transaction.atomic
def act(*, actor, application_id, action, revision, reason=""):
    require(actor, "elm.task.act")
    app = locked_application(actor, application_id)
    if app.revision != revision or app.status not in rules.PENDING:
        raise ConflictError("This request changed. Refresh before acting.", code="stale_request")
    task = WorkflowTask.objects.select_for_update().filter(application=app, pending=True,
                                                           user_id=actor.user_id, role=actor.active_role).first()
    if task is None:
        raise NotFoundError()
    if actor.user_id == app.user_id and not (task.role == "Director" and task.stage == "sanction"):
        raise PermissionDeniedError("You cannot process or approve your own leave.", code="self_approval")
    if action not in rules.allowed_decisions(task.stage, app.category, app.kind):
        raise ConflictError("That decision is not available at this workflow stage.", code="invalid_transition")
    if action in ("reject", "not_recommend", "decline") and not reason.strip():
        raise DomainError("Provide a reason for this decision.", code="reason_required")
    previous = app.status
    task.pending = False
    task.save()
    if action == "decline":
        app.status = "applicant_action"
        notify(app.user_id, app, "The substitute declined. Nominate a replacement or withdraw.")
    elif action == "accept":
        validate_substitute(app)
        begin_route(app, configuration_for(app.user_id))
    elif action in ("recommend", "not_recommend", "forward"):
        route = route_for(app, configuration_for(app.user_id))
        position = next((i for i, step in enumerate(route) if step["stage"] == task.stage), None)
        if position is None or position + 1 >= len(route):
            raise DomainError("The current routing configuration is incomplete.", code="hierarchy_missing")
        app.route = route
        app.route_index = position + 1
        assign(app, route[position + 1])
    elif action in ("approve", "review"):
        apply_final(app, task)
        app.status = "reviewed" if app.kind == "resumption" else "approved"
        notify(app.user_id, app, f"Your {app.kind} request #{app.pk} was {app.status}.")
    else:
        app.status = "rejected"
        notify(app.user_id, app, f"Your {app.kind} request #{app.pk} was rejected.")
    app.revision += 1
    app.save()
    audit(app, actor, action, previous, reason)
    return app


@transaction.atomic
def withdraw(*, actor, application_id, revision):
    # BR-EL-022, BR-EL-034; CW-EL-01/03.
    require(actor, "elm.application.self")
    app = locked_application(actor, application_id)
    if app.user_id != actor.user_id:
        raise NotFoundError()
    if app.revision != revision or app.status not in rules.PENDING or app.kind not in ("leave", "extension"):
        raise ConflictError("Only a pending new leave or extension can be withdrawn.")
    previous = app.status
    for task in WorkflowTask.objects.select_for_update().filter(application=app, pending=True):
        task.pending = False
        task.save()
        notify(task.user_id, app, f"Request #{app.pk} was withdrawn; the assigned task ended.")
    app.status = "withdrawn"
    app.revision += 1
    app.save()
    audit(app, actor, "withdraw", previous)
    return app


@transaction.atomic
def replace_substitute(*, actor, application_id, revision, substitute_id):
    # EL-UC-019, BR-EL-015: this changes the consent assignment, not submitted leave details.
    require(actor, "elm.application.self")
    app = locked_application(actor, application_id)
    locked_configuration(app.user_id, substitute_id)
    if app.user_id != actor.user_id:
        raise NotFoundError()
    if app.revision != revision or app.status != "applicant_action":
        raise ConflictError("Replacement is available only after a substitute declines.")
    app.substitute_id = substitute_id
    validate_substitute(app)
    assign(app, {"stage": "substitute", "user_id": substitute_id, "role": employee(substitute_id).kind})
    app.revision += 1
    app.save()
    audit(app, actor, "replace_substitute", "applicant_action")
    return app


@transaction.atomic
def lifecycle(*, actor, application_id, kind, reason, end_date=None, substitute_id=None):
    require(actor, "elm.application.self")
    parent = locked_application(actor, application_id)
    if parent.user_id != actor.user_id:
        raise NotFoundError()
    if parent.kind != "leave" or parent.status != "approved":
        raise ConflictError("Select an approved original leave application.")
    if parent.changes.filter(status__in=rules.PENDING).exists():
        raise ConflictError("Another lifecycle request is still pending.")
    today = timezone.localdate()
    start = parent.start_date
    end = parent.effective_end_date
    config = locked_configuration(actor.user_id, substitute_id)
    if kind == "cancellation":
        if today >= start:
            raise ConflictError("Cancellation is available only before leave begins.")
    elif kind == "extension":
        if parent.category not in rules.CONTINUOUS or not start <= today <= end or parent.resumption_reviewed:
            raise ConflictError("Only ongoing EL, COL, or VL can be extended.")
        if end_date is None or end_date <= end:
            raise DomainError("Enter an end date later than the current approved end.")
        start, end = end + timedelta(days=1), end_date
    elif kind == "resumption":
        if parent.category not in rules.CONTINUOUS or parent.resumption_reviewed:
            raise ConflictError("Resumption review is available once for EL, COL, or VL.")
        if end_date is None or not start <= end_date <= today:
            raise DomainError("Enter the actual return date between leave start and today.")
        end = end_date
    else:
        raise DomainError("Choose cancellation, extension, or resumption.")
    app = Application(user_id=actor.user_id, parent=parent, kind=kind, category=parent.category,
                      start_date=start, end_date=end, effective_end_date=end, reason=reason,
                      half=parent.half, station_leave=parent.station_leave,
                      station_details=parent.station_details, medical_reference=parent.medical_reference,
                      substitute_id=substitute_id)
    if not reason.strip():
        raise DomainError("Provide a reason or resumption details.")
    if kind == "extension":
        app.days_by_year = validate(app, config, exclude_ids=[parent.pk])
    app.save()
    if kind == "resumption":
        if not parent.final_authority_id or not parent.final_authority_role:
            raise DomainError("The original sanctioning authority is not recorded.")
        assign(app, {"stage": "sanction", "user_id": parent.final_authority_id,
                     "role": parent.final_authority_role})
    elif kind == "extension" and config.coverage_required:
        assign(app, {"stage": "substitute", "user_id": substitute_id,
                     "role": employee(substitute_id).kind})
    else:
        begin_route(app, config)
    audit(app, actor, f"request_{kind}", "not_submitted", reason)
    return app


@transaction.atomic
def ensure_current_account(actor):
    require(actor, "elm.application.self")
    locked_configuration(actor.user_id)
    return account_for(actor.user_id, timezone.localdate().year)


@transaction.atomic
def mark_notification_read(actor, notification_id):
    require(actor, "elm.notification.self")
    updated = Notification.objects.filter(pk=notification_id, user_id=actor.user_id).update(read=True)
    if not updated:
        raise NotFoundError()
