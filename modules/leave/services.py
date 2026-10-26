from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.leave.domain import (
    CATEGORIES,
    ENTITLEMENTS,
    LeaveRuleError,
    chargeable_days,
    conversion_vl_to_el,
    overlaps,
)
from modules.leave.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
    LeaveLedger,
    LeaveNotification,
    LeavePolicy,
    LeaveSlaEvent,
    LeaveTransition,
    SubstituteRequest,
)


def _policy(year):
    return LeavePolicy.objects.filter(year=year).first()


def _calendar(year):
    return HolidayCalendar.objects.filter(year=year, published=True).order_by("-version").first()


def _change(app, state, actor_id=None, reason=""):
    old = app.state
    app.state = state
    app.save(update_fields=["state", "updated_at"])
    LeaveTransition.objects.create(
        application=app, from_state=old, to_state=state, actor_user_id=actor_id, reason=reason
    )
    recipients = {
        "awaiting_substitute": app.substitute_user_id,
        "unit_head_review": app.unit_head_user_id,
        "establishment_routing": app.route.get("establishment_user_id"),
        "final_sanction": app.final_authority_user_id,
        "director_self_sanction": app.user_id,
    }
    recipient = recipients.get(state)
    if recipient is not None:
        LeaveNotification.objects.create(application=app, user_id=recipient,
                                          kind="task_assigned")
    return app


def _account(user_id, year, category, faculty=False):
    policy = _policy(year)
    configured = policy.values.get("entitlements", {}) if policy else {}
    entitlement = Decimal(str(configured.get(category, ENTITLEMENTS[category])))
    defaults = {
        "balance": entitlement if category != "EL" or not faculty else Decimal("0")
    }
    return LeaveAccount.objects.get_or_create(
        user_id=user_id, year=year, category=category,
        defaults={**defaults, "is_faculty": faculty},
    )[0]


def validate_application(
    *,
    actor,
    category,
    start_date,
    end_date,
    half="",
    substitute_user_id=None,
    exclude_application_id=None,
):
    if category not in CATEGORIES:
        raise LeaveRuleError("Unsupported leave category.")
    if start_date > end_date:
        raise LeaveRuleError("Leave end date must not precede its start date.")
    if category == "VL" and getattr(actor, "kind", "") != "faculty":
        raise LeaveRuleError("VL is available only to faculty employees.")
    if category == "EL" and getattr(actor, "kind", "") == "faculty":
        raise LeaveRuleError("EL is available only to non-faculty employees in this baseline.")
    if category == "CL" and half not in ("", "first", "second"):
        raise LeaveRuleError("CL half must be first or second.")
    if category != "CL" and half:
        raise LeaveRuleError("Half-day leave is only available for CL.")
    calendar = _calendar(start_date.year)
    holidays = {date.fromisoformat(h["date"]) for h in (calendar.holidays if calendar else [])}
    if category == "RH":
        valid_rh_dates = {
            date.fromisoformat(h["date"]) for h in (calendar.holidays if calendar else []) if h.get("kind") == "RH"
        }
        requested_dates = [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]
        if any(day not in valid_rh_dates for day in requested_dates):
            raise LeaveRuleError("RH must use an applicable date in the published RH calendar.")
        if start_date != end_date:
            raise LeaveRuleError("RH requests must be limited to a single restricted holiday date.")
    if category == "VL":
        policy = _policy(start_date.year)
        vacations = policy.values.get("vacation_periods", []) if policy else []
        if not any(
            start_date.isoformat() >= p["start"] and end_date.isoformat() <= p["end"]
            for p in vacations
        ):
            raise LeaveRuleError("VL must fall within an Academic Calendar vacation period.")
    days = chargeable_days(category, start_date, end_date, half=half, closed_holidays=holidays)
    account = _account(
        actor.user_id, start_date.year, category, getattr(actor, "kind", "") == "faculty"
    )
    if days > account.balance:
        raise LeaveRuleError("Requested leave exceeds the available balance.")
    active = LeaveApplication.objects.filter(
        user_id=actor.user_id,
        state__in=(
            "awaiting_substitute",
            "applicant_action",
            "unit_head_review",
            "establishment_routing",
            "final_sanction",
            "director_self_sanction",
            "approved",
        ),
    )
    if exclude_application_id:
        active = active.exclude(pk=exclude_application_id)
    for existing in active:
        if overlaps(
            start_date,
            end_date,
            category,
            half,
            existing.start_date,
            existing.end_date,
            existing.category,
            existing.half,
        ):
            raise LeaveRuleError("Leave overlaps an active pending or approved request.")
    if substitute_user_id is not None and substitute_user_id == actor.user_id:
        raise LeaveRuleError("An employee cannot nominate themselves as substitute.")
    if substitute_user_id is not None:
        substitute_active = LeaveApplication.objects.filter(
            user_id=substitute_user_id,
            state__in=(
                "awaiting_substitute", "applicant_action", "unit_head_review",
                "establishment_routing", "final_sanction", "director_self_sanction", "approved",
            ),
        )
        if any(
            start_date <= item.end_date and item.start_date <= end_date
            for item in substitute_active
        ):
            raise LeaveRuleError("The nominated substitute has overlapping leave.")
    return days


