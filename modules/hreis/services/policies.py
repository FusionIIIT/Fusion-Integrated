"""Effective-dated, append-only HR policy maintenance and active lookup.

Every quantitative entitlement and authority route is supplied as documented
institutional policy. This service has intentionally no default values.
"""

from __future__ import annotations

from datetime import datetime

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.hreis.domain.routing import (
    AUTHORITY_DESIGNATIONS,
    ApprovalRoute,
    RouteError,
    validate_route,
)
from modules.hreis.models import AuditEvent, HRPolicyVersion
from modules.hreis.services.authz import require

_ADMIN = frozenset({"hradmin"})
_FAMILIES = frozenset({"leave", "appraisal", "ltc", "cpda"})
_KINDS = frozenset({"faculty", "staff"})
_FAMILY_LOCKS = {"leave": 142001, "appraisal": 142002, "ltc": 142003, "cpda": 142004}


def _check_parameters(family: str, parameters: dict) -> None:
    if not isinstance(parameters, dict) or not parameters:
        raise BadRequestError(
            "Provide the institution's explicit policy parameters.",
            code="policy_parameters_missing",
        )
    allowed = {"routes", "eligibility", "submission_window", "conditions"}
    if set(parameters) - allowed:
        raise BadRequestError(
            "Policy contains an unknown configuration field.", code="policy_unknown_field"
        )
    if "routes" in parameters:
        routes = parameters["routes"]
        if not isinstance(routes, list):
            raise BadRequestError("Approval routes must be an array.", code="invalid_routes")
        unique = set()
        for row in routes:
            if (
                not isinstance(row, dict)
                or set(row)
                != {
                    "employee_kind",
                    "department",
                    "authorities",
                }
                or not isinstance(row["employee_kind"], str)
                or not isinstance(row["department"], str)
                or not isinstance(row["authorities"], list)
            ):
                raise BadRequestError(
                    "Each route needs employee_kind, department and authorities.",
                    code="invalid_routes",
                )
            key = (row["employee_kind"], row["department"])
            if key in unique:
                raise BadRequestError(
                    "Each employee group and department has one route.", code="duplicate_route"
                )
            unique.add(key)
            try:
                validate_route(
                    ApprovalRoute(
                        family=family,
                        employee_kind=row["employee_kind"],
                        department=row["department"],
                        version="policy",
                        authorities=tuple(row["authorities"]),
                    )
                )
            except (RouteError, TypeError, KeyError) as exc:
                raise BadRequestError(
                    "Approval route is not valid for verified IAM roles.", code="invalid_routes"
                ) from exc
    if "eligibility" in parameters:
        if family != "leave":
            raise BadRequestError(
                "Eligibility by leave type belongs only to leave policy.",
                code="wrong_policy_family",
            )
        rules = parameters["eligibility"]
        if not isinstance(rules, dict) or set(rules) - _KINDS:
            raise BadRequestError(
                "Leave eligibility must be keyed by employee kind.", code="invalid_eligibility"
            )
        from modules.hreis.domain.leave import LEAVE_TYPES

        for choices in rules.values():
            if (
                not isinstance(choices, dict)
                or set(choices) - LEAVE_TYPES
                or any(type(value) is not bool for value in choices.values())
            ):
                raise BadRequestError(
                    "Each leave type needs an explicit eligibility boolean.",
                    code="invalid_eligibility",
                )
    if "submission_window" in parameters:
        if family != "appraisal":
            raise BadRequestError(
                "Submission window belongs only to appraisal policy.", code="wrong_policy_family"
            )
        window = parameters["submission_window"]
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            raise BadRequestError(
                "Appraisal window must declare start and end.", code="invalid_window"
            )
        try:
            start = datetime.fromisoformat(window["start"])
            end = datetime.fromisoformat(window["end"])
        except (TypeError, ValueError) as exc:
            raise BadRequestError(
                "Appraisal dates must be ISO 8601 timestamps.", code="invalid_window"
            ) from exc
        if timezone.is_naive(start) or timezone.is_naive(end) or start >= end:
            raise BadRequestError(
                "Appraisal submission window must be time-zone aware.", code="invalid_window"
            )
    if "conditions" in parameters:
        conditions = parameters["conditions"]
        if not isinstance(conditions, dict):
            raise BadRequestError(
                "Policy conditions must be a key/value object.", code="invalid_conditions"
            )
        reminder_fields = {"pending_reminder_after_hours", "reminder_recipients"}
        if reminder_fields.intersection(conditions):
            delay = conditions.get("pending_reminder_after_hours")
            recipients = conditions.get("reminder_recipients")
            allowed = {"hradmin", *AUTHORITY_DESIGNATIONS}
            if (
                type(delay) is not int
                or delay < 1
                or not isinstance(recipients, dict)
                or not recipients
                or any(
                    role not in allowed
                    or not isinstance(users, list)
                    or not users
                    or any(type(user_id) is not int or user_id <= 0 for user_id in users)
                    or len(set(users)) != len(users)
                    for role, users in recipients.items()
                )
            ):
                raise BadRequestError(
                    "Provide a positive reminder delay and configured authority user IDs.",
                    code="invalid_reminder_config",
                )
        policy_fields = {"policy_notice_at", "policy_notice_recipients"}
        if policy_fields.intersection(conditions):
            at = conditions.get("policy_notice_at")
            recipients = conditions.get("policy_notice_recipients")
            try:
                due = datetime.fromisoformat(at) if isinstance(at, str) else None
            except ValueError:
                due = None
            if (
                due is None
                or timezone.is_naive(due)
                or not isinstance(recipients, list)
                or not recipients
                or any(type(user_id) is not int or user_id <= 0 for user_id in recipients)
                or len(set(recipients)) != len(recipients)
            ):
                raise BadRequestError(
                    "Configure a timezone-aware notice date and recipient user IDs.",
                    code="invalid_policy_notice",
                )


