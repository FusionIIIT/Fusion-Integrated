

def can_resolve_complaint(physically_verified: bool) -> tuple[bool, str]:
    if not physically_verified:
        return False, "Complaint may be marked resolved only after completed work passes physical verification."
    return True, "Physical verification passed; complaint may be marked resolved."

def can_settle_payment(auditor_verified: bool, director_approved: bool, role: str) -> tuple[bool, str]:
    if not auditor_verified:
        return False, "Payment settlement requires prior Auditor invoice and completed-work validation."
    if not director_approved:
        return False, "Payment settlement requires Director final approval."
    if role not in ["accounts", "Accounts Department"]:
        return False, "Payment settlement must be executed by Accounts Department."
    return True, "Settlement authorized."
