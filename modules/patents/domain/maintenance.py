"""Post-grant maintenance cycle states (BR-PMS-059..061, BW-PMS-14, BW-PMS-15)."""
from __future__ import annotations

ACTIVE = "ACTIVE"
DECISION_REQUESTED = "DECISION_REQUESTED"
RENEWAL_APPROVED = "RENEWAL_APPROVED"
DO_NOT_RENEW = "DO_NOT_RENEW"
RENEWED = "RENEWED"

#: A cycle that has no request or decision yet ("" is a patent granted before this field).
CYCLE_OPEN = frozenset({"", ACTIVE, RENEWED})
#: A cycle that is waiting for, or can still take, the Director's decision.
AWAITING_DECISION = CYCLE_OPEN | {DECISION_REQUESTED}
