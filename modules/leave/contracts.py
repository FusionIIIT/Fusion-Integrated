"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest
from modules.leave.selectors import balances

#: Every state in which an approval is in force, whatever else is being decided
#: about the request at the same time.
#:
#: Asking for a cancellation, or for an extension, does not undo the approval
#: already granted -- the employee is still going, or has already gone. Listing
#: only the settled states meant a request under either kind of review vanished
#: from this answer, and a scheduling consumer would happily assign somebody
#: whose leave has not been cancelled.
ABSENT_STATES = (
    State.APPROVED_NOT_STARTED.value,
    State.ONGOING.value,
    State.AWAITING_RESUMPTION.value,
    State.AWAITING_RESUMPTION_VERIFICATION.value,
    # Cancellation under consideration: still approved until somebody says
    # otherwise.
    State.CANCELLATION_UNIT_HEAD.value,
    State.CANCELLATION_ESTABLISHMENT.value,
    State.CANCELLATION_FINAL.value,
    # Extension under consideration: the original leave is running regardless.
    State.EXTENSION_AWAITING_SUBSTITUTE.value,
    State.EXTENSION_APPLICANT_ACTION_REQUIRED.value,
    State.EXTENSION_AWAITING_UNIT_HEAD.value,
    State.EXTENSION_AWAITING_ESTABLISHMENT.value,
    State.EXTENSION_AWAITING_FINAL.value,
)


@dataclass(frozen=True)
class OnLeaveDTO:
    user_id: int
    category: str
    starts_on: date
    ends_on: date
    #: True while a cancellation or an extension is being decided. The absence
    #: still stands; a consumer that cares can say "away, subject to review".
    under_review: bool = False


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    category: str
    available: Decimal


def get_absences(user_ids: Sequence[int], on: date) -> dict[int, OnLeaveDTO]:
    """Who among these people is away on this date.

    Another module asking "can this person be scheduled" wants one call for the
    whole list, so the answer is keyed by user.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveRequest.objects.filter(
        user_id__in=ids,
        state__in=ABSENT_STATES,
        starts_on__lte=on,
        ends_on__gte=on,
    ).only("user_id", "category", "state", "starts_on", "ends_on")
    return {
        r.user_id: OnLeaveDTO(
            user_id=r.user_id,
            category=r.category,
            starts_on=r.starts_on,
            ends_on=r.ends_on,
            under_review=r.state.startswith(("CANCELLATION", "EXTENSION")),
        )
        for r in rows
    }


def get_balances(
    user_ids: Sequence[int], year: int, category: str
) -> dict[int, LeaveBalanceDTO]:
    """What each of these people has left in one category."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.leave.domain.categories import Category

    wanted = Category(category)
    out: dict[int, LeaveBalanceDTO] = {}
    for user_id in ids:
        balance = balances.balance_for(user_id, year, wanted)
        out[user_id] = LeaveBalanceDTO(
            user_id=user_id, category=category, available=balance.available
        )
    return out