@transaction.atomic
def submit(*, actor, data):
    days = validate_application(
        actor=actor,
        category=data["category"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        half=data.get("half", ""),
        substitute_user_id=data.get("substitute_user_id"),
    )
    policy = _policy(data["start_date"].year)
    route = dict(policy.hierarchy if policy else {})
    route["applicant_roles"] = list(getattr(actor, "roles", ()))
    app = LeaveApplication.objects.create(
        user_id=actor.user_id,
        category=data["category"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        half=data.get("half", ""),
        purpose=data["purpose"],
        station_leave=data.get("station_leave", {}),
        medical_evidence=data.get("medical_evidence", {}),
        chargeable_days=days,
        substitute_required=bool(data.get("substitute_user_id")),
        substitute_user_id=data.get("substitute_user_id"),
        unit_head_user_id=route.get("unit_head_user_id"),
        final_authority_user_id=route.get("final_authority_user_id"),
        route=route,
    )
    director = "Director" in getattr(actor, "roles", ())
    if app.substitute_required:
        next_state = "awaiting_substitute"
        SubstituteRequest.objects.create(application=app, substitute_user_id=app.substitute_user_id)
    elif director:
        next_state = "director_self_sanction"
    else:
        next_state = "unit_head_review"
    return _change(app, next_state, actor.user_id)


@transaction.atomic
def respond_substitute(*, app, actor, accept):
    req = app.substitute_requests.filter(
        substitute_user_id=actor.user_id, response="pending"
    ).first()
    if not req or app.state != "awaiting_substitute":
        raise LeaveRuleError("This substitute request is no longer pending.")
    req.response = "accepted" if accept else "declined"
    req.responded_at = timezone.now()
    req.save(update_fields=["response", "responded_at"])
    return _change(
        app,
        "unit_head_review"
        if accept and "Director" not in app.route.get("applicant_roles", [])
        else "director_self_sanction"
        if accept
        else "applicant_action",
        actor.user_id,
    )


@transaction.atomic
def replace_substitute(*, app, actor, substitute_user_id):
    if (
        app.user_id != actor.user_id
        or app.state != "applicant_action"
        or substitute_user_id == actor.user_id
    ):
        raise LeaveRuleError("A replacement substitute is not allowed for this request.")
    app.substitute_user_id = substitute_user_id
    app.save(update_fields=["substitute_user_id", "updated_at"])
    SubstituteRequest.objects.create(application=app, substitute_user_id=substitute_user_id)
    return _change(app, "awaiting_substitute", actor.user_id)


@transaction.atomic
def withdraw(*, app, actor):
    if app.user_id != actor.user_id or app.state in (
        "approved",
        "rejected",
        "withdrawn",
        "cancelled",
    ):
        raise LeaveRuleError("Only a pending request can be withdrawn.")
    return _change(app, "withdrawn", actor.user_id)


@transaction.atomic
def cancellation(*, actor, app):
    if (
        app.user_id != actor.user_id
        or app.state != "approved"
        or app.start_date <= timezone.localdate()
    ):
        raise LeaveRuleError("Only an approved leave that has not started can be cancelled.")
    return LeaveApplication.objects.create(
        user_id=actor.user_id,
        category=app.category,
        request_type="cancellation",
        base_leave_id=app.pk,
        start_date=app.start_date,
        end_date=app.end_date,
        purpose="Cancellation: " + app.purpose,
        chargeable_days=app.chargeable_days,
        state="unit_head_review",
        unit_head_user_id=app.unit_head_user_id,
        final_authority_user_id=app.final_authority_user_id,
        route=app.route,
    )


@transaction.atomic
def extension(*, actor, app, start_date, end_date, purpose, substitute_user_id=None):
    if (
        app.user_id != actor.user_id
        or app.category not in ("EL", "COL", "VL")
        or app.state != "approved"
    ):
        raise LeaveRuleError("Only ongoing EL, COL, or VL leave may be extended.")
    if not (app.start_date <= timezone.localdate() <= app.end_date):
        raise LeaveRuleError("The leave must be ongoing to request an extension.")
    days = validate_application(
        actor=actor,
        category=app.category,
        start_date=start_date,
        end_date=end_date,
        substitute_user_id=substitute_user_id,
        exclude_application_id=app.pk,
    )
    request = LeaveApplication.objects.create(
        user_id=actor.user_id,
        category=app.category,
        request_type="extension",
        base_leave_id=app.pk,
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
        chargeable_days=days,
        substitute_required=bool(substitute_user_id),
        substitute_user_id=substitute_user_id,
        unit_head_user_id=app.unit_head_user_id,
        final_authority_user_id=app.final_authority_user_id,
        state="awaiting_substitute" if substitute_user_id else "unit_head_review",
        route=app.route,
    )
    if substitute_user_id:
        SubstituteRequest.objects.create(application=request, substitute_user_id=substitute_user_id)
    return request


@transaction.atomic
def review(*, app, actor, outcome, reason="", recommendation=""):
    if app.state not in (
        "unit_head_review",
        "establishment_routing",
        "final_sanction",
        "director_self_sanction",
    ):
        raise LeaveRuleError("This request is not awaiting this workflow action.")
    assigned = {
        "unit_head_review": app.unit_head_user_id,
        "establishment_routing": app.route.get("establishment_user_id"),
        "final_sanction": app.final_authority_user_id,
        "director_self_sanction": app.user_id,
    }[app.state]
    if assigned is not None and assigned != actor.user_id:
        raise LeaveRuleError("You are not the assigned authority for this request.")
    if app.category in ("CL", "RH") and app.state == "unit_head_review":
        if outcome not in ("approve", "reject"):
            raise LeaveRuleError("Unit Head must approve or reject CL/RH.")
        return approve(app, actor.user_id, outcome == "approve", reason)
    if app.state == "unit_head_review":
        if recommendation not in ("recommended", "not_recommended"):
            raise LeaveRuleError("Recommendation is required.")
        app.recommendation = recommendation
        app.save(update_fields=["recommendation", "updated_at"])
        return _change(
            app,
            "establishment_routing" if app.route.get("establishment_user_id") else "final_sanction",
            actor.user_id,
            reason,
        )
    if app.state == "establishment_routing":
        return _change(app, "final_sanction", actor.user_id, reason)
    return approve(app, actor.user_id, outcome == "approve", reason)


@transaction.atomic
def approve(app, actor_id, approved, reason=""):
    app.decision_reason = reason
    app.approved_at = timezone.now() if approved else None
    target = "approved" if approved else "rejected"
    if approved and app.request_type in ("new", "extension"):
        account = _account(app.user_id, app.start_date.year, app.category)
        account.balance -= app.chargeable_days
        account.save(update_fields=["balance", "updated_at"])
        LeaveLedger.objects.create(
            account=account, application_id=app.pk, amount=-app.chargeable_days, kind="approval"
        )
    if approved and app.request_type == "cancellation" and app.base_leave_id:
        base = LeaveApplication.objects.select_for_update().get(pk=app.base_leave_id)
        base.state = "cancelled"
        base.save(update_fields=["state", "updated_at"])
        account = _account(base.user_id, base.start_date.year, base.category)
        account.balance += base.chargeable_days
        account.save(update_fields=["balance", "updated_at"])
        LeaveLedger.objects.create(
            account=account,
            application_id=base.pk,
            amount=base.chargeable_days,
            kind="cancellation",
        )
    return _change(app, target, actor_id, reason)


@transaction.atomic
def year_end(*, year):
    results = []
    for account in LeaveAccount.objects.select_for_update().filter(year=year):
        if account.category in ("CL", "RH", "SCL"):
            account.balance = Decimal("0")
        elif account.category == "VL":
            converted = conversion_vl_to_el(account.balance)
            target = _account(account.user_id, year + 1, "EL", faculty=True)
            target.balance += converted
            target.carried += converted
            target.save(update_fields=["balance", "carried", "updated_at"])
            LeaveLedger.objects.create(account=target, amount=converted, kind="vl_conversion")
            account.balance = Decimal("0")
        elif account.category in ("EL", "COL"):
            target = _account(account.user_id, year + 1, account.category,
                              faculty=account.is_faculty)
            target.balance += account.balance
            target.carried += account.balance
            target.save(update_fields=["balance", "carried", "updated_at"])
            LeaveLedger.objects.create(account=target, amount=account.balance, kind="carry_forward")
            account.balance = Decimal("0")
        account.save(update_fields=["balance", "updated_at"])
        results.append(account.pk)
    return results


def process_sla(*, now=None):
    now = now or timezone.now()
    count = 0
    for app in LeaveApplication.objects.filter(
        state__in=(
            "awaiting_substitute",
            "unit_head_review",
            "establishment_routing",
            "final_sanction",
            "director_self_sanction",
        )
    ):
        policy = _policy(app.start_date.year)
        if not policy:
            continue
        age = (now - app.created_at).total_seconds() / 3600
        kind = (
            "escalation"
            if age >= policy.escalation_hours
            else "reminder"
            if age >= policy.reminder_hours
            else None
        )
        if kind and not app.sla_events.filter(kind=kind, created_at__date=now.date()).exists():
            LeaveSlaEvent.objects.create(application=app, kind=kind)
            recipient = {
                "awaiting_substitute": app.substitute_user_id,
                "unit_head_review": app.unit_head_user_id,
                "establishment_routing": app.route.get("establishment_user_id"),
                "final_sanction": app.final_authority_user_id,
                "director_self_sanction": app.user_id,
            }.get(app.state)
            if recipient is not None:
                LeaveNotification.objects.create(application=app, user_id=recipient, kind=kind)
            count += 1
    return count


@transaction.atomic
def record_offline(*, actor, employee_user_id, employee_kind, data, evidence):
    if not evidence:
        raise LeaveRuleError("Sanction/reference evidence is required.")

    from types import SimpleNamespace

    employee = SimpleNamespace(user_id=employee_user_id, kind=employee_kind, roles=())

    days = validate_application(
        actor=employee, category=data["category"], start_date=data["start_date"],
        end_date=data["end_date"], half=data.get("half", ""),
    )
    app = LeaveApplication.objects.create(
        user_id=employee_user_id, category=data["category"],
        start_date=data["start_date"], end_date=data["end_date"],
        half=data.get("half", ""), purpose=data["purpose"],
        station_leave=data.get("station_leave", {}),
        medical_evidence={**data.get("medical_evidence", {}), "offline_evidence": evidence},
        chargeable_days=days, state="draft", decision_reason="Offline sanction synchronized",
    )
    return approve(app, actor.user_id, True, "Offline sanction: " + str(evidence))


@transaction.atomic
def review_resumption(*, resumption, actor):
    app = resumption.application
    if app.final_authority_user_id is not None and app.final_authority_user_id != actor.user_id:
        raise LeaveRuleError("You are not the assigned resumption authority.")
    approved_end = app.end_date
    actual = resumption.actual_date
    if actual == approved_end:
        state = "reviewed_normal"
    else:
        calendar = _calendar(app.start_date.year)
        holidays = {date.fromisoformat(h["date"]) for h in (calendar.holidays if calendar else [])}
        actual_end = actual if actual >= app.start_date else app.start_date
        actual_days = chargeable_days(app.category, app.start_date, actual_end,
                                      half=app.half, closed_holidays=holidays)
        account = _account(app.user_id, app.start_date.year, app.category)
        difference = actual_days - app.chargeable_days
        if difference > 0:
            if difference > account.balance:
                raise LeaveRuleError("Late resumption exceeds the available balance.")
            account.balance -= difference
            kind = "late_resumption"
        else:
            account.balance += -difference
            kind = "early_resumption"
        account.save(update_fields=["balance", "updated_at"])
        LeaveLedger.objects.create(account=account, application_id=app.pk,
                                   amount=-difference, kind=kind)
        app.end_date = actual_end
        app.chargeable_days = actual_days
        app.save(update_fields=["end_date", "chargeable_days", "updated_at"])
        state = "reviewed_early" if actual < approved_end else "reviewed_late"
    resumption.state = state
    resumption.reviewed_by = actor.user_id
    resumption.reviewed_at = timezone.now()
    resumption.save(update_fields=["state", "reviewed_by", "reviewed_at"])
    return resumption
