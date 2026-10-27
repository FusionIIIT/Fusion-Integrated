# modules/elm/domain/workflow.py
from modules.elm.domain.errors import InvalidStateTransitionError

class LeaveState:
    DRAFT = 'DRAFT'
    AWAITING_SUBSTITUTE_RESPONSE = 'AWAITING_SUBSTITUTE_RESPONSE'
    AWAITING_APPLICANT_ACTION = 'AWAITING_APPLICANT_ACTION'
    AWAITING_UNIT_HEAD_REVIEW = 'AWAITING<｜begin▁of▁sentence｜>AITING_UNIT_HEAD_REVIEW'
    AWAITING_ESTABLISHMENT_REVIEW = 'AWAITING_ESTABLISHMENT_REVIEW'
    AWAITING_SANCTION_AUTHORITY_REVIEW = 'AWAITING_SANCTION_AUTHORITY_REVIEW'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    WITHDRAWN = 'WITHDRAWN'
    AWAITING_CANCELLATION_REVIEW = 'AWAITING_CANCELLATION_REVIEW'
    CANCELLED = 'CANCELLED'
    AWAITING_EXTENSION_REVIEW = 'AWAITING_EXTENSION_REVIEW'
    AWAITING_RESUMPTION_REVIEW = 'AWAITING_RESUMPTION_REVIEW'

class LeaveEvent:
    SUBMIT = 'SUBMIT'
    SUBSTITUTE_ACCEPT = 'SUBSTITUTE_ACCEPT'
    SUBSTITUTE_DECLINE = 'SUBSTITUTE_DECLINE'
    NOMINATE_REPLACEMENT = 'NOMINATE_REPLACEMENT'
    UNIT_HEAD_APPROVE = 'UNIT_HEAD_APPROVE'
    UNIT_HEAD_REJECT = 'UNIT_HEAD_REJECT'
    UNIT_HEAD_RECOMMEND = 'UNIT_HEAD_RECOMMEND'
    ESTABLISHMENT_VERIFY = 'ESTABLISHMENT_VERIFY'
    SANCTION_APPROVE = 'SANCTION_APPROVE'
    SANCTION_REJECT = 'SANCTION_REJECT'
    WITHDRAW = 'WITHDRAW'
    REQUEST_CANCELLATION = 'REQUEST_CANCELLATION'
    APPROVE_CANCELLATION = 'APPROVE_CANCELLATION'
    REJECT_CANCELLATION = 'REJECT_CANCELLATION'
    REQUEST_EXTENSION = 'REQUEST_EXTENSION'
    APPROVE_EXTENSION = 'APPROVE_EXTENSION'
    SUBMIT_RESUMPTION = 'SUBMIT_RESUMPTION'
    APPROVE_RESUMPTION = 'APPROVE_RESUMPTION'

def validate_transition(
    current_state: str,
    event: str,
    is_director: bool = False,
    category: str = 'CL',
    establishment_configured: bool = False,
    substitute_required: bool = False,
) -> str:
    # 1. Handle WITHDRAW from any pending state
    if event == LeaveEvent.WITHDRAW:
        if current_state in (
            LeaveState.AWAITING_SUBSTITUTE_RESPONSE,
            LeaveState.AWAITING_APPLICANT_ACTION,
            LeaveState.AWAITING_UNIT_HEAD_REVIEW,
            LeaveState.AWAITING_ESTABLISHMENT_REVIEW,
            LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW,
        ):
            return LeaveState.WITHDRAWN
        raise InvalidStateTransitionError(f'Cannot withdraw leave in {current_state} state.')

    # 2. Handle SUBMIT from DRAFT
    if current_state == LeaveState.DRAFT and event == LeaveEvent.SUBMIT:
        if is_director:
            return LeaveState.AWAITING_SUBSTITUTE_RESPONSE if substitute_required else LeaveState.APPROVED
        return LeaveState.AWAITING_SUBSTITUTE_RESPONSE if substitute_required else LeaveState.AWAITING_UNIT_HEAD_REVIEW

    # 3. Handle AWAITING_SUBSTITUTE_RESPONSE
    if current_state == LeaveState.AWAITING_SUBSTITUTE_RESPONSE:
        if event == LeaveEvent.SUBSTITUTE_ACCEPT:
            return LeaveState.APPROVED if is_director else LeaveState.AWAITING_UNIT_HEAD_REVIEW
        if event == LeaveEvent.SUBSTITUTE_DECLINE:
            return LeaveState.AWAITING_APPLICANT_ACTION

    # 4. Handle AWAITING_APPLICANT_ACTION
    if current_state == LeaveState.AWAITING_APPLICANT_ACTION:
        if event == LeaveEvent.NOMINATE_REPLACEMENT:
            return LeaveState.AWAITING_SUBSTITUTE_RESPONSE

    # 5. Handle AWAITING_UNIT_HEAD_REVIEW
    if current_state == LeaveState.AWAITING_UNIT_HEAD_REVIEW:
        if category in ('CL', 'RH'):
            if event == LeaveEvent.UNIT_HEAD_APPROVE:
                return LeaveState.APPROVED
            if event == LeaveEvent.UNIT_HEAD_REJECT:
                return LeaveState.REJECTED
        else:
            if event == LeaveEvent.UNIT_HEAD_RECOMMEND:
                return LeaveState.AWAITING_ESTABLISHMENT_REVIEW if establishment_configured else LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW

    # 6. Handle AWAITING_ESTABLISHMENT_REVIEW
    if current_state == LeaveState.AWAITING_ESTABLISHMENT_REVIEW:
        if event == LeaveEvent.ESTABLISHMENT_VERIFY:
            return LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW

    # 7. Handle AWAITING_SANCTION_AUTHORITY_REVIEW
    if current_state == LeaveState.AWAITING_SANCTION_AUTHORITY_REVIEW:
        if event == LeaveEvent.SANCTION_APPROVE:
            return LeaveState.APPROVED
        if event == LeaveEvent.SANCTION_REJECT:
            return LeaveState.REJECTED

    # 8. Handle APPROVED state transitions (cancellation, extension, resumption)
    if current_state == LeaveState.APPROVED:
        if event == LeaveEvent.REQUEST_CANCELLATION:
            return LeaveState.AWAITING_CANCELLATION_REVIEW
        if event == LeaveEvent.REQUEST_EXTENSION:
            return LeaveState.AWAITING_EXTENSION_REVIEW
        if event == LeaveEvent.SUBMIT_RESUMPTION:
            return LeaveState.AWAITING_RESUMPTION_REVIEW

    # 9. Handle Cancellation review
    if current_state == LeaveState.AWAITING_CANCELLATION_REVIEW:
        if event == LeaveEvent.APPROVE_CANCELLATION:
            return LeaveState.CANCELLED
        if event == LeaveEvent.REJECT_CANCELLATION:
            return LeaveState.APPROVED

    # 10. Handle Resumption review
    if current_state == LeaveState.AWAITING_RESUMPTION_REVIEW:
        if event == LeaveEvent.APPROVE_RESUMPTION:
            return LeaveState.APPROVED

    raise InvalidStateTransitionError(f'Illegal transition from {current_state} via {event}')