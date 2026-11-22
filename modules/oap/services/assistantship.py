from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.oap.domain import assistantship as asd
from modules.oap.domain import roles
from modules.oap.domain import state_machines as sm
from modules.oap.models import (
    AssistantshipClaim,
    SupervisorVerification,
    TAAssignment,
    ThesisSupervisorAssignment,
)
from modules.oap.selectors import scoping
from modules.oap.services import notifications
from modules.oap.services.common import (
    bad_request,
    domain_guard,
    locked,
    need,
    need_role,
    record,
)


def _resolve_supervisors(student_user_id: int) -> tuple[int | None, int | None]:
    thesis = (
        ThesisSupervisorAssignment.objects.filter(
            student_user_id=student_user_id, superseded_at__isnull=True
        )
        .values_list("supervisor_user_id", flat=True)
        .first()
    )
    ta = (
        TAAssignment.objects.filter(
            student_user_id=student_user_id, supervisor_user_id__isnull=False
        )
        .order_by("-assigned_at")
        .values_list("supervisor_user_id", flat=True)
        .first()
    )
    return thesis, ta


def submit(principal) -> AssistantshipClaim:
    need(principal, "oap.assistantship_claim.create")
    thesis, ta = _resolve_supervisors(principal.user_id)
    if thesis is None or ta is None:
        missing = " and ".join(
            n for n, v in (("thesis supervisor", thesis), ("TA supervisor", ta)) if v is None
        )
        raise ConflictError(
            f"Your {missing} is not recorded yet. Ask the Department Administrator "
            "to record it before you submit.",
            code="supervisor_unresolved",
        )
    with transaction.atomic():
        claim = AssistantshipClaim.objects.create(
            user_id=principal.user_id, thesis_supervisor_user_id=thesis, ta_supervisor_user_id=ta
        )
        record("claim", claim.pk, "", sm.CLAIM_AWAITING_DUAL, principal.user_id)
        notifications.notify(
            [principal.user_id],
            "Assistantship claim submitted",
            f"Your assistantship claim #{claim.pk} was sent to both supervisors.",
        )
        notifications.notify(
            {thesis, ta},
            "Assistantship claim awaiting your verification",
            f"Assistantship claim #{claim.pk} needs your verification.",
        )
    return claim


def verify(principal, pk: int, role: str) -> AssistantshipClaim:
    need(principal, "oap.assistantship_verification.review")
    if role not in asd.SUPERVISOR_ROLES:
        raise bad_request("Role must be 'thesis' or 'ta'.", "invalid_role")
    with transaction.atomic(), domain_guard():
        claim = locked(scoping.claims_for(principal), pk, "Assistantship claim not found.")
        expected = (
            claim.thesis_supervisor_user_id if role == asd.THESIS else claim.ta_supervisor_user_id
        )
        if principal.user_id != expected:
            raise PermissionDeniedError(
                "You are not the assigned supervisor for this role on this claim.",
                code="not_assigned_role",
            )
        if SupervisorVerification.objects.filter(claim=claim, role=role).exists():
            raise ConflictError(
                "You have already verified this claim in this role.", code="already_verified"
            )
        previous = claim.status
        new_state = sm.next_state("claim", previous, "verify", "supervisor")
        try:
            with transaction.atomic():
                SupervisorVerification.objects.create(
                    claim=claim,
                    role=role,
                    verified_by_user_id=principal.user_id,
                    verified_at=timezone.now(),
                )
        except IntegrityError as exc:
            raise ConflictError(
                "This verification was already recorded.", code="already_verified"
            ) from exc
        claim.status = new_state
        claim.save(update_fields=["status", "updated_at"])
        record("claim", claim.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [claim.user_id],
            "Assistantship claim verified",
            f"Supervisor verification recorded on claim #{claim.pk}.",
        )
    return claim


def forward(principal, pk: int) -> AssistantshipClaim:
    need(principal, "oap.assistantship_claim.review")
    need_role(principal, roles.DEPARTMENT_ADMIN)
    with transaction.atomic(), domain_guard():
        claim = locked(scoping.claims_for(principal), pk, "Assistantship claim not found.")
        recorded = list(claim.verifications.values_list("role", flat=True))
        if not asd.both_recorded(recorded):
            raise ConflictError(
                "Both supervisor verifications are needed before department review.",
                code="verification_incomplete",
            )
        previous = claim.status
        new_state = sm.next_state("claim", previous, "forward", "dept_admin")
        claim.status = new_state
        claim.department_forwarded_by_user_id = principal.user_id
        claim.department_forwarded_at = timezone.now()
        claim.save(
            update_fields=[
                "status",
                "department_forwarded_by_user_id",
                "department_forwarded_at",
                "updated_at",
            ]
        )
        record("claim", claim.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [claim.user_id],
            "Assistantship claim forwarded",
            f"Claim #{claim.pk} was forwarded to the HoD.",
        )
    return claim


def decide(principal, pk: int, outcome: str) -> AssistantshipClaim:
    need(principal, "oap.assistantship_claim.approve")
    need_role(principal, roles.HOD)
    if outcome not in ("approve", "reject"):
        raise bad_request("Outcome must be 'approve' or 'reject'.", "invalid_outcome")
    with transaction.atomic(), domain_guard():
        claim = locked(scoping.claims_for(principal), pk, "Assistantship claim not found.")
        previous = claim.status
        new_state = sm.next_state("claim", previous, outcome, "hod")
        claim.status = new_state
        claim.hod_decided_by_user_id = principal.user_id
        claim.hod_decided_at = timezone.now()
        claim.save(
            update_fields=["status", "hod_decided_by_user_id", "hod_decided_at", "updated_at"]
        )
        record("claim", claim.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [claim.user_id],
            "Assistantship claim decided",
            f"Claim #{claim.pk} was {new_state.replace('_', ' ')}.",
        )
    return claim


def process_stipend(principal, pk: int) -> AssistantshipClaim:
    need(principal, "oap.assistantship_claim.update")
    need_role(principal, roles.ACADEMIC_ADMIN)
    with transaction.atomic(), domain_guard():
        claim = locked(scoping.claims_for(principal), pk, "Assistantship claim not found.")
        previous = claim.status
        new_state = sm.next_state("claim", previous, "process_stipend", "academic_admin")
        claim.status = new_state
        claim.stipend_processed_by_user_id = principal.user_id
        claim.stipend_processed_at = timezone.now()
        claim.save(
            update_fields=[
                "status",
                "stipend_processed_by_user_id",
                "stipend_processed_at",
                "updated_at",
            ]
        )
        record("claim", claim.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [claim.user_id],
            "Stipend processed",
            f"The stipend for claim #{claim.pk} has been processed.",
        )
    return claim
