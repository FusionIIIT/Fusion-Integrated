import datetime
from django.db import transaction
from modules.hr_eis.models.claims import LtcClaim, CpdaClaim
from modules.hr_eis.contracts import ClaimStatus, VerificationStatus, AuthorityRoles
from modules.hr_eis.domain.rules import validate_ltc_claim, validate_cpda_claim, validate_settlement
from modules.hr_eis.domain.state_machine import ClaimStateMachine
from modules.hr_eis.services.audit import AuditService

class ClaimService:
    @classmethod
    def submit_ltc(cls, employee, claim_type, block_year, destination, dep_date, ret_date, claimed_amt):
        # BR-HR-016
        validate_ltc_claim(claim_type, float(claimed_amt))
        claim = LtcClaim.objects.create(
            employee=employee,
            claim_type=claim_type,
            block_year=block_year,
            destination=destination,
            departure_date=dep_date,
            return_date=ret_date,
            claimed_amount=claimed_amt,
            status=ClaimStatus.SUBMITTED,
            hr_verification=VerificationStatus.PENDING
        )
        AuditService.log("LtcClaim", claim.id, employee.employee_id, "SUBMIT_LTC", to_state=ClaimStatus.SUBMITTED)
        return claim

    @classmethod
    def verify_ltc(cls, claim, actor, verified=True):
        # BR-HR-017
        ClaimStateMachine.transition(claim.status, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
        claim.status = ClaimStatus.VERIFIED_HR
        claim.hr_verification = VerificationStatus.VERIFIED if verified else VerificationStatus.FLAGGED
        claim.save()
        AuditService.log("LtcClaim", claim.id, actor, "VERIFY_LTC", to_state=ClaimStatus.VERIFIED_HR)
        return claim

    @classmethod
    def approve_ltc(cls, claim, approved_amount, actor_role, actor_id):
        # BR-HR-018
        ClaimStateMachine.transition(claim.status, ClaimStatus.APPROVED_AUTHORITY, actor_role)
        claim.status = ClaimStatus.APPROVED_AUTHORITY
        claim.approved_amount = approved_amount
        claim.save()
        AuditService.log("LtcClaim", claim.id, actor_id, "APPROVE_LTC", to_state=ClaimStatus.APPROVED_AUTHORITY)
        return claim

    @classmethod
    def settle_ltc(cls, claim, disbursement_ref, actor_role, actor_id):
        # BR-HR-019, BR-HR-022, BR-HR-035
        validate_settlement(claim.status, float(claim.approved_amount), disbursement_ref)
        ClaimStateMachine.transition(claim.status, ClaimStatus.SETTLED_FINANCE, actor_role)
        claim.status = ClaimStatus.SETTLED_FINANCE
        claim.disbursement_ref = disbursement_ref
        claim.settled_at = datetime.datetime.now()
        claim.save()
        AuditService.log("LtcClaim", claim.id, actor_id, "SETTLE_LTC", to_state=ClaimStatus.SETTLED_FINANCE, details=disbursement_ref)
        return claim

    @classmethod
    def submit_cpda(cls, employee, claim_type, financial_year, purpose, claimed_amt, budget=100000.0):
        # BR-HR-020
        validate_cpda_claim(float(claimed_amt), purpose, budget)
        claim = CpdaClaim.objects.create(
            employee=employee,
            claim_type=claim_type,
            financial_year=financial_year,
            purpose=purpose,
            claimed_amount=claimed_amt,
            status=ClaimStatus.SUBMITTED,
            hr_verification=VerificationStatus.PENDING
        )
        AuditService.log("CpdaClaim", claim.id, employee.employee_id, "SUBMIT_CPDA", to_state=ClaimStatus.SUBMITTED)
        return claim

    @classmethod
    def settle_cpda(cls, claim, disbursement_ref, actor_role, actor_id):
        # BR-HR-022, BR-HR-035
        validate_settlement(claim.status, float(claim.approved_amount), disbursement_ref)
        ClaimStateMachine.transition(claim.status, ClaimStatus.SETTLED_FINANCE, actor_role)
        claim.status = ClaimStatus.SETTLED_FINANCE
        claim.disbursement_ref = disbursement_ref
        claim.settled_at = datetime.datetime.now()
        claim.save()
        AuditService.log("CpdaClaim", claim.id, actor_id, "SETTLE_CPDA", to_state=ClaimStatus.SETTLED_FINANCE, details=disbursement_ref)
        return claim
