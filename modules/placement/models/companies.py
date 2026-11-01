"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# -- Companies and their people ------------------------------------------------
class Company(TimeStampedModel):
    """A recruiting organisation.

    `approval_status` is the PC-BR-007 gate; `status` is the ongoing
    relationship. An approved company can still be blacklisted later.
    """

    STATUS = [("prospect", "Prospect"), ("active", "Active"),
              ("blacklisted", "Blacklisted")]
    APPROVAL = [("pending", "Pending institute approval"),
                ("approved", "Approved"), ("rejected", "Rejected")]

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80, unique=True)
    sector = models.CharField(max_length=60, blank=True)
    website = models.URLField(blank=True)
    hq_city = models.CharField(max_length=80, blank=True)
    tier_rank = models.PositiveSmallIntegerField(null=True, blank=True,
                                                 help_text="1 = best")
    status = models.CharField(max_length=12, choices=STATUS, default="prospect")

    # Rule 8: once placed here a student may not switch out, and must join.
    is_marquee = models.BooleanField(default=False)

    # Rules 2.B and 10 turn on this, so it is a field, not a guess from `sector`.
    SECTOR_KIND = [("it", "IT / software"), ("core", "Core engineering"),
                   ("other", "Other")]
    sector_kind = models.CharField(max_length=8, choices=SECTOR_KIND,
                                   default="other")

    approval_status = models.CharField(max_length=12, choices=APPROVAL,
                                       default="pending", db_index=True)
    approval_note = models.CharField(max_length=300, blank=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    registered_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "placement_company"
        indexes = [
            models.Index(fields=["status", "name"], name="company_status_idx"),
            models.Index(fields=["approval_status"], name="company_approval_idx"),
        ]
        constraints = [
            # An approval records who made it even if the service layer is bypassed.
            models.CheckConstraint(
                condition=~Q(approval_status="approved")
                | Q(approved_by_user_id__isnull=False),
                name="company_approval_is_attributed",
            ),
        ]

    @property
    def can_operate(self) -> bool:
        """PC-BR-007: company functions are enabled only once authorized."""
        return self.approval_status == "approved" and self.status != "blacklisted"

    def __str__(self) -> str:
        return self.name


class CompanyContact(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="contacts")
    name = models.CharField(max_length=120)
    designation = models.CharField(max_length=120, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "placement_company_contact"
        indexes = [models.Index(fields=["company", "is_primary"],
                                name="contact_company_idx")]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class RecruiterAccount(TimeStampedModel):
    """A recruiter's login. PCMS-owned, deliberately not an IAM identity, so
    an auth bug here cannot expose the institute directory.

    `company` is the isolation boundary: every recruiter query filters on it.
    Invitation only — there is no self-service signup.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="recruiters")
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120, blank=True)

    password_hash = models.CharField(max_length=256, blank=True)

    # Only the SHA-256 digest is stored, so a dump yields no usable invite.
    invite_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)
    invited_by_user_id = models.IntegerField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_recruiter_account"
        indexes = [models.Index(fields=["company", "is_active"],
                                name="recruiter_company_idx")]

    @property
    def can_sign_in(self) -> bool:
        return bool(self.is_active and self.password_hash and self.accepted_at)

    def __str__(self) -> str:
        return f"{self.email} @{self.company_id}"


class RecruiterLoginAttempt(models.Model):
    """Every attempt, including unknown addresses — that is the stuffing
    signal."""

    email = models.CharField(max_length=254, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    outcome = models.CharField(max_length=24)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "placement_recruiter_login_attempt"
        indexes = [models.Index(fields=["email", "-at"],
                                name="recruiter_attempt_idx")]

    def __str__(self) -> str:
        return f"{self.email} {self.outcome}"


class RecruiterSession(models.Model):
    """A signed-in recruiter's session. `key` is the SHA-256 of the bearer
    token, so a dump of this table yields no usable session."""

    key = models.CharField(max_length=64, primary_key=True)
    account = models.ForeignKey(RecruiterAccount, on_delete=models.CASCADE,
                                related_name="sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    #: Set in memory by `services.recruiters.sign_in`, never persisted.
    raw_key: str = ""

    class Meta:
        db_table = "placement_recruiter_session"
        indexes = [models.Index(fields=["account", "-created_at"],
                                name="recruiter_session_idx")]

    def __str__(self) -> str:
        # Never render the key — it is the credential, and __str__ reaches logs.
        return f"session for account {self.account_id}"
