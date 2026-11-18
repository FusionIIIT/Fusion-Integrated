import base64
import hashlib
import json
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError
from fusion_auth.client import get_client
from fusion_auth.principal import Principal
from modules.psm import models as m
from modules.psm import selectors, services
from modules.psm.access import member

REPORTS = {
    "operational": "indents",
    "procurement": "orders",
    "stock": "stock",
    "financial": "invoices",
    "audit": "audit",
}


def cipher():
    # Key rotation invalidates old schedules; credentials are never returned through the API.
    key = base64.urlsafe_b64encode(
        hashlib.sha256((settings.SECRET_KEY + ":psm-report-credentials").encode()).digest()
    )
    return Fernet(key)


def authorize(principal, report):
    scope = member(principal)
    if not principal.has_permission("psm.report.view"):
        raise DomainError("Report access is required.")
    if report not in REPORTS:
        raise DomainError("Unknown report.")
    allowed = ["ps_admin", "accounts", "auditor", "department_admin", "department_head"]
    if report == "financial":
        allowed = ["accounts", "auditor"]
    if report == "audit":
        allowed = ["accounts", "auditor"]
    if scope.role not in allowed:
        raise DomainError("This report is outside your role.")
    return scope


def report_rows(principal, report, filters):
    authorize(principal, report)
    resource = REPORTS[report]
    if not isinstance(filters, dict) or set(filters) - {
        "status",
        "department",
        "item",
        "from",
        "to",
    }:
        raise DomainError("Unsupported report filters.")
    qs = selectors.collection(principal, resource)
    for key, value in filters.items():
        if key in ("from", "to"):
            from django.utils.dateparse import parse_date

            date = parse_date(value)
            if date is None:
                raise DomainError("Report dates must be YYYY-MM-DD.")
            qs = qs.filter(**{"created_at__date__" + ("gte" if key == "from" else "lte"): date})
        elif key in {f.name for f in qs.model._meta.fields}:
            qs = qs.filter(**{key: value})
        else:
            raise DomainError(f"{key} is not a supported filter for this report.")
    rows = list(qs.order_by("-created_at").values())
    if report == "financial":
        from django.db.models import Sum

        paid = dict(
            m.Payment.objects.filter(invoice_id__in=[row["id"] for row in rows])
            .values("invoice_id")
            .annotate(total=Sum("amount"))
            .values_list("invoice_id", "total")
        )
        for row in rows:
            row["paid_amount"] = paid.get(row["id"], 0)
            row["outstanding"] = row["amount"] - row["paid_amount"]
    return json.loads(json.dumps(rows, cls=DjangoJSONEncoder))


@transaction.atomic
def generate_report(principal, data, schedule=None):
    report = services.text(data, "report")
    filters = data.get("filters", {})
    rows = report_rows(principal, report, filters)
    run = m.ReportRun.objects.create(
        user_id=principal.user_id, report=report, filters=filters, rows=rows, schedule=schedule
    )
    services.audit(principal, run, "report_generated", {"report": report, "rows": len(rows)})
    return run


@transaction.atomic
def schedule_report(principal, data):
    report = services.text(data, "report")
    authorize(principal, report)
    if not principal.has_permission("psm.report.schedule"):
        raise DomainError("Scheduling permission is required.")
    report_rows(principal, report, data.get("filters", {}))
    hours = services.number(data, "interval_hours", 1)
    if hours != int(hours) or hours > 8760:
        raise DomainError("Schedule interval must be an integer from 1 to 8760 hours.")
    token = data.get("_credential")
    if not isinstance(token, str) or not token:
        raise DomainError("An IAM session is required to authorize future report runs.")
    obj = m.ReportSchedule.objects.create(
        user_id=principal.user_id,
        report=report,
        filters=data.get("filters", {}),
        interval_hours=int(hours),
        next_run=services.moment(data, "next_run"),
        credential=cipher().encrypt(token.encode()).decode(),
    )
    services.audit(principal, obj, "report_scheduled")
    return obj


def resolve_schedule(schedule):
    token = cipher().decrypt(schedule.credential.encode()).decode()
    if getattr(settings, "PSM_PREVIEW", False):
        from devtools.psm_preview_auth import resolve_token

        principal = resolve_token(token)
    else:
        session = get_client().resolve_session(auth_token=token)
        principal = Principal.from_session(session) if session else None
    if principal is None or principal.user_id != schedule.user_id:
        raise DomainError("Schedule session expired; recreate the schedule after signing in.")
    if not principal.has_permission("psm.report.schedule"):
        raise DomainError("Scheduling permission has been revoked.")
    authorize(principal, schedule.report)
    return principal


def run_due_reports():
    count = 0
    for pk in m.ReportSchedule.objects.filter(
        enabled=True, next_run__lte=timezone.now()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            obj = m.ReportSchedule.objects.select_for_update().get(pk=pk)
            if not obj.enabled or obj.next_run > timezone.now():
                continue
            try:
                with transaction.atomic():
                    principal = resolve_schedule(obj)
                    generate_report(principal, {"report": obj.report, "filters": obj.filters}, obj)
            except (DomainError, InvalidToken) as exc:
                obj.enabled = False
                m.Audit.objects.create(
                    actor_id=obj.user_id,
                    department="",
                    entity="reportschedule",
                    object_id=obj.pk,
                    action="schedule_blocked",
                    snapshot={"reason": str(exc)},
                )
            else:
                obj.next_run = timezone.now() + timedelta(hours=obj.interval_hours)
                count += 1
            obj.save()
    return count
