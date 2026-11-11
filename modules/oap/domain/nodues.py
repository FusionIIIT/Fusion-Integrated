"""CW-OAP-03: no-dues clearance workflow (pure Python)."""
from modules.oap.domain.errors import InvalidTransition

NO_CASE = "No active clearance case"
IN_PROGRESS = "Verification In Progress"
ALL_CLEAR = "Verification Complete – All Clear"  # noqa: RUF001
DUES_OUTSTANDING = "Verification Complete – Dues Outstanding"  # noqa: RUF001
FINALIZED = "Finalized – Certificate Available"  # noqa: RUF001

START_STATE = NO_CASE
INITIAL_STATE = IN_PROGRESS

STATE_CHOICES = [
    (state, state)
    for state in (IN_PROGRESS, ALL_CLEAR, DUES_OUTSTANDING, FINALIZED)
]

# DUES_OUTSTANDING has no outgoing row in the spec.
TERMINAL_STATES = {DUES_OUTSTANDING, FINALIZED}

# OA-BR-31: seven mandatory authorities, each records only its own domain.
AUTHORITIES = [
    ("library", "Library", "Librarian"),
    ("hostel", "Hostel", "Hostel Warden"),
    ("mess", "Mess", "Mess In-charge"),
    ("department", "Respective Department", "Department Verifier"),
    ("lab", "Lab", "Lab Supervisor"),
    ("academic_section", "Academic Section", "Academic Section Verifier"),
    ("student_section", "Student Section", "Student Section Verifier"),
]
DOMAIN_CODES = [code for code, _, _ in AUTHORITIES]

VERIFY_PERMISSIONS = {
    "library": "oap.nodues.verify_library",
    "hostel": "oap.nodues.verify_hostel",
    "mess": "oap.nodues.verify_mess",
    "department": "oap.nodues.verify_department",
    "lab": "oap.nodues.verify_lab",
    "academic_section": "oap.nodues.verify_academic_section",
    "student_section": "oap.nodues.verify_student_section",
}

RESULT_PENDING = "Pending"
RESULT_CLEAR = "Clear"
RESULT_DUES = "Dues Outstanding"
RESULT_CHOICES = [(r, r) for r in (RESULT_PENDING, RESULT_CLEAR, RESULT_DUES)]

SUBMIT_PERMISSION = "oap.nodues.submit"
FINALIZE_PERMISSION = "oap.nodues.finalize"


def verify_permission(domain_code):
    if domain_code not in DOMAIN_CODES:
        raise ValueError(f"Unknown no-dues domain code: '{domain_code}'")
    return VERIFY_PERMISSIONS[domain_code]


def submit(state):
    """Row 1: Student submits (OA-UC-21)."""
    if state == NO_CASE:
        return IN_PROGRESS
    raise InvalidTransition(f"Cannot apply action 'submit' in state '{state}'")


def state_after_results(state, results):
    """Rows 2-4 (OA-UC-22, OA-BR-32, OA-BR-33)."""
    if state != IN_PROGRESS:
        raise InvalidTransition(
            f"Cannot apply action 'record result' in state '{state}'"
        )
    values = [results[code] for code in DOMAIN_CODES]
    if RESULT_PENDING in values:
        return IN_PROGRESS
    if all(value == RESULT_CLEAR for value in values):
        return ALL_CLEAR
    return DUES_OUTSTANDING


def finalize(state, results):
    """Row 5 (OA-UC-23, OA-BR-33)."""
    if state == ALL_CLEAR and all(
        results[code] == RESULT_CLEAR for code in DOMAIN_CODES
    ):
        return FINALIZED
    raise InvalidTransition(f"Cannot apply action 'finalize' in state '{state}'")
