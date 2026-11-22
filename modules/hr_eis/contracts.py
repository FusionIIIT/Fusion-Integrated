"""Constants, choices, and contract definitions for HR-EIS."""

class LeaveTypes:
    CASUAL = "Casual"
    RESTRICTED = "Restricted"
    MEDICAL = "Medical"
    EARNED = "Earned"
    VACATION = "Vacation"
    SABBATICAL = "Sabbatical"
    ALL = [CASUAL, RESTRICTED, MEDICAL, EARNED, VACATION, SABBATICAL]
    CHOICES = [(x, x) for x in ALL]

class EmploymentTypes:
    FACULTY = "Faculty"
    STAFF = "Staff"
    ADMIN = "Admin"
    ALL = [FACULTY, STAFF, ADMIN]
    CHOICES = [(x, x) for x in ALL]

class EmployeeStatus:
    ACTIVE = "Active"
    ON_LEAVE = "On_Leave"
    RETIRED = "Retired"
    SUSPENDED = "Suspended"
    ALL = [ACTIVE, ON_LEAVE, RETIRED, SUSPENDED]
    CHOICES = [(x, x) for x in ALL]

class LeaveStatus:
    SUBMITTED = "Submitted"
    RECOMMENDED = "Recommended"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    ALL = [SUBMITTED, RECOMMENDED, APPROVED, REJECTED, CANCELLED]
    CHOICES = [(x, x) for x in ALL]

class AppraisalStatus:
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under_Review"
    FINALIZED = "Finalized"
    ARCHIVED = "Archived"
    ALL = [DRAFT, SUBMITTED, UNDER_REVIEW, FINALIZED, ARCHIVED]
    CHOICES = [(x, x) for x in ALL]

class ClaimType:
    ADVANCE = "Advance"
    REIMBURSEMENT = "Reimbursement"
    ALL = [ADVANCE, REIMBURSEMENT]
    CHOICES = [(x, x) for x in ALL]

class ClaimStatus:
    SUBMITTED = "Submitted"
    VERIFIED_HR = "Verified_HR"
    APPROVED_AUTHORITY = "Approved_Authority"
    SETTLED_FINANCE = "Settled_Finance"
    REJECTED = "Rejected"
    ALL = [SUBMITTED, VERIFIED_HR, APPROVED_AUTHORITY, SETTLED_FINANCE, REJECTED]
    CHOICES = [(x, x) for x in ALL]

class VerificationStatus:
    PENDING = "Pending"
    VERIFIED = "Verified"
    FLAGGED = "Flagged"
    ALL = [PENDING, VERIFIED, FLAGGED]
    CHOICES = [(x, x) for x in ALL]

class AuthorityRoles:
    HOD = "HOD"
    REGISTRAR = "Registrar"
    DIRECTOR = "Director"
    HR_ADMIN = "HR Administrator"
    ACCOUNTANT = "Accountant"
