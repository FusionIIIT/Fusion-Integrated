"""Every tracked deadline, computed from the records (BR-PMS-097..100, UC-PMS-016)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db.models import Prefetch, QuerySet

from modules.pms.domain import deadlines as dl
from modules.pms.domain import office_actions as oa
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AttorneyAssignment,
    MaintenanceCycle,
    OfficeAction,
    ReviewCycle,
)

ACCEPTED = Prefetch("application__attorney_assignments",
                    queryset=AttorneyAssignment.objects.filter(status=sm.ACCEPTED),
                    to_attr="accepted_assignments")


@dataclass(frozen=True)
class DeadlineRow:
    kind: str
    subject_id: int
    application_id: int
    reference: str
    due_on: date
    responsible_user_id: int | None


def tracked(applications: QuerySet[Application]) -> list[DeadlineRow]:
    """Four kinds, four queries, whatever the number of applications."""
    rows = [DeadlineRow(dl.REVIEW, c.pk, c.application_id, c.application.reference,
                        c.due_on, c.director_user_id)
            for c in (ReviewCycle.objects.filter(status="open", application__in=applications)
                      .select_related("application"))]
    rows += [DeadlineRow(dl.REVISION, a.pk, a.pk, a.reference, a.revision_due_on,
                         a.applicant_user_id)
             for a in applications.filter(status__in=sorted(sm.REVISABLE),
                                          revision_due_on__isnull=False)]
    for o in (OfficeAction.objects.exclude(status=sm.RESPONSE_SUBMITTED)
              .filter(application__in=applications)
              .select_related("application").prefetch_related("extensions", ACCEPTED)):
        due = oa.current_deadline(o.response_due_on, [e.new_due_on for e in o.extensions.all()])
        if oa.tracked(due):
            accepted = o.application.accepted_assignments
            rows.append(DeadlineRow(dl.OFFICE_ACTION, o.pk, o.application_id,
                                    o.application.reference, due,
                                    accepted[0].attorney_user_id if accepted else None))
    rows += [DeadlineRow(dl.MAINTENANCE, m.pk, m.application_id, m.application.reference,
                         m.due_on, m.deciding_director_user_id)
             for m in (MaintenanceCycle.objects.filter(status__in=sorted(sm.LIVE_CYCLE),
                                                       application__in=applications)
                       .select_related("application"))]
    return sorted(rows, key=lambda r: (r.due_on, r.kind, r.subject_id))
