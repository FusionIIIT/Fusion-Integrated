"""ELM leave categories, states and actor vocabulary.

Pure data — the policy numbers here are the *baseline defaults* from the
problem statement (PS §3). The configured values live in
``elm.PolicyConfig`` and are what validation actually reads (BR-EL-030);
these defaults seed a fresh installation and are what the domain maths
falls back to when no configuration row exists yet.
"""
from __future__ import annotations

from decimal import Decimal

# -- leave categories (PS §2) -------------------------------------------------
CL = "CL"     # Casual Leave
RH = "RH"     # Restricted Holiday
SCL = "SCL"   # Special Casual Leave
EL = "EL"     # Earned Leave
COL = "COL"   # Commuted Leave
VL = "VL"     # Vacation Leave (faculty only)

CATEGORIES = (CL, RH, SCL, EL, COL, VL)

#: Higher-sanction categories: Unit Head recommends, then the configured
#: hierarchy decides (PS §7). CL/RH are Unit-Head-final.
HIGHER_SANCTION_CATEGORIES = (SCL, EL, COL, VL)
UNIT_HEAD_FINAL_CATEGORIES = (CL, RH)

#: Continuous-counting categories: intervening weekends and closed holidays
#: inside the approved interval count as leave days (PS §4).
CONTINUOUS_COUNTING_CATEGORIES = (EL, COL, VL)

#: Faculty-only category (PS §3).
FACULTY_ONLY_CATEGORIES = (VL,)

#: Baseline entitlements: days per year, half-day support, carry-forward.
BASELINE_ENTITLEMENTS: dict[str, dict] = {
    CL: {"annual_days": Decimal("8"), "half_day": True,
         "half_day_value": Decimal("0.5"), "carry_forward": False},
    RH: {"annual_days": Decimal("2"), "half_day": False,
         "half_day_value": None, "carry_forward": False},
    SCL: {"annual_days": Decimal("15"), "half_day": False,
          "half_day_value": None, "carry_forward": False},
    EL: {"annual_days": Decimal("30"), "half_day": False,
         "half_day_value": None, "carry_forward": True},
    COL: {"annual_days": Decimal("20"), "half_day": False,
          "half_day_value": None, "carry_forward": True},
    VL: {"annual_days": Decimal("60"), "half_day": False,
         "half_day_value": None, "carry_forward": False,
         "vacation_only": True,
         "conversion_ratio": Decimal("2")},  # 2 VL : 1 EL, fractional kept
}

# -- request kinds -------------------------------------------------------------
KIND_NEW = "new"
KIND_CANCELLATION = "cancellation"
KIND_EXTENSION = "extension"
REQUEST_KINDS = (KIND_NEW, KIND_CANCELLATION, KIND_EXTENSION)

# -- actors in the state-transition tables ------------------------------------
ACTOR_EMPLOYEE = "employee"
ACTOR_SUBSTITUTE = "substitute"
ACTOR_UNIT_HEAD = "unit_head"
ACTOR_ESTABLISHMENT = "establishment"
ACTOR_SANCTIONING = "sanctioning_authority"
ACTORS = (ACTOR_EMPLOYEE, ACTOR_SUBSTITUTE, ACTOR_UNIT_HEAD,
          ACTOR_ESTABLISHMENT, ACTOR_SANCTIONING)

# -- new-leave states (WF v1.6 STTs) ------------------------------------------
DRAFT = "draft"
AWAITING_SUBSTITUTE_RESPONSE = "awaiting_substitute_response"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD_REVIEW = "awaiting_unit_head_review"
AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
AWAITING_ESTABLISHMENT_ROUTING = "awaiting_establishment_routing"
AWAITING_FINAL_SANCTION_DECISION = "awaiting_final_sanction_decision"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

NEW_LEAVE_STATES = (
    DRAFT, AWAITING_SUBSTITUTE_RESPONSE, APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD_REVIEW, AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_ESTABLISHMENT_ROUTING, AWAITING_FINAL_SANCTION_DECISION,
    APPROVED, REJECTED, WITHDRAWN,
)

# -- cancellation states (CW-EL-02) -------------------------------------------
CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head_review"
CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
CANCELLATION_PENDING_FINAL = "cancellation_pending_final_decision"

CANCELLATION_STATES = (
    CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_ESTABLISHMENT,
    CANCELLATION_PENDING_FINAL, APPROVED, REJECTED, WITHDRAWN,
)

# -- extension states (CW-EL-03) ----------------------------------------------
AWAITING_EXTENSION_SUBSTITUTE = "awaiting_extension_substitute_response"
EXTENSION_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
AWAITING_EXTENSION_UNIT_HEAD = "awaiting_extension_unit_head_review"
EXTENSION_PENDING_ESTABLISHMENT = "extension_pending_establishment"
EXTENSION_PENDING_FINAL = "extension_pending_final_decision"

