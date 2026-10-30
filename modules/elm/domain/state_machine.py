class InvalidTransition(Exception):
    pass


# State Constants
AWAITING_SUBSTITUTE_RESPONSE = "AWAITING_SUBSTITUTE_RESPONSE"
APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
AWAITING_UNIT_HEAD_REVIEW = "AWAITING_UNIT_HEAD_REVIEW"
AWAITING_ESTABLISHMENT_ROUTING = "AWAITING_ESTABLISHMENT_ROUTING"
AWAITING_FINAL_SANCTION = "AWAITING_FINAL_SANCTION"
AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"

PENDING_STATES = {
    AWAITING_SUBSTITUTE_RESPONSE,
    APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD_REVIEW,
    AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_FINAL_SANCTION,
    AWAITING_DIRECTOR_SELF_SANCTION,
}

UNIT_HEAD_FINAL_CATEGORIES = {"CL", "RH"}


def initial_state(substitute_required: bool, applicant_is_director: bool) -> str:
    if substitute_required:
        return AWAITING_SUBSTITUTE_RESPONSE
    if applicant_is_director:
        return AWAITING_DIRECTOR_SELF_SANCTION
    return AWAITING_UNIT_HEAD_REVIEW


def transition(
    state: str,
    action: str,
    *,
    category: str | None = None,
    applicant_is_director: bool = False,
    establishment_configured: bool = False,
) -> str:
    if action == "withdraw":
        if state in PENDING_STATES:
            return WITHDRAWN
        raise InvalidTransition(f"Cannot withdraw from state {state}")

    if state == AWAITING_SUBSTITUTE_RESPONSE:
        if action == "substitute_accept":
            return (
                AWAITING_DIRECTOR_SELF_SANCTION
                if applicant_is_director
                else AWAITING_UNIT_HEAD_REVIEW
            )
        if action == "substitute_decline":
            return APPLICANT_ACTION_REQUIRED

    if state == APPLICANT_ACTION_REQUIRED and action == "nominate_replacement":
        return AWAITING_SUBSTITUTE_RESPONSE

    if state == AWAITING_UNIT_HEAD_REVIEW:
        if action in ("approve", "reject"):
            if category in UNIT_HEAD_FINAL_CATEGORIES:
                return APPROVED if action == "approve" else REJECTED
            raise InvalidTransition(f"Unit head cannot approve/reject category {category}")
        if action in ("recommend", "not_recommend"):
            if category not in UNIT_HEAD_FINAL_CATEGORIES:
                return (
                    AWAITING_ESTABLISHMENT_ROUTING
                    if establishment_configured
                    else AWAITING_FINAL_SANCTION
                )

            raise InvalidTransition(f"Unit head cannot recommend/not_recommend category {category}")

    if state == AWAITING_ESTABLISHMENT_ROUTING and action == "route":
        return AWAITING_FINAL_SANCTION

    if state in (AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF_SANCTION) and action in (
        "approve",
        "reject",
    ):
        return APPROVED if action == "approve" else REJECTED

    raise InvalidTransition(f"Invalid transition from {state} with action {action}")
