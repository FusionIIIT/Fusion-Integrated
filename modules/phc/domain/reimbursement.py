PENDING_PHC_REVIEW = "pending_phc_review"
PENDING_ACCOUNTS_VERIFICATION = "pending_accounts_verification"
PENDING_SANCTION = "pending_sanction"
APPROVED_FOR_PAYMENT = "approved_for_payment"
REIMBURSED = "reimbursed"
REJECTED = "rejected"

TRANSITION_TABLE = {
    PENDING_PHC_REVIEW: {"review": PENDING_ACCOUNTS_VERIFICATION},
    PENDING_ACCOUNTS_VERIFICATION: {"verify": PENDING_SANCTION},
    PENDING_SANCTION: {"approve": APPROVED_FOR_PAYMENT, "reject": REJECTED},
    APPROVED_FOR_PAYMENT: {},
    REIMBURSED: {},
    REJECTED: {}
}

def get_next_status(current_status, action):
    if current_status not in TRANSITION_TABLE:
        raise ValueError(f"Invalid current status: {current_status} # PHC-BR-08")
    
    next_status = TRANSITION_TABLE[current_status].get(action)
    if next_status is None:
        raise ValueError(f"Invalid action '{action}' for status {current_status} # PHC-BR-08")
    
    return next_status

def validate_submission(claimant_user_kind, prescription_patient_user_id, expense_date, window_days=30):
    from datetime import date
    
    if claimant_user_kind not in ["faculty", "staff"]:
        raise ValueError("Claimant must be an employee (faculty or staff) # PHC-BR-04")
    
    if prescription_patient_user_id != claimant_user_kind:
        raise ValueError("Prescription does not belong to the claimant # PHC-BR-05")
    
    if expense_date > date.today():
        raise ValueError("Expense date cannot be in the future # PHC-BR-06")
    
    if (date.today() - expense_date).days > window_days:
        raise ValueError(f"Expense date must be within {window_days} days of today # PHC-BR-06")
