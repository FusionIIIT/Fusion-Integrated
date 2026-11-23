"""Publishing a new settings version (UC-PMS-025; Step 2.8; blueprint Q-13)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.pms.domain import policy as pol
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import PmsPolicy
from modules.pms.selectors import candidates
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import audit
from modules.pms.services.base import now, require, ruled

P_PUBLISH = "pms.policy.publish"


def _people(spec: pol.PolicySpec) -> None:
    ids = {*spec.escalation_chain}
    if spec.pcc_contact_user_id:
        ids.add(spec.pcc_contact_user_id)
    if spec.licensing_route and spec.licensing_route.director_user_id:
        ids.add(spec.licensing_route.director_user_id)
    unknown = ids - set(directory.get_users(sorted(ids))) if ids else set()
    if unknown:
        raise InvalidInput("Some people named in the settings are not in the directory; pick "
                           "them again from the search.", code="unknown_person")


@ruled
def publish(*, actor, payload: dict, based_on_version: int) -> PmsPolicy:
    require(actor, P_PUBLISH)
    if not isinstance(payload, dict):
        raise InvalidInput("Send the settings as an object.", code="invalid_policy")
    try:
        with transaction.atomic():
            latest = PmsPolicy.objects.select_for_update().order_by("-version").first()
            current = latest.version if latest else 0
            if based_on_version != current:
                raise ConflictError(f"The settings changed (now version {current}) since you "
                                    f"opened them. Reload and make your change again.",
                                    code="policy_stale")
            spec = pol.parse(payload, version=current + 1)
            _people(spec)
            row = PmsPolicy.objects.create(version=current + 1, effective_from=now(),
                                           payload=pol.to_payload(spec),
                                           published_by_user_id=actor.user_id)
            audit.record(actor, "policy.published", obj=row, frm=str(current),
                         to=str(row.version))
    except IntegrityError as exc:
        raise ConflictError("Someone published settings at the same moment. Reload and try "
                            "again.", code="policy_stale") from exc
    return row


def setup_gaps() -> list[str]:
    return pol.missing_configuration(policy_selector.current(),
                                     directors=candidates.active_directors().count(),
                                     panel=candidates.active_panel().count())
