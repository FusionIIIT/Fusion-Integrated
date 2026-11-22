from django.db import models
from modules.hr_eis.models.employee import EmployeeProfile
from modules.hr_eis.contracts import ClaimType, ClaimStatus, VerificationStatus

class LtcClaim(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="ltc_claims")
    claim_type = models.CharField(max_length=30, choices=ClaimType.CHOICES, default=ClaimType.REIMBURSEMENT)
    block_year = models.CharField(max_length=20)
    destination = models.CharField(max_length=150)
    travel_mode = models.CharField(max_length=50, default="Air/Train")
    departure_date = models.DateField()
    return_date = models.DateField()
    claimed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=30, choices=ClaimStatus.CHOICES, default=ClaimStatus.SUBMITTED, db_index=True)
    hr_verification = models.CharField(max_length=20, choices=VerificationStatus.CHOICES, default=VerificationStatus.PENDING)
    disbursement_ref = models.CharField(max_length=100, blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"LTC Claim #{self.id} ({self.employee.employee_id} - {self.claimed_amount} [{self.status}])"

class CpdaClaim(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="cpda_claims")
    claim_type = models.CharField(max_length=30, choices=ClaimType.CHOICES, default=ClaimType.REIMBURSEMENT)
    financial_year = models.CharField(max_length=20)
    purpose = models.CharField(max_length=255)
    claimed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=30, choices=ClaimStatus.CHOICES, default=ClaimStatus.SUBMITTED, db_index=True)
    hr_verification = models.CharField(max_length=20, choices=VerificationStatus.CHOICES, default=VerificationStatus.PENDING)
    disbursement_ref = models.CharField(max_length=100, blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CPDA Claim #{self.id} ({self.employee.employee_id} - {self.claimed_amount} [{self.status}])"
