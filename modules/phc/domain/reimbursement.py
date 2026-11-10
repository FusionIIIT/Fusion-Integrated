PENDING_PHC_REVIEW = "PENDING_PHC_REVIEW"
PENDING_ACCOUNTS_VERIFICATION = "PENDING_ACCOUNTS_VERIFICATION"
PENDING_SANCTION = "PENDING_SANCTION"
APPROVED_FOR_PAYMENT = "APPROVED_FOR_PAYMENT"
REIMBURSED = "REIMBURSED"
REJECTED = "REJECTED"

TRANSITION_TABLE = {
    PENDING_PHC_REVIEW: {"review": PENDING_ACCOUNTS_VERIFICATION},
    PENDING_ACCOUNTS_VERIFICATION: {"verify": PENDING_SANCTION},
    PENDING_SANCTION: {"approve": APPROVED_FOR_PAYMENT, "reject": REJECTED},
    APPROVED_FOR_PAYMENT: {},
    REIMBURSED: {},
    REJECTED: {}
}

def get_next_status(current_status: str, action: str) -> str:
    if current_status not in TRANSITION_TABLE:
        raise ValueError(f"Invalid current status: {current_status} # PHC-BR-08")
    
    next_status = TRANSITION_TABLE[current_status].get(action)
    if next_status is None:
        raise ValueError(f"Invalid action '{action}' for status {current_status} # PHC-BR-14")
    
    return next_status

def validate_claim_submission(claimant_kind: str, prescription_patient_id: int, claimant_user_id: int, expense_date, today, window_days: int = 30) -> None:
    if claimant_kind not in ["faculty", "staff"]:
        raise ValueError("Claimant must be an employee (faculty or staff) # PHC-BR-04")
    
    if prescription_patient_id != claimant_user_id:
        raise ValueError("Prescription does not belong to the claimant # PHC-BR-05")
    
    if expense_date > today:
        raise ValueError("Expense date cannot be in the future # PHC-BR-06")
    
    if (today - expense_date).days > window_days:
        raise ValueError(f"Expense date must be within {window_days} days of today # PHC-BR-06")
