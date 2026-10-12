"""The vocabulary the whole module reasons in.

Pure strings and tuples so everything here tests in milliseconds with no DB and
no framework — the domain contract forbids importing Django at all.
"""
from __future__ import annotations

# -- Leave categories (BR-EL-001) ----------------------------------------------
CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

CATEGORIES = (CL, RH, SCL, EL, COL, VL)

CATEGORY_LABELS = {
    CL: "Casual Leave",
    RH: "Restricted Holiday",
    SCL: "Special Casual Leave",
    EL: "Earned Leave",
    COL: "Commuted Leave",
    VL: "Vacation Leave",
}

#: Intervening weekends and closed holidays count as leave days (BR-EL-011).
CONTINUOUS = (EL, COL, VL)
#: First-half / second-half, 0.5 day each (BR-EL-010).
HALF_DAY = (CL,)
#: The Unit Head is the final authority (BR-EL-016).
UNIT_HEAD_FINAL = (CL, RH)
#: Unit Head recommends; configured hierarchy decides (BR-EL-017/018).
HIGHER_SANCTION = (SCL, EL, COL, VL)
#: Formal resumption review applies (BR-EL-027).
RESUMPTION = (EL, COL, VL)
#: Ongoing-leave extension applies (BR-EL-025).
EXTENSION = (EL, COL, VL)
#: Faculty-only categories (BR-EL-006).
FACULTY_ONLY = (VL,)

HALVES = ("first", "second")

# -- Request lifecycle ---------------------------------------------------------
DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
AWAITING_DIRECTOR_SANCTION = "awaiting_director_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"

STATUSES = (
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION,
    APPROVED, REJECTED, WITHDRAWN, CANCELLED,
)

TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED})

#: Everything a request may still be withdrawn from (BR-EL-022).
PENDING_APPROVAL = frozenset({
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION,
})

# -- Request kinds -------------------------------------------------------------
NEW = "new"
CANCELLATION = "cancellation"
EXTENSION_KIND = "extension"

KINDS = (NEW, CANCELLATION, EXTENSION_KIND)

# -- Actor roles (BR-EL-036) ---------------------------------------------------
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTION = "sanction"
DIRECTOR = "director"
SYSTEM = "system"

# -- Decisions -----------------------------------------------------------------
APPROVE = "approve"
REJECT = "reject"
RECOMMENDED = "recommended"
NOT_RECOMMENDED = "not_recommended"
ACCEPT = "accept"
DECLINE = "decline"

# -- Workflow task types -------------------------------------------------------
T_SUBSTITUTE = "substitute"
T_UNIT_HEAD = "unit_head"
T_ESTABLISHMENT = "establishment"
T_FINAL_SANCTION = "final_sanction"
T_DIRECTOR_SANCTION = "director_sanction"
T_RESUMPTION = "resumption"

TASK_TYPES = (
    T_SUBSTITUTE, T_UNIT_HEAD, T_ESTABLISHMENT, T_FINAL_SANCTION,
    T_DIRECTOR_SANCTION, T_RESUMPTION,
)

# -- Resumption outcomes (BR-EL-028) -------------------------------------------
RES_NORMAL = "normal"
RES_EARLY = "early"
RES_LATE = "late"

# -- Ledger kinds --------------------------------------------------------------
LEDGER_CREDIT = "credit"
LEDGER_DEDUCT = "deduct"
LEDGER_RESTORE = "restore"
LEDGER_LAPSE = "lapse"
LEDGER_CONVERT_IN = "convert_in"
LEDGER_CONVERT_OUT = "convert_out"
LEDGER_ADJUST = "adjust"
LEDGER_CARRY = "carry_forward"