EXTENSION_STATES = (
    AWAITING_EXTENSION_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    AWAITING_EXTENSION_UNIT_HEAD, EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL, APPROVED, REJECTED, WITHDRAWN,
)

STATES_BY_KIND = {
    KIND_NEW: NEW_LEAVE_STATES,
    KIND_CANCELLATION: CANCELLATION_STATES,
    KIND_EXTENSION: EXTENSION_STATES,
}

#: Every state from which the applicant may still withdraw (BR-EL-022:
#: withdrawal is cross-cutting across all valid pending pre-final states).
PENDING_STATES = frozenset(
    s for states in STATES_BY_KIND.values() for s in states
    if s not in (APPROVED, REJECTED, WITHDRAWN)
)

#: Terminal states — no further transition of any kind is legal.
TERMINAL_STATES = frozenset({APPROVED, REJECTED, WITHDRAWN})

# -- resumption review outcomes (CW-EL-04) ------------------------------------
RESUMPTION_REVIEW_PENDING = "review_pending"
RESUMPTION_REVIEWED_NORMAL = "reviewed_normal"
RESUMPTION_REVIEWED_EARLY = "reviewed_early"
RESUMPTION_REVIEWED_LATE = "reviewed_late"
RESUMPTION_STATES = (
    RESUMPTION_REVIEW_PENDING, RESUMPTION_REVIEWED_NORMAL,
    RESUMPTION_REVIEWED_EARLY, RESUMPTION_REVIEWED_LATE,
)

# -- half-day vocabulary ------------------------------------------------------
HALF_FULL = "full"
HALF_FIRST = "first"
HALF_SECOND = "second"
HALF_DAY_CHOICES = (
    (HALF_FULL, "Full day"),
    (HALF_FIRST, "First half"),
    (HALF_SECOND, "Second half"),
)

# -- task classes (one actionable workflow task per step) ---------------------
TASK_SUBSTITUTE_RESPONSE = "substitute_response"
TASK_UNIT_HEAD_REVIEW = "unit_head_review"
TASK_ESTABLISHMENT_ROUTING = "establishment_routing"
TASK_FINAL_SANCTION = "final_sanction"
TASK_RESUMPTION_REVIEW = "resumption_review"
TASK_CLASSES = (
    TASK_SUBSTITUTE_RESPONSE, TASK_UNIT_HEAD_REVIEW,
    TASK_ESTABLISHMENT_ROUTING, TASK_FINAL_SANCTION,
    TASK_RESUMPTION_REVIEW,
)

# -- employee / authority kinds -----------------------------------------------
KIND_FACULTY = "faculty"
KIND_STAFF = "staff"
EMPLOYEE_KINDS = (KIND_FACULTY, KIND_STAFF)

# -- task / task-queue statuses --------------------------------------------
TASK_STATUSES = (("pending", "Pending"),
                 ("completed", "Completed"),
                 ("cancelled", "Cancelled"))

# -- notification / outbox statuses ------------------------------------------
OUTBOX_STATUSES = (("pending", "Pending"),
                   ("sending", "Sending"),
                   ("sent", "Sent"),
                   ("failed", "Failed"))

# -- substitute nomination statuses ------------------------------------------
NOMINATION_STATUSES = (("pending", "Awaiting response"),
                       ("accepted", "Accepted"),
                       ("declined", "Declined"),
                       ("superseded",
                        "Superseded by a later nomination"),
                       ("withdrawn",
                        "Withdrawn with the request"))

# -- leave record statuses ---------------------------------------------------
RECORD_STATUSES = (("ongoing", "Ongoing / upcoming"),
                   ("completed", "Completed"),
                   ("cancelled", "Cancelled"))

# -- resumption review statuses -----------------------------------------------
RESUMPTION_REVIEW_STATUSES = (
    (RESUMPTION_REVIEW_PENDING, "Awaiting review"),
    (RESUMPTION_REVIEWED_NORMAL, "Reviewed — normal resumption"),
    (RESUMPTION_REVIEWED_EARLY, "Reviewed — early return"),
    (RESUMPTION_REVIEWED_LATE, "Reviewed — late return"),
)

# -- organizational unit types ---------------------------------------------
UNIT_TYPE_CHOICES = (("department", "Department"),
                     ("section", "Section"),
                     ("office", "Office"))

# -- hierarchy category groups -------------------------------------------------
CATEGORY_GROUP_CHOICES = (("cl_rh", "CL / RH — Unit Head final"),
                          ("higher_sanction",
                           "SCL / EL / COL / VL — higher sanction"))
