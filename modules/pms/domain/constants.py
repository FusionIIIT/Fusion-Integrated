"""Domain constants, status enumerations, thresholds and limits for PMS."""

# Application Lifecycle States
STATUS_DRAFT = "draft"
STATUS_SUBMITTED = "submitted"
STATUS_UNDER_REVIEW = "under_review"
STATUS_APPROVED = "approved"
STATUS_NEEDS_REVISION = "needs_revision"
STATUS_RESUBMITTED = "resubmitted"
STATUS_REJECTED = "rejected"
STATUS_APPEAL_SUBMITTED = "appeal_submitted"
STATUS_REMANDED_FOR_AMENDMENT = "remanded_for_amendment"
STATUS_REJECTION_UPHELD = "rejection_upheld"
STATUS_DECISION_MODIFIED = "decision_modified"
STATUS_ASSIGNMENT_OFFERED = "assignment_offered"
STATUS_ATTORNEY_ASSIGNED = "attorney_assigned"
STATUS_BUDGET_APPROVED = "budget_approved"
STATUS_BUDGET_REJECTED = "budget_rejected"
STATUS_BUDGET_ESCALATED = "budget_escalated"
STATUS_FILED = "filed"
STATUS_OFFICE_ACTION_RECORDED = "office_action_recorded"
STATUS_RESPONSE_READY = "response_ready"
STATUS_AWAITING_APPLICANT_APPROVAL = "awaiting_applicant_approval"
STATUS_APPLICANT_APPROVED = "applicant_approved"
STATUS_RESPONSE_SUBMITTED = "response_submitted"
STATUS_GRANTED = "granted"
STATUS_RENEWAL_DECISION_REQUESTED = "renewal_decision_requested"
STATUS_RENEWAL_APPROVED = "renewal_approved"
STATUS_RENEWED = "renewed"
STATUS_DO_NOT_RENEW = "do_not_renew"
STATUS_WITHDRAWN = "withdrawn"
STATUS_EXPIRED = "expired"

APPLICATION_STATUSES = frozenset(
    {
        STATUS_DRAFT,
        STATUS_SUBMITTED,
        STATUS_UNDER_REVIEW,
        STATUS_APPROVED,
        STATUS_NEEDS_REVISION,
        STATUS_RESUBMITTED,
        STATUS_REJECTED,
        STATUS_APPEAL_SUBMITTED,
        STATUS_REMANDED_FOR_AMENDMENT,
        STATUS_REJECTION_UPHELD,
        STATUS_DECISION_MODIFIED,
        STATUS_ASSIGNMENT_OFFERED,
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_BUDGET_APPROVED,
        STATUS_BUDGET_REJECTED,
        STATUS_BUDGET_ESCALATED,
        STATUS_FILED,
        STATUS_OFFICE_ACTION_RECORDED,
        STATUS_RESPONSE_READY,
        STATUS_AWAITING_APPLICANT_APPROVAL,
        STATUS_APPLICANT_APPROVED,
        STATUS_RESPONSE_SUBMITTED,
        STATUS_GRANTED,
        STATUS_RENEWAL_DECISION_REQUESTED,
        STATUS_RENEWAL_APPROVED,
        STATUS_RENEWED,
        STATUS_DO_NOT_RENEW,
        STATUS_WITHDRAWN,
        STATUS_EXPIRED,
    }
)

# Terminal states
TERMINAL_STATUSES = frozenset(
    {
        STATUS_WITHDRAWN,
        STATUS_EXPIRED,
        STATUS_REJECTION_UPHELD,
        STATUS_DO_NOT_RENEW,
    }
)

# Pre-filing states eligible for withdrawal (BR-PMS-067, 068, 069, 070)
WITHDRAWAL_ELIGIBLE_STATUSES = frozenset(
    {
        STATUS_DRAFT,
        STATUS_SUBMITTED,
        STATUS_UNDER_REVIEW,
        STATUS_APPROVED,
        STATUS_NEEDS_REVISION,
        STATUS_RESUBMITTED,
        STATUS_ASSIGNMENT_OFFERED,
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_BUDGET_APPROVED,
        STATUS_BUDGET_REJECTED,
        STATUS_BUDGET_ESCALATED,
    }
)

# Review Decisions (BR-PMS-029)
DECISION_APPROVE = "approve"
DECISION_REJECT = "reject"
DECISION_NEEDS_REVISION = "needs_revision"
DECISIONS = frozenset({DECISION_APPROVE, DECISION_REJECT, DECISION_NEEDS_REVISION})

# Decision validation constraints (BR-PMS-030, 031, 035)
JUSTIFICATION_MIN_LEN = 50
REVIEW_WINDOW_BUSINESS_DAYS = 15
REVISION_WINDOW_DAYS = 60

# Attorney Assignment Statuses (BW-PMS-06, 07)
ATTORNEY_STATUS_OFFERED = "offered"
ATTORNEY_STATUS_ACCEPTED = "accepted"
ATTORNEY_STATUS_DECLINED = "declined"
ATTORNEY_STATUSES = frozenset(
    {
        ATTORNEY_STATUS_OFFERED,
        ATTORNEY_STATUS_ACCEPTED,
        ATTORNEY_STATUS_DECLINED,
    }
)

# Patentability recommendations (BR-PMS-046)
REC_FILE_PATENT = "file_patent"
REC_DO_NOT_FILE = "do_not_file"
REC_NEEDS_AMENDMENT = "needs_amendment"
ATTORNEY_RECOMMENDATIONS = frozenset(
    {
        REC_FILE_PATENT,
        REC_DO_NOT_FILE,
        REC_NEEDS_AMENDMENT,
    }
)

# Appeal outcomes (BR-PMS-095)
APPEAL_UPHOLD = "uphold_rejection"
APPEAL_REMAND = "remand_for_amendment"
APPEAL_MODIFY = "modify_decision"
APPEAL_OUTCOMES = frozenset({APPEAL_UPHOLD, APPEAL_REMAND, APPEAL_MODIFY})

# Maintenance Renewal Decisions (BR-PMS-061)
MAINTENANCE_RENEW = "renew"
MAINTENANCE_DO_NOT_RENEW = "do_not_renew"
MAINTENANCE_DECISIONS = frozenset({MAINTENANCE_RENEW, MAINTENANCE_DO_NOT_RENEW})

# Document Constraints (BR-PMS-014, 015)
DOC_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
DOC_MIME_PDF = "application/pdf"

# Document sensitivity classifications (BR-PMS-130)
SENSITIVITY_STANDARD = "standard"
SENSITIVITY_CONFIDENTIAL = "confidential"
SENSITIVITY_RESTRICTED = "restricted"
SENSITIVITIES = frozenset(
    {
        SENSITIVITY_STANDARD,
        SENSITIVITY_CONFIDENTIAL,
        SENSITIVITY_RESTRICTED,
    }
)

# Default Budget Escalation Threshold limit in INR (BR-PMS-051)
DEFAULT_BUDGET_THRESHOLD = 100000.00

# Deadline notification offsets in days (BR-PMS-101, 102, 103)
ALERT_OFFSETS_DAYS = (30, 15, 5)

# Actors
ACTOR_APPLICANT = "applicant"
ACTOR_DIRECTOR = "director"
ACTOR_PCC_ADMIN = "pcc_admin"
ACTOR_ATTORNEY = "attorney"
ACTOR_SYSTEM = "system"
ACTORS = frozenset(
    {
        ACTOR_APPLICANT,
        ACTOR_DIRECTOR,
        ACTOR_PCC_ADMIN,
        ACTOR_ATTORNEY,
        ACTOR_SYSTEM,
    }
)
