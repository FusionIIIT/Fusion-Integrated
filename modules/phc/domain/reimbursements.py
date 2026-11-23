from datetime import date
from decimal import Decimal


def validate_submission_date(expense_date: date, submission_date: date,
                             window_days: int) -> None:
    if expense_date > submission_date:
        raise ValueError("The expense date cannot be in the future.")
    if (submission_date - expense_date).days > window_days:
        raise ValueError(
            f"Submit the claim within {window_days} calendar days of the expense date."
        )


def validate_claim_amount(amount: Decimal) -> None:
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Enter a claim amount greater than zero.")


CLAIM_PENDING_PHC = "pending_phc_review"
CLAIM_PENDING_ACCOUNTS = "pending_accounts_verification"
CLAIM_PENDING_SANCTION = "pending_sanction"
CLAIM_APPROVED_PAYMENT = "approved_for_payment"
CLAIM_REJECTED = "rejected"
CLAIM_REIMBURSED = "reimbursed"
CLAIM_TERMINAL = frozenset({CLAIM_REJECTED, CLAIM_REIMBURSED})

CLAIM_TRANSITIONS = (
    (CLAIM_PENDING_PHC, "review", "Compounder", CLAIM_PENDING_ACCOUNTS),
    (CLAIM_PENDING_ACCOUNTS, "verify", "Accounts Admin", CLAIM_PENDING_SANCTION),
    (CLAIM_PENDING_SANCTION, "approve", "Registrar", CLAIM_APPROVED_PAYMENT),
    (CLAIM_PENDING_SANCTION, "reject", "Registrar", CLAIM_REJECTED),
    (CLAIM_APPROVED_PAYMENT, "pay", "Accounts Admin", CLAIM_REIMBURSED),
)


def claim_transition(state: str, event: str, actor: str) -> str:
    for source, action, role, target in CLAIM_TRANSITIONS:
        if (source, action) == (state, event):
            if actor != role:
                raise PermissionError("This action is reserved for the assigned office role.")
            return target
    raise LookupError("The claim is closed or the requested action is not available.")
