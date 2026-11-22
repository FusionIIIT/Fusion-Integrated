from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.oap.domain import no_dues as nd
from modules.oap.domain import roles
from modules.oap.models import NoDuesCase, NoDuesResult
from modules.oap.selectors import scoping
from modules.oap.services import notifications
from modules.oap.services.common import bad_request, locked, need, need_role, record

RESULT_VALUES = {"clear": nd.CLEAR, "outstanding": nd.OUTSTANDING}


def _results(case: NoDuesCase) -> dict[str, str]:
    return dict(case.results.values_list("domain", "result"))


def initiate(principal) -> NoDuesCase:
    need(principal, "oap.no_dues_case.create")
    try:
        with transaction.atomic():
            case = NoDuesCase.objects.create(user_id=principal.user_id)
            NoDuesResult.objects.bulk_create(
                [NoDuesResult(case=case, domain=d) for d in nd.DOMAINS]
            )
            record("no_dues", case.pk, "", nd.IN_PROGRESS, principal.user_id)
            notifications.notify(
                [principal.user_id],
                "No-dues clearance started",
                f"Your no-dues clearance #{case.pk} was sent to all seven authorities.",
            )
    except IntegrityError as exc:
        raise ConflictError(
            "You already have a no-dues clearance in progress.", code="open_case_exists"
        ) from exc
    return case


def record_result(principal, case_id: int, result: str) -> NoDuesCase:
    need(principal, "oap.no_dues_result.update")
    domain = roles.AUTHORITY_DOMAIN.get(principal.active_role)
    if domain is None:
        raise PermissionDeniedError(
            "Your active role is not a no-dues clearance authority.", code="wrong_role"
        )
    if result not in RESULT_VALUES:
        raise bad_request("Result must be 'clear' or 'outstanding'.", "invalid_result")

    with transaction.atomic():
        case = locked(scoping.no_dues_for(principal), case_id, "No-dues case not found.")
        if case.finalized:
            raise ConflictError("This clearance is already finalized.", code="already_finalized")
        before = nd.derive_status(_results(case), finalized=False)
        row = case.results.select_for_update().get(domain=domain)
        row.result = RESULT_VALUES[result]
        row.recorded_by_user_id = principal.user_id
        row.recorded_at = timezone.now()
        row.save(update_fields=["result", "recorded_by_user_id", "recorded_at", "updated_at"])

        after = nd.derive_status(_results(case), finalized=False)
        if after != before:
            record("no_dues", case.pk, before, after, principal.user_id)
        if after in (nd.ALL_CLEAR, nd.DUES_OUTSTANDING) and before == nd.IN_PROGRESS:
            notifications.notify(
                [case.user_id],
                "No-dues verification completed",
                f"All seven authorities have recorded their result for clearance #{case.pk}.",
            )
    return case


def finalize(principal, case_id: int) -> NoDuesCase:
    need(principal, "oap.no_dues_case.approve")
    need_role(principal, roles.ACADEMIC_ADMIN)
    with transaction.atomic():
        case = locked(scoping.no_dues_for(principal), case_id, "No-dues case not found.")
        if case.finalized:
            raise ConflictError("This clearance is already finalized.", code="already_finalized")
        results = _results(case)
        status = nd.derive_status(results, finalized=False)
        if status != nd.ALL_CLEAR:
            open_domains = [d for d in nd.DOMAINS if results.get(d) != nd.CLEAR]
            raise ConflictError(
                "Finalization needs all seven clearances recorded as clear. "
                f"Still open: {', '.join(open_domains)}.",
                code="not_all_clear",
            )
        case.finalized = True
        case.finalized_by_user_id = principal.user_id
        case.finalized_at = timezone.now()
        case.save(update_fields=["finalized", "finalized_by_user_id", "finalized_at", "updated_at"])
        record("no_dues", case.pk, status, nd.FINALIZED, principal.user_id)
        notifications.notify(
            [case.user_id],
            "No-dues certificate available",
            f"Your no-dues certificate for clearance #{case.pk} is ready to download.",
        )
    return case
