"""Pure rules from the PMS workflow and business-rule specs. No Django here."""

DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_REVIEW = "under_review"
NEEDS_REVISION = "needs_revision"
RESUBMITTED = "resubmitted"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
APPEAL_SUBMITTED = "appeal_submitted"
REJECTION_UPHELD = "rejection_upheld"
REMANDED = "remanded_for_amendment"
DECISION_MODIFIED = "decision_modified"
FILED = "filed"

LABELS = {
    DRAFT: "Draft", SUBMITTED: "Submitted", UNDER_REVIEW: "Under Review",
    NEEDS_REVISION: "Needs Revision", RESUBMITTED: "Resubmitted", APPROVED: "Approved",
    REJECTED: "Rejected", WITHDRAWN: "Withdrawn", APPEAL_SUBMITTED: "Appeal Submitted",
    REJECTION_UPHELD: "Rejection Upheld", REMANDED: "Remanded for Amendment",
    DECISION_MODIFIED: "Decision Modified", FILED: "Filed",
}

#: BR: justification of at least 50 characters for every decision.
JUSTIFICATION_MIN = 50
#: BR: review within 15 business days of assignment.
REVIEW_BUSINESS_DAYS = 15
#: BR: resubmission within 60 days of the rejection/revision decision.
RESUBMISSION_DAYS = 60
#: Appeal window is not fixed by the spec; configurable placeholder.
APPEAL_DAYS = 60

#: Statuses from which the applicant may still withdraw (before filing).
WITHDRAWABLE = frozenset({DRAFT, SUBMITTED, UNDER_REVIEW, NEEDS_REVISION, RESUBMITTED,
                          APPROVED, REJECTED, REMANDED})
#: Statuses from which a revision may be resubmitted.
REVISABLE = frozenset({NEEDS_REVISION, REJECTED, REMANDED})

REVIEW_DECISIONS = {"approve": APPROVED, "reject": REJECTED, "needs_revision": NEEDS_REVISION}
APPEAL_OUTCOMES = {"uphold": REJECTION_UPHELD, "remand": REMANDED, "modify": DECISION_MODIFIED}
RECOMMENDATIONS = ("file_patent", "do_not_file", "needs_amendment")

#: Document rules (PS 2.3.1): PDF only, under 50 MB.
DOCUMENT_MAX_BYTES = 50 * 1024 * 1024
DOCUMENT_TYPES = ("application/pdf",)
SENSITIVITY_LEVELS = ("public", "internal", "confidential")

#: Co-inventor shares must total exactly 100 (PS 2.3.12).
OWNERSHIP_TOTAL = 100


def validate_document(content_type: str, size: int) -> str | None:
    """Return a human message when the upload breaks a rule, else None."""
    if content_type not in DOCUMENT_TYPES:
        return "Only PDF documents are accepted."
    if size <= 0:
        return "The file is empty."
    if size > DOCUMENT_MAX_BYTES:
        return "The file is larger than 50 MB."
    return None


def validate_ownership(shares: list[float]) -> str | None:
    if not shares:
        return "At least one inventor is required."
    if any(s <= 0 for s in shares):
        return "Each ownership share must be positive."
    if round(sum(shares), 2) != OWNERSHIP_TOTAL:
        return f"Ownership shares must total {OWNERSHIP_TOTAL}%."
    return None
