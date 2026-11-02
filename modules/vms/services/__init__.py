"""VMS Business Rule and domain services."""
from modules.vms.services.exceptions import (
    VMSDomainException,
    BlacklistMatchException,
    DuplicatePassException,
    UnauthorizedZoneException,
    PassExpiredException,
    GateValidationException,
    CheckoutBlockedException,
)
from modules.vms.services.blacklist_service import (
    check_blacklist,
    add_to_blacklist,
    remove_from_blacklist,
)
from modules.vms.services.visitor_service import (
    register_visitor,
    check_same_day_duplicate_pass,
    check_safelist_status,
    get_anonymized_visitor_record,
)
from modules.vms.services.pass_service import (
    issue_visit_pass,
    validate_pass_validity,
    extend_pass_duration,
)
from modules.vms.services.visit_service import (
    create_visit_request,
    decide_visit_request,
    terminate_visit_early,
)
from modules.vms.services.gate_service import (
    validate_and_check_in_visitor,
    check_out_visitor,
)
from modules.vms.services.access_service import (
    validate_zone_access,
    grant_temporary_zone_elevation,
)
from modules.vms.services.muster_service import (
    start_emergency_muster,
    update_muster_roll_call,
    audit_muster_overstay_evictions,
    complete_emergency_muster,
)
from modules.vms.services.event_service import (
    process_bulk_event_attendees,
    process_event_checkout,
)

__all__ = [
    "VMSDomainException",
    "BlacklistMatchException",
    "DuplicatePassException",
    "UnauthorizedZoneException",
    "PassExpiredException",
    "GateValidationException",
    "CheckoutBlockedException",
    "check_blacklist",
    "add_to_blacklist",
    "remove_from_blacklist",
    "register_visitor",
    "check_same_day_duplicate_pass",
    "check_safelist_status",
    "get_anonymized_visitor_record",
    "issue_visit_pass",
    "validate_pass_validity",
    "extend_pass_duration",
    "create_visit_request",
    "decide_visit_request",
    "terminate_visit_early",
    "validate_and_check_in_visitor",
    "check_out_visitor",
    "validate_zone_access",
    "grant_temporary_zone_elevation",
    "start_emergency_muster",
    "update_muster_roll_call",
    "audit_muster_overstay_evictions",
    "complete_emergency_muster",
    "process_bulk_event_attendees",
    "process_event_checkout",
]