def current_policy(family: str, *, at=None) -> HRPolicyVersion:
    if family not in _FAMILIES:
        raise BadRequestError("Unknown HR policy family.", code="unknown_policy_family")
    now = at or timezone.now()
    policies = list(
        HRPolicyVersion.objects.filter(
            family=family,
            effective_from__lte=now,
        ).order_by("-effective_from", "-version")[:2]
    )
    if not policies or (
        policies[0].effective_until is not None
        and policies[0].effective_until <= now
    ):
        raise ConflictError(
            "No effective institutional policy is configured.", code="policy_unavailable"
        )
    if len(policies) > 1:
        previous = policies[1]
        superseded = (
            previous.effective_until is None
            and policies[0].effective_from > previous.effective_from
            and policies[0].version > previous.version
        )
        overlapping = previous.effective_until is None or previous.effective_until > now
        if overlapping and not superseded:
            raise ConflictError("Institutional policy periods overlap.", code="ambiguous_policy")
    return policies[0]


@transaction.atomic
def create_policy(
    actor,
    *,
    family: str,
    version: int,
    effective_from,
    effective_until,
    parameters: dict,
    idempotency_key: str,
) -> HRPolicyVersion:
    require(actor, "hreis.policy.manage", allowed_roles=_ADMIN)
    if family not in _FAMILIES or type(version) is not int or version <= 0:
        raise BadRequestError("Unknown policy family/version.", code="invalid_policy")
    if (
        not isinstance(effective_from, datetime)
        or timezone.is_naive(effective_from)
        or (
            effective_until is not None
            and (
                not isinstance(effective_until, datetime)
                or timezone.is_naive(effective_until)
                or effective_until <= effective_from
            )
        )
    ):
        raise BadRequestError("Provide valid effective policy dates.", code="invalid_policy_dates")
    _check_parameters(family, parameters)
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 100:
        raise BadRequestError("Provide a unique request key.", code="missing_idempotency_key")
    if AuditEvent.objects.filter(event_key=f"policy:{idempotency_key}").exists():
        raise ConflictError("Policy operation already exists.", code="operation_replayed")
    # Serialize policy publication per family, even when no policy row exists yet.
    # The advisory lock key is a static internal constant, never request SQL text.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_FAMILY_LOCKS[family]])
    # Endpoints are exclusive; a successor may begin when its predecessor ends.
    overlaps = HRPolicyVersion.objects.filter(family=family).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gt=effective_from)
    )
    if effective_until is not None:
        overlaps = overlaps.filter(effective_from__lt=effective_until)
    # An immutable open-ended predecessor may be superseded by a later,
    # higher-versioned policy of either duration. Its history stays unchanged.
    overlaps = overlaps.exclude(
        effective_until__isnull=True,
        effective_from__lt=effective_from,
        version__lt=version,
    )
    if overlaps.exists():
        raise ConflictError("The new policy overlaps an existing version.", code="policy_overlap")
    row = HRPolicyVersion.objects.create(
        family=family,
        version=version,
        effective_from=effective_from,
        effective_until=effective_until,
        parameters=parameters,
        approved_by_user_id=actor.user_id,
        approved_designation=actor.active_role,
    )
    AuditEvent.objects.create(
        event_key=f"policy:{idempotency_key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        action="policy_create",
        resource_kind="policy",
        resource_id=row.pk,
        data={"family": family, "version": version},
    )
    return row


def policy_for_request(family: str) -> HRPolicyVersion:
    return current_policy(family)
