"""Automatic Director assignment, only when PCC_ADMIN switches it on (BR-PMS-022; PMS-AFR-050)."""
from __future__ import annotations

import logging

from django.db import transaction

from modules.pms.domain import assignment
from modules.pms.domain import state_machine as sm
from modules.pms.models import Application
from modules.pms.selectors import candidates
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors.oversight import awaiting_director
from modules.pms.services import escalations, review
from modules.pms.services.base import inventor_ids

log = logging.getLogger("fusion.pms.routing")


def auto_route() -> int:
    """Same eligibility as a manual assignment; the least-loaded eligible Director wins."""
    if not policy_selector.current().auto_routing_enabled:
        return 0
    routed = 0
    for pk in list(awaiting_director().values_list("pk", flat=True)):
        with transaction.atomic():
            app = Application.objects.select_for_update().get(pk=pk)
            if app.status not in sm.AWAITING_DIRECTOR:
                continue
            pool = assignment.eligible_directors(candidates.director_candidates(),
                                                 app.domain_code, app.applicant_user_id,
                                                 inventor_ids(app))
            if not pool:
                escalations.raise_case("no_eligible_director", app, app.pk,
                                       note="Automatic routing found no eligible Director.")
                continue
            review.assign(app, pool[0].user_id, actor=None, actor_kind=sm.SYSTEM)
            routed += 1
    log.info("pms.routing.auto routed=%d", routed)
    return routed
