"""
Service layer for applying, substitute consent and decisions.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from fusion_auth.principal import Principal
from fusion_auth.permissions import HasModuleGrant, HasPermission
from .domain.state_machine import Transition
from .domain.policy import get_cl_entitlement, get_cl_lapse, get_cl_applicable_categories, get_cl_entitlement, get_cl_lapse, get_cl_applicable_categories
from .domain.state_machine import Transition

@transaction.atomic
def apply_leave(principal_id: int, *, leave_category: str, start_date: str, end_date: str, *, reason: str = None, substitute_id: int = None) -> str:
    """
    Apply for leave.

    :param principal_id: The id of the acting person.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param reason: The reason for the leave.
    :param substitute_id: The id of the substitute, if applicable.
    :return: A string indicating the result of the operation.
    """
    try:
        principal = Principal(user_id=principal_id)
        if not get_cl_applicable_categories(principal, leave_category):
            raise ValidationError(f"Leave category '{leave_category}' is not applicable for principal '{principal}'.")
        
        if not get_cl_entitlement(principal, leave_category):
            raise ValidationError(f"Principal '{principal}' does not have entitlement for leave category '{leave_category}'.")
        
        if not get_cl_lapse(principal, leave_category):
            raise ValidationError(f"Leave category '{leave_category}' does not lapse for principal '{principal}'.")
        
        transition = Transition(principal, leave_category, "apply", start_date, end_date, reason)
        transition.apply()
        
        if substitute_id:
            respond_to_substitute_request(substitute_id, principal_id, leave_category, start_date, end_date, reason)
            return "Leave application submitted. Awaiting substitute consent."
        else:
            unit_head_review(principal_id, leave_category, start_date, end_date, reason)
            return "Leave application submitted. Awaiting Unit Head review."
    except ValidationError as e:
        return str(e)

@transaction.atomic
def respond_to_substitute_request(substitute_id: int, principal_id: int, leave_category: str, start_date: str, end_date: str, *, action: str) -> str:
    """
    Respond to a substitute request.

    :param substitute_id: The id of the substitute.
    :param principal_id: The id of the principal.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param action: The action to take ('accept' or 'decline').
    :return: A string indicating the result of the operation.
    """
    if action not in ["accept", "decline"]:
        raise ValueError(f"Invalid action '{action}'. Action must be 'accept' or 'decline'.")
    
    transition = Transition(substitute_id, principal_id, leave_category, start_date, end_date, action)
    transition.apply()
    
    if action == "accept":
        return "Substitute consent given. Request routed to Unit Head."
    else:
        return "Substitute declined. Request routed to Unit Head for final decision."

@transaction.atomic
def nominate_replacement_substitute(principal_id: int, leave_category: str, start_date: str, end_date: str, *, substitute_id: int) -> str:
    """
    Nominate a replacement substitute.

    :param principal_id: The id of the principal.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param substitute_id: The id of the replacement substitute.
    :return: A string indicating the result of the operation.
    """
    transition = Transition(substitute_id, principal_id, leave_category, start_date, end_date, "nominate_replacement_substitute")
    transition.apply()
    
    return f"Replacement substitute '{substitute_id}' nominated for principal '{principal_id}'. Request routed to Unit Head."

@transaction.atomic
def unit_head_review(principal_id: int, leave_category: str, start_date: str, end_date: str, *, recommendation: str) -> str:
    """
    Unit Head makes a final decision.

    :param principal_id: The id of the principal.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param recommendation: The recommendation ('Recommended' or 'Not Recommended').
    :return: A string indicating the result of the operation.
    """
    if recommendation not in ["Recommended", "Not Recommended"]:
        raise ValueError(f"Invalid recommendation '{recommendation}'. Recommendation must be 'Recommended' or 'Not Recommended'.")
    
    transition = Transition(principal_id, leave_category, "unit_head_review", start_date, end_date, recommendation)
    transition.apply()
    
    return f"Unit Head made a final decision: '{recommendation}' for principal '{principal_id}'."

@transaction.atomic
def establishment_verify_and_route(principal_id: int, leave_category: str, start_date: str, end_date: str, *, recommendation: str) -> str:
    """
    Establishment verifies and routes a higher-sanction request.

    :param principal_id: The id of the principal.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param recommendation: The recommendation ('Recommended' or 'Not Recommended').
    :return: A string indicating the result of the operation.
    """
    if recommendation not in ["Recommended", "Not Recommended"]:
        raise ValueError(f"Invalid recommendation '{recommendation}'. Recommendation must be 'Recommended' or 'Not Recommended'.")
    
    transition = Transition(principal_id, leave_category, "establishment_verify_and_route", start_date, end_date, recommendation)
    transition.apply()
    
    return f"Establishment verified and routed the request. Recommendation: '{recommendation}' for principal '{principal_id}'."

@transaction.atomic
def final_sanction_decision(principal_id: int, leave_category: str, start_date: str, end_date: str, *, decision: str) -> str:
    """
    Make a final sanctioning decision.

    :param principal_id: The id of the principal.
    :param leave_category: The leave category.
    :param start_date: The start date of the leave.
    :param end_date: The end date of the leave.
    :param decision: The decision ('approve' or 'reject').
    :return: A string indicating the result of the operation.
    """
    if decision not in ["approve", "reject"]:
        raise ValueError(f"Invalid decision '{decision}'. Decision must be 'approve' or 'reject'.")
    
    transition = Transition(principal_id, leave_category, "final_sanction_decision", start_date, end_date, decision)
    transition.apply()
    
    return f"Final sanctioning decision made: '{decision}' for principal '{principal_id}'."
