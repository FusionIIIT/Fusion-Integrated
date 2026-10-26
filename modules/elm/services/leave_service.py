"""Transactional ELM commands. Identity and permissions come from Fusion Principal."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.elm.domain.state_machine import (
    ACTIVE,
    CONTINUOUS,
    CREDITS,
    HIGHER,
    PENDING,
    count_days,
    intervals_overlap,
)
from modules.elm.models import (
    AccountEntry,
    AttendanceEvent,
    EmployeeRecord,
    HolidayCalendar,
    LeaveActionLog,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    Notification,
    VacationPeriod,
)


def authorize(actor, permission):
    if not actor or not actor.has_module("elm") or not actor.has_permission(permission):
        raise PermissionDeniedError()


def employee(user_id, *, lock=False):
    qs = EmployeeRecord.objects.select_for_update() if lock else EmployeeRecord.objects
    try:
        return qs.get(user_id=str(user_id), is_active=True)
    except EmployeeRecord.DoesNotExist as exc:
        raise DomainError("An active ELM employee profile is required.") from exc


def lock_people(ids):
    # One deterministic lock order serializes overlaps across categories and substitute races.
    return list(
        EmployeeRecord.objects.select_for_update()
        .filter(user_id__in=sorted(set(map(str, ids))))
        .order_by("user_id")
    )


def policy():
    return LeavePolicy.objects.filter(pk=1).first() or LeavePolicy()


def entry(balance, action, amount, actor_id, req=None):
    AccountEntry.objects.create(
        user_id=balance.user_id,
        leave_type=balance.leave_type,
        year=balance.year,
        action=action,
        amount=amount,
        actor_user_id=str(actor_id),
        request=req,
    )


def account(profile, category, year):
    credit = Decimal(str(policy().annual_credits.get(category, CREDITS[category])))
    if category == "EL" and profile.kind == "faculty":
        credit = Decimal(0)
    if (category == "VL" and profile.kind != "faculty") or (
        category == "COL" and not profile.col_eligible
    ):
        credit = Decimal(0)
    balance, created = LeaveBalance.objects.get_or_create(
        user_id=profile.user_id, leave_type=category, year=year, defaults={"credited": credit}
    )
    if created:
        entry(balance, "ANNUAL_CREDIT", credit, "system")
    return LeaveBalance.objects.select_for_update().get(pk=balance.pk)


def log(req, actor_id, action, remarks="", role="employee"):
    LeaveActionLog.objects.create(
        leave_request=req,
        actor_user_id=str(actor_id),
        actor_role=role,
        action=action,
        remarks=remarks,
    )


def notify(req, recipient, event):
    if recipient:
        Notification.objects.create(
            request=req,
            recipient_user_id=str(recipient),
            event=event,
            message=f"{req.request_kind} {req.id}: {event} ({req.status})",
        )


def attendance(req, event):
    AttendanceEvent.objects.create(
        request=req,
        user_id=req.applicant_user_id,
        event=event,
        payload={
            "start_date": str(req.start_date),
            "end_date": str(req.actual_end_date or req.end_date),
            "leave_type": req.leave_type,
            "days": str(req.actual_duration_days or req.duration_days),
        },
    )


def get_request(leave_id, extra_people=()):
    try:
        ref = LeaveRequest.objects.only("applicant_user_id", "substitute_user_id").get(pk=leave_id)
        lock_people([ref.applicant_user_id, ref.substitute_user_id, *extra_people])
        return LeaveRequest.objects.select_for_update().get(pk=leave_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.") from exc


def owned(req, actor):
    if req.applicant_user_id != str(actor.user_id):
        raise PermissionDeniedError("This is not your leave request.")


def effective_calendar(year):
    cal = (
        HolidayCalendar.objects.filter(year=year, published_at__lte=timezone.now())
        .order_by("-published_at", "-pk")
        .first()
    )
    if not cal:
        raise DomainError("Publish a holiday/RH calendar for the requested year before applying.")
    return cal


def recorded_end(req):
    end = req.actual_end_date or req.end_date
    if req.request_kind == "EXTEND" and req.original_id and req.original.actual_end_date:
        end = min(end, req.original.actual_end_date)
    return end


def overlaps(user_id, start, end, half=False, session="", exclude=()):
    rows = (
        LeaveRequest.objects.filter(
            applicant_user_id=str(user_id),
            status__in=ACTIVE,
            request_kind__in=["LEAVE", "EXTEND"],
            start_date__lte=end,
        )
        .exclude(pk__in=exclude)
        .select_related("original")
    )
    return any(
        r.start_date <= recorded_end(r)
        and intervals_overlap(
            start,
            end,
            r.start_date,
            recorded_end(r),
            half=half,
            session=session,
            other_half=r.is_half_day,
            other_session=r.half_day_session,
        )
        for r in rows
    )


def has_responsibility(user_id, start, end):
    rows = LeaveRequest.objects.filter(
        substitute_user_id=str(user_id),
        substitute_status="ACCEPTED",
        status__in=ACTIVE,
        start_date__lte=end,
    ).select_related("original")
    return any(
        r.start_date <= recorded_end(r)
        and intervals_overlap(start, end, r.start_date, recorded_end(r))
        for r in rows
    )


def substitute_valid(profile, substitute_id, start, end):
    if str(substitute_id) == profile.user_id:
        raise DomainError("You cannot nominate yourself as substitute.")
    employee(substitute_id)
    if overlaps(substitute_id, start, end):
        raise ConflictError("The substitute has overlapping pending or approved leave.")


def resolve_route(profile, category, actor=None):
    if profile.is_director:
        return [{"user_id": profile.user_id, "role": "director"}]
    route = profile.routes.get(category, [])
    if not route or route[0].get("role") != "unit_head":
        raise DomainError("Configure the employee's Unit Head and sanctioning route first.")
    route = route[:1] if category in {"CL", "RH"} else route
    if category in HIGHER and len(route) < 2:
        raise DomainError("Higher-sanction leave needs a Unit Head and final authority.")
    for step in route:
        if str(step["user_id"]) == profile.user_id:
            raise DomainError(
                "An employee cannot sanction their own leave outside the Director path."
            )
        employee(step["user_id"])
    return [{"user_id": str(s["user_id"]), "role": s["role"]} for s in route]


def assign(req):
    req.task_assigned_at = timezone.now()
    req.reminder_sent = req.escalation_sent = False
    if req.status == "PENDING_SUBSTITUTE":
        req.current_approver_user_id, req.current_approver_role = (
            req.substitute_user_id,
            "substitute",
        )
    elif req.status == "APPLICANT_ACTION":
        req.current_approver_user_id, req.current_approver_role = req.applicant_user_id, "employee"
    else:
        step = req.route[req.route_index]
        req.current_approver_user_id, req.current_approver_role = step["user_id"], step["role"]
        req.status = "PENDING_UNIT_HEAD" if step["role"] == "unit_head" else "PENDING_AUTHORITY"
    req.save()
    notify(req, req.current_approver_user_id, "TASK_ASSIGNED")


def validate_application(profile, data, *, exclude=(), retrospective=False):
    category, start, end = data["leave_type"], data["start_date"], data["end_date"]
    if start.year != end.year:
        raise DomainError("Split cross-year requests into separate annual applications.")
    if (end - start).days > 365 or end < start:
        raise DomainError("Invalid leave date range.")
    if not retrospective and start < timezone.localdate():
        raise DomainError("Past leave requires authorized offline entry with sanction evidence.")
    if category == "VL" and profile.kind != "faculty":
        raise DomainError("Vacation leave is available only to faculty.")
    if category == "COL" and not profile.col_eligible:
        raise DomainError("This employee is not eligible for COL.")
    p, cal = policy(), effective_calendar(start.year)
    try:
        days = count_days(
            category,
            start,
            end,
            half_day=data.get("is_half_day", False),
            session=data.get("half_day_session", ""),
            closed=cal.closed_dates,
            restricted=cal.restricted_dates,
            weekends=p.weekend_days or [5, 6],
        )
    except ValueError as exc:
        raise DomainError(str(exc)) from exc
    if data.get("duration_days") is not None and Decimal(str(data["duration_days"])) != days:
        raise DomainError(f"Duration must match the server-calculated {days} days.")
    if category == "VL":
        dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        periods = list(VacationPeriod.objects.filter(start_date__lte=end, end_date__gte=start))
        if any(not any(v.start_date <= d <= v.end_date for v in periods) for d in dates):
            raise DomainError(
                "VL must be within vacation periods supplied by the Academic Calendar."
            )
    if (
        category == "COL"
        and p.medical_evidence_required
        and not data.get("evidence_reference", "").strip()
    ):
        raise DomainError("Medical evidence reference is required for COL.")
    if overlaps(
        profile.user_id,
        start,
        end,
        data.get("is_half_day", False),
        data.get("half_day_session", ""),
        exclude,
    ):
        raise ConflictError("Overlapping pending or approved leave exists.")
    # An employee cannot request leave after accepting responsibility for someone else.
    if has_responsibility(profile.user_id, start, end):
        raise ConflictError("You have accepted substitute responsibility during this interval.")
    sub = str(data.get("substitute_id", "")).strip()
    if profile.coverage_required and not sub and not retrospective:
        raise DomainError("A substitute is required for this employee.")
    if sub:
        substitute_valid(profile, sub, start, end)
    if data.get("station_leave"):
        if (
            not data.get("station_leave_address", "").strip()
            or not data.get("out_of_station_from")
            or not data.get("out_of_station_to")
        ):
            raise DomainError("Station leave requires address, departure and return dates.")
        if not (data["out_of_station_from"] <= start <= end <= data["out_of_station_to"]):
            raise DomainError("Station departure/return dates must enclose the leave interval.")
    elif (
        data.get("station_leave_address")
        or data.get("out_of_station_from")
        or data.get("out_of_station_to")
    ):
        raise DomainError("Station details require the station-leave option.")
    return days


class LeaveService:
    @staticmethod
    @transaction.atomic
    def apply_leave(actor, **data):
        authorize(actor, "elm.leave.apply")
        lock_people([actor.user_id, data.get("substitute_id", "")])
        profile = employee(actor.user_id)
        if actor.kind not in {"faculty", "staff"} or actor.kind != profile.kind:
            raise PermissionDeniedError(
                "An employee IAM identity matching the ELM profile is required."
            )
        days = validate_application(profile, data)
        balance = account(profile, data["leave_type"], data["start_date"].year)
        if balance.closed or balance.balance < days:
            raise ConflictError("Insufficient balance or the leave year is closed.")
        route = resolve_route(profile, data["leave_type"])
        sub = str(data.pop("substitute_id", "")).strip()
        data.pop("duration_days", None)
        req = LeaveRequest.objects.create(
            applicant_user_id=profile.user_id,
            duration_days=days,
            substitute_user_id=sub,
            substitute_status="PENDING" if sub else "NOT_REQUIRED",
            route=route,
            status="PENDING_SUBSTITUTE" if sub else "PENDING_UNIT_HEAD",
            **data,
        )
        balance.pending += days
        balance.save(update_fields=["pending"])
        entry(balance, "RESERVE", days, actor.user_id, req)
        log(req, actor.user_id, "SUBMIT")
        assign(req)
        return req

    @staticmethod
    @transaction.atomic
    def respond_substitute(actor, leave_id, accept, remarks=""):
        authorize(actor, "elm.leave.substitute")
        req = get_request(leave_id)
        lock_people([req.applicant_user_id, actor.user_id])
        if req.substitute_user_id != str(actor.user_id):
            raise PermissionDeniedError("Not the designated substitute.")
        if req.status != "PENDING_SUBSTITUTE":
            raise ConflictError("This request is not awaiting substitute consent.")
        if not accept and not remarks.strip():
            raise DomainError("A decline reason is required.")
        if accept:
            substitute_valid(
                employee(req.applicant_user_id), actor.user_id, req.start_date, req.end_date
            )
        req.substitute_status = "ACCEPTED" if accept else "REJECTED"
        req.substitute_remarks = remarks
        req.status = "PENDING_UNIT_HEAD" if accept else "APPLICANT_ACTION"
        log(
            req,
            actor.user_id,
            "SUBSTITUTE_ACCEPT" if accept else "SUBSTITUTE_DECLINE",
            remarks,
            "substitute",
        )
        assign(req)
        return req

    @staticmethod
    @transaction.atomic
    def replace_substitute(actor, leave_id, substitute_id):
        authorize(actor, "elm.leave.apply")
        req = get_request(leave_id, [substitute_id])
        owned(req, actor)
        if req.status != "APPLICANT_ACTION":
            raise ConflictError("Replacement is available only after substitute decline.")
        lock_people([req.applicant_user_id, substitute_id])
        substitute_valid(employee(actor.user_id), substitute_id, req.start_date, req.end_date)
        req.substitute_user_id, req.substitute_status = str(substitute_id), "PENDING"
        req.substitute_remarks, req.status = "", "PENDING_SUBSTITUTE"
        log(req, actor.user_id, "REPLACE_SUBSTITUTE", str(substitute_id))
        assign(req)
        return req

    @staticmethod
    @transaction.atomic
    def review_unit_head(actor, leave_id, approve, remarks="", forward_higher=False):
        authorize(actor, "elm.leave.approve")
        req = get_request(leave_id)
        profile = employee(req.applicant_user_id)
        employee(actor.user_id)
        lock_people([req.applicant_user_id])
        if req.status not in {"PENDING_UNIT_HEAD", "PENDING_AUTHORITY"}:
            raise ConflictError("This request is not awaiting approval.")
        if (
            req.current_approver_user_id != str(actor.user_id)
            or actor.active_role != req.current_approver_role
        ):
            raise PermissionDeniedError(
                "Only the assigned authority in the assigned active role may decide."
            )
        if str(actor.user_id) == req.applicant_user_id and not (
            profile.is_director and actor.active_role == "director"
        ):
            raise PermissionDeniedError("Self-approval is restricted to the Director path.")
        if not approve and not remarks.strip():
            raise DomainError("A rejection or non-recommendation reason is required.")
        if req.route_index < len(req.route) - 1:
            req.recommendation = "RECOMMENDED" if approve else "NOT_RECOMMENDED"
            log(req, actor.user_id, req.recommendation, remarks, actor.active_role)
            req.route_index += 1
            assign(req)
            return req
        LeaveService._finalize(req, profile, actor, approve, remarks)
        return req

    @staticmethod
    def _finalize(req, profile, actor, approve, remarks):
        balance = account(profile, req.leave_type, req.start_date.year)
        if balance.closed:
            raise ConflictError("This leave account year is closed; reconcile it administratively.")
        if req.request_kind in {"LEAVE", "EXTEND"}:
            if approve and req.substitute_user_id:
                substitute_valid(profile, req.substitute_user_id, req.start_date, req.end_date)
            balance.pending -= req.duration_days
            if approve:
                balance.availed += req.duration_days
            entry(
                balance, "APPROVE" if approve else "RELEASE", req.duration_days, actor.user_id, req
            )
        elif req.request_kind == "CANCEL" and approve:
            original = get_request(req.original_id)
            if original.status != "APPROVED" or timezone.localdate() >= original.start_date:
                raise ConflictError("Cancellation must be finalized before approved leave starts.")
            balance.availed -= original.duration_days
            original.status = "CANCELLED"
            original.save(update_fields=["status", "updated_at"])
            entry(balance, "CANCEL_RESTORE", original.duration_days, actor.user_id, req)
            attendance(original, "CANCELLED")
        elif req.request_kind == "RESUME" and approve:
            original = get_request(req.original_id)
            total = original.duration_days + sum(
                (
                    r.duration_days
                    for r in original.followups.filter(request_kind="EXTEND", status="APPROVED")
                ),
                Decimal(0),
            )
            delta = req.duration_days - total
            if delta > balance.balance:
                raise ConflictError("Insufficient balance for late resumption.")
            if overlaps(
                profile.user_id,
                original.start_date,
                req.end_date,
                exclude=[original.pk, *original.followups.values_list("pk", flat=True)],
            ):
                raise ConflictError("The actual leave interval overlaps another request.")
            balance.availed += delta
            original.actual_end_date, original.actual_duration_days = (
                req.end_date,
                req.duration_days,
            )
            original.save(update_fields=["actual_end_date", "actual_duration_days", "updated_at"])
            entry(balance, "RESUMPTION_ADJUST", delta, actor.user_id, req)
            attendance(original, "RESUMPTION_REVIEWED")
        if balance.pending < 0 or balance.availed < 0:
            raise ConflictError("Leave ledger is inconsistent; reconcile before proceeding.")
        balance.save(update_fields=["pending", "availed"])
        req.status = "APPROVED" if approve else "REJECTED"
        req.rejection_reason = "" if approve else remarks
        req.current_approver_user_id = req.current_approver_role = ""
        req.save()
        log(
            req,
            actor.user_id,
            "APPROVE" if approve else "REJECT",
            remarks,
            actor.active_role or "leave_admin",
        )
        notify(req, req.applicant_user_id, "FINAL_DECISION")
        if approve and req.request_kind in {"LEAVE", "EXTEND"}:
            attendance(req, "APPROVED")

    @staticmethod
    @transaction.atomic
    def withdraw_leave(actor, leave_id, reason=""):
        authorize(actor, "elm.leave.apply")
        req = get_request(leave_id)
        owned(req, actor)
        if req.status not in PENDING:
            raise ConflictError("Only pending requests can be withdrawn.")
        lock_people([req.applicant_user_id])
        if req.request_kind in {"LEAVE", "EXTEND"}:
            b = account(employee(actor.user_id), req.leave_type, req.start_date.year)
            if b.closed or b.pending < req.duration_days:
                raise ConflictError("Leave ledger requires reconciliation.")
            b.pending -= req.duration_days
            b.save(update_fields=["pending"])
            entry(b, "WITHDRAW_RELEASE", req.duration_days, actor.user_id, req)
        recipients = {s["user_id"] for s in req.route} | {req.substitute_user_id}
        req.status = "WITHDRAWN"
        req.current_approver_user_id = req.current_approver_role = ""
        req.save()
        log(req, actor.user_id, "WITHDRAW", reason)
        for recipient in recipients:
            notify(req, recipient, "WITHDRAWN")
        return req

    @staticmethod
    @transaction.atomic
    def followup(actor, leave_id, kind, **data):
        authorize(actor, "elm.leave.apply")
        original = get_request(leave_id, [data.get("substitute_id", "")])
        owned(original, actor)
        lock_people([actor.user_id, data.get("substitute_id", "")])
        profile = employee(actor.user_id)
        if (
            original.status != "APPROVED"
            or original.request_kind != "LEAVE"
            or original.actual_end_date
        ):
            raise ConflictError("A current approved original leave is required.")
        if original.followups.filter(status__in=PENDING).exists():
            raise ConflictError("Another follow-up is already pending for this leave.")
        effective_end = max(
            [
                original.end_date,
                *original.followups.filter(request_kind="EXTEND", status="APPROVED").values_list(
                    "end_date", flat=True
                ),
            ]
        )
        today = timezone.localdate()
        reason = data.get("reason", "").strip()
        if not reason:
            raise DomainError("A reason or resumption detail is required.")
        if kind == "CANCEL":
            if today >= original.start_date:
                raise ConflictError("Cancellation is available only before leave starts.")
            start, end, days = original.start_date, original.end_date, original.duration_days
        elif kind == "EXTEND":
            if (
                original.leave_type not in CONTINUOUS
                or not original.start_date <= today <= effective_end
            ):
                raise ConflictError("Only ongoing EL, COL or VL can be extended.")
            start, end = effective_end + timedelta(days=1), data["end_date"]
            if start.year != original.start_date.year or end.year != original.start_date.year:
                raise DomainError(
                    "Cross-year extensions require annual-account reconciliation "
                    "and are not supported yet."
                )
            validation = {**data, "start_date": start, "leave_type": original.leave_type}
            days = validate_application(profile, validation)
        elif kind == "RESUME":
            if original.leave_type not in CONTINUOUS or today < original.start_date:
                raise ConflictError("Resumption requires an EL, COL or VL leave that has begun.")
            start, end = original.start_date, data["end_date"]
            if end > today or end < start or end.year != start.year:
                raise DomainError(
                    "Actual resumption must be between the start date and today "
                    "in the same leave year."
                )
            days = Decimal((end - start).days + 1)
        else:
            raise DomainError("Unknown follow-up type.")
        route = original.route if kind != "RESUME" else original.route[-1:]
        sub = str(data.get("substitute_id", "")).strip() if kind == "EXTEND" else ""
        req = LeaveRequest.objects.create(
            applicant_user_id=profile.user_id,
            leave_type=original.leave_type,
            start_date=start,
            end_date=end,
            duration_days=days,
            reason=reason,
            original=original,
            request_kind=kind,
            route=route,
            evidence_reference=data.get("evidence_reference", ""),
            substitute_user_id=sub,
            substitute_status="PENDING" if sub else "NOT_REQUIRED",
            status="PENDING_SUBSTITUTE" if sub else "PENDING_UNIT_HEAD",
        )
        if kind == "EXTEND":
            b = account(profile, req.leave_type, start.year)
            if b.closed or b.balance < days:
                raise ConflictError("Insufficient balance for extension.")
            b.pending += days
            b.save(update_fields=["pending"])
            entry(b, "RESERVE", days, actor.user_id, req)
        log(req, actor.user_id, "SUBMIT_" + kind, reason)
        assign(req)
        return req

    @staticmethod
    @transaction.atomic
    def record_offline(actor, employee_id, sanction_reference, unavailable_reason, **data):
        authorize(actor, "elm.leave.admin")
        if not sanction_reference.strip() or not unavailable_reason.strip():
            raise DomainError("Offline sanction reference and ELM-unavailable reason are required.")
        if data["start_date"] > timezone.localdate():
            raise DomainError("Offline synchronization is retrospective.")
        lock_people([employee_id])
        profile = employee(employee_id)
        days = validate_application(profile, data, retrospective=True)
        b = account(profile, data["leave_type"], data["start_date"].year)
        if b.closed or b.balance < days:
            raise ConflictError("Insufficient balance or closed leave year.")
        data.pop("substitute_id", None)
        data.pop("duration_days", None)
        req = LeaveRequest.objects.create(
            applicant_user_id=profile.user_id,
            duration_days=days,
            status="APPROVED",
            current_approver_role="",
            **data,
        )
        b.availed += days
        b.save(update_fields=["availed"])
        entry(b, "OFFLINE_SYNC", days, actor.user_id, req)
        log(
            req,
            actor.user_id,
            "OFFLINE_SYNC",
            sanction_reference + ": " + unavailable_reason,
            "leave_admin",
        )
        notify(req, profile.user_id, "OFFLINE_RECORDED")
        attendance(req, "OFFLINE_RECORDED")
        return req
