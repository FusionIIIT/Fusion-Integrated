"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


# -- Season and policy ---------------------------------------------------------
class PlacementPolicy(TimeStampedModel):
    """One season of the signed Placement Policy. Switching rules live in
    PolicyCategory, which is per discipline group."""

    season = models.CharField(max_length=12, unique=True)     # "2026-27"
    label = models.CharField(max_length=60, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Rule 6: from this date, appearing is mandatory for unplaced students.
    mandatory_from = models.DateField(null=True, blank=True)

    # discipline code -> policy group (cse_ece | core | design)
    discipline_groups = models.JSONField(default=dict, blank=True)

    min_cpi_to_register = models.DecimalField(max_digits=4, decimal_places=2,
                                              null=True, blank=True)
    allow_backlog_registration = models.BooleanField(default=True)

    # Rules 20 and 21. Recorded only; PCMS does not take payment.
    late_registration_fee = models.PositiveIntegerField(default=1000)
    reregistration_fee = models.PositiveIntegerField(default=2000)

    # Fallback when the recruiter sets no deadline (PC-BR-013).
    default_offer_response_hours = models.PositiveIntegerField(default=72)

    class Meta:
        db_table = "placement_policy"
        verbose_name_plural = "placement policies"

    def __str__(self) -> str:
        return self.season


class PolicyCategory(TimeStampedModel):
    """One category within a discipline group (policy rule 2).

        CSE/ECE  Cat 1  <=10 LPA      1.5x, one switch then out
                 Cat 2  10-16.5 LPA   2x,   one switch then out
        Core     Cat 1  6.5-11.5 LPA  1.5x and must exceed 11.5
        Design   Cat 1  <=7.5 LPA     1.5x, out once above 12
                 Cat 2  7.5-12 LPA    1.5x, out once above 12
    """

    GROUPS = [("cse_ece", "CSE & ECE"), ("core", "ME, SM and Core"),
              ("design", "Design")]

    policy = models.ForeignKey(PlacementPolicy, on_delete=models.CASCADE,
                               related_name="categories")
    group = models.CharField(max_length=12, choices=GROUPS)
    number = models.PositiveSmallIntegerField()               # Cat 1 / Cat 2

    ctc_min = models.DecimalField(max_digits=8, decimal_places=2,
                                  null=True, blank=True)
    ctc_max = models.DecimalField(max_digits=8, decimal_places=2,
                                  null=True, blank=True)

    switch_multiplier = models.DecimalField(max_digits=4, decimal_places=2,
                                            default=Decimal("1.5"))
    # An absolute floor a switch must exceed, on top of the multiple.
    switch_floor = models.DecimalField(max_digits=8, decimal_places=2,
                                       null=True, blank=True)
    # Holding above this ends the student's season.
    exit_above = models.DecimalField(max_digits=8, decimal_places=2,
                                     null=True, blank=True)
    # Null means unlimited, bounded instead by exit_above.
    max_switches = models.PositiveSmallIntegerField(null=True, blank=True,
                                                    default=1)

    class Meta:
        db_table = "placement_policy_category"
        ordering = ["group", "number"]
        constraints = [
            models.UniqueConstraint(fields=["policy", "group", "number"],
                                    name="policy_category_unique"),
            models.CheckConstraint(
                condition=Q(ctc_min__isnull=True) | Q(ctc_max__isnull=True)
                | Q(ctc_max__gte=models.F("ctc_min")),
                name="policy_category_band_valid"),
        ]
        verbose_name_plural = "policy categories"

    def __str__(self) -> str:
        return f"{self.get_group_display()} Cat {self.number}"


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

    # Rules 2.B and 10 turn on this, so it is a field, not a guess from
    # the free-text `sector`.
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
            # An approval must record who made it, even if the service layer
            # is bypassed.
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


# -- Student placement profile (PC-UC-001, PC-BR-001) --------------------------
class StudentProfile(TimeStampedModel, UserScopedModel):
    """What a student maintains about themselves.

    No academic facts here: CPI, credits and backlogs come from the IAM
    projection, so a student can never type their own.
    """

    user_id = models.IntegerField(unique=True)      # narrower than the mixin

    headline = models.CharField(max_length=160, blank=True)
    about = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    alternate_email = models.EmailField(blank=True)

    skills = models.JSONField(default=list, blank=True)
    achievements = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)

    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)

    # Denormalised so an eligibility sweep does not recompute per student.
    completeness_percent = models.PositiveSmallIntegerField(default=0)
    is_complete = models.BooleanField(default=False, db_index=True)
    missing_fields = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "placement_student_profile"

    def __str__(self) -> str:
        return f"profile u{self.user_id} ({self.completeness_percent}%)"


class ProfileDocument(TimeStampedModel, UserScopedModel):
    """A document a student has attached to their profile.

    New rows are Drive links; rows written before the switch hold uploaded
    bytes. The CHECK constraint allows exactly one, so the download view
    always knows which it is holding.
    """

    KIND = [("resume", "Resume"), ("certificate", "Certificate"),
            ("offer_letter", "Offer letter"), ("other", "Other")]

    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE,
                                related_name="documents")
    kind = models.CharField(max_length=20, choices=KIND, default="other")
    title = models.CharField(max_length=160, blank=True)
    #: Display only, sanitised on the way in.
    original_filename = models.CharField(max_length=255, blank=True)

    #: Rebuilt from the file id, never a copy of what was submitted.
    drive_url = models.URLField(max_length=500, blank=True)
    drive_file_id = models.CharField(max_length=200, blank=True, db_index=True)

    #: Legacy upload path. Blank on every row written since the switch.
    storage_key = models.CharField(max_length=255, blank=True, null=True,
                                   unique=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "placement_profile_document"
        indexes = [models.Index(fields=["profile", "kind", "is_active"],
                                name="document_profile_idx")]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(drive_file_id="", storage_key__isnull=False)
                    | (~models.Q(drive_file_id="")
                       & models.Q(storage_key__isnull=True))
                ),
                name="document_is_link_or_file_not_both",
            ),
        ]

    @property
    def is_link(self) -> bool:
        return bool(self.drive_file_id)

    def __str__(self) -> str:
        return f"{self.kind}:{self.title or self.original_filename}"


class PlacementRegistration(TimeStampedModel, UserScopedModel):
    """A student opting into a season. Carries the counters the offer policy
    reads."""

    STATUS = [("registered", "Registered"), ("debarred", "Debarred"),
              ("opted_out", "Opted out")]

    policy = models.ForeignKey(PlacementPolicy, on_delete=models.PROTECT,
                               related_name="registrations")
    status = models.CharField(max_length=12, choices=STATUS, default="registered")
    offer_count = models.PositiveSmallIntegerField(default=0)
    best_accepted_tier_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    best_accepted_ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2,
                                                null=True, blank=True)

    # Rule 2.A, "one time only": locked on the first accepted offer from its
    # CTC band, or set ahead of time by the office.
    category_number = models.PositiveSmallIntegerField(null=True, blank=True)
    category_locked_at = models.DateTimeField(null=True, blank=True)

    # Rule 2: each category caps this.
    switches_used = models.PositiveSmallIntegerField(default=0)

    # Denormalised from the held offer so the policy check is one row read.
    held_is_marquee = models.BooleanField(default=False)
    held_sector_kind = models.CharField(max_length=8, blank=True)

    # Rules 19 and 21. Recorded only — debarment is a human decision.
    consent_failures = models.PositiveSmallIntegerField(default=0)
    reregistration_count = models.PositiveSmallIntegerField(default=0)
    registered_late = models.BooleanField(default=False)

    debarred_reason = models.CharField(max_length=300, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_registration"
        constraints = [
            models.UniqueConstraint(fields=["policy", "user_id"],
                                    name="registration_unique_per_season"),
        ]
        indexes = [models.Index(fields=["policy", "status"],
                                name="registration_season_idx")]

    def __str__(self) -> str:
        return f"reg u{self.user_id} {self.policy_id} {self.status}"


# -- Postings ------------------------------------------------------------------
class JobPosting(TimeStampedModel):
    """An opportunity. PC-BR-003 requires a description, criteria and a
    deadline before publishing, enforced by a database constraint."""

    STATUS = [("draft", "Draft"), ("pending_approval", "Pending TPO approval"),
              ("published", "Published"), ("closed", "Applications closed"),
              ("in_progress", "Selection in progress"),
              ("completed", "Completed"), ("cancelled", "Cancelled")]
    KIND = [("fte", "Full time"), ("internship", "Internship"),
            ("ppo", "Pre-placement offer")]

    company = models.ForeignKey(Company, on_delete=models.PROTECT,
                                related_name="postings")
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=KIND, default="fte")
    placement_year = models.CharField(max_length=12, db_index=True)   # "2026-27"

    description = models.TextField(blank=True)          # PC-BR-003 role description
    location = models.CharField(max_length=120, blank=True)
    ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    stipend_pm = models.DecimalField(max_digits=10, decimal_places=2,
                                     null=True, blank=True)
    bond_months = models.PositiveSmallIntegerField(null=True, blank=True)
    seats = models.PositiveSmallIntegerField(null=True, blank=True)

    eligibility_rule = models.JSONField(default=dict, blank=True)
    eligibility_rule_locked_at = models.DateTimeField(null=True, blank=True)

    # Rule 7: opens the process to placed students as well as unplaced.
    is_dream_slot = models.BooleanField(default=False)
    dream_slot_note = models.CharField(max_length=300, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)   # PC-BR-003 deadline
    published_at = models.DateTimeField(null=True, blank=True)

    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_by_recruiter = models.ForeignKey(
        RecruiterAccount, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="postings_created")

    class Meta:
        db_table = "placement_job_posting"
        indexes = [
            models.Index(fields=["placement_year", "status", "closes_at"],
                         name="posting_year_status_idx"),
            models.Index(fields=["company", "placement_year"],
                         name="posting_company_year_idx"),
        ]
        constraints = [
            # PC-BR-002: publishing freezes the rule so criteria cannot move
            # under applicants.
            models.CheckConstraint(
                condition=~Q(status="published")
                | Q(eligibility_rule_locked_at__isnull=False),
                name="posting_published_has_locked_rule",
            ),
            # PC-BR-003.
            models.CheckConstraint(
                condition=~Q(status="published")
                | (~Q(description="") & Q(closes_at__isnull=False)),
                name="posting_published_has_required_content",
            ),
            models.CheckConstraint(
                condition=Q(closes_at__isnull=True) | Q(opens_at__isnull=True)
                | Q(closes_at__gt=models.F("opens_at")),
                name="posting_window_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} @ {self.company_id}"


# -- Applications --------------------------------------------------------------
class Application(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("under_review", "Under review"), ("shortlisted", "Shortlisted"),
        ("interview_scheduled", "Interview scheduled"),
        ("selected", "Selected"),
        ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
        ("auto_withdrawn", "Withdrawn automatically"),
        ("offer_issued", "Offer issued"), ("offer_accepted", "Offer accepted"),
        ("offer_declined", "Offer declined"), ("offer_expired", "Offer expired"),
    ]

    posting = models.ForeignKey(JobPosting, on_delete=models.PROTECT,
                                related_name="applications")
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    # Frozen at submission, so a later CPI change never rewrites history.
    cpi_at_apply = models.DecimalField(max_digits=4, decimal_places=2,
                                       null=True, blank=True)
    semester_at_apply = models.PositiveSmallIntegerField(null=True, blank=True)
    standing_declared_seq_at_apply = models.IntegerField(null=True, blank=True)
    eligibility_snapshot = models.JSONField(default=dict, blank=True)

    resume = models.ForeignKey(ProfileDocument, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")
    cover_note = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "placement_application"
        constraints = [
            models.UniqueConstraint(fields=["posting", "user_id"],
                                    name="application_unique_per_posting"),
        ]
        indexes = [
            models.Index(fields=["posting", "status"], name="application_posting_idx"),
            models.Index(fields=["user_id", "status"], name="application_user_idx"),
        ]

    def __str__(self) -> str:
        return f"app#{self.pk} u{self.user_id} {self.status}"


class ApplicationTransition(models.Model):
    """Append-only audit of every status change (PC-BR-008)."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)       # institute person
    actor_recruiter_id = models.IntegerField(null=True, blank=True)  # or a recruiter
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "placement_application_transition"
        indexes = [models.Index(fields=["application", "at"],
                                name="transition_app_idx")]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status}->{self.to_status}"


# -- Interviews (PC-UC-009, PC-BR-011, PC-BR-012) ------------------------------
class InterviewRound(TimeStampedModel):
    """PC-BR-011: date, time slot and mode are all required."""

    KIND = [("test", "Written / online test"), ("gd", "Group discussion"),
            ("tech", "Technical interview"), ("hr", "HR interview"),
            ("other", "Other")]
    MODE = [("online", "Online"), ("offline", "Offline")]

    posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE,
                                related_name="rounds")
    seq = models.PositiveSmallIntegerField(default=1)
    kind = models.CharField(max_length=12, choices=KIND, default="tech")
    mode = models.CharField(max_length=8, choices=MODE)          # required
    starts_at = models.DateTimeField()                           # date + time slot
    ends_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    meeting_url = models.URLField(blank=True)
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    instructions = models.TextField(blank=True)

    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    scheduled_by_recruiter = models.ForeignKey(
        RecruiterAccount, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+")

    class Meta:
        db_table = "placement_interview_round"
        constraints = [
            models.UniqueConstraint(fields=["posting", "seq"],
                                    name="round_unique_seq_per_posting"),
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True)
                | Q(ends_at__gt=models.F("starts_at")),
                name="round_time_valid",
            ),
            # Online needs a link, offline needs a venue.
            models.CheckConstraint(
                condition=(Q(mode="online") & ~Q(meeting_url=""))
                | (Q(mode="offline") & ~Q(venue="")),
                name="round_has_a_location",
            ),
        ]
        indexes = [models.Index(fields=["posting", "seq"], name="round_posting_idx"),
                   models.Index(fields=["starts_at"], name="round_when_idx")]

    def __str__(self) -> str:
        return f"{self.posting_id} round {self.seq} ({self.kind})"


class RoundParticipation(TimeStampedModel):
    OUTCOME = [("pending", "Pending"), ("attended", "Attended"),
               ("absent", "Absent"), ("passed", "Passed"), ("failed", "Failed")]

    round = models.ForeignKey(InterviewRound, on_delete=models.CASCADE,
                              related_name="participants")
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="participations")
    outcome = models.CharField(max_length=12, choices=OUTCOME, default="pending")
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_round_participation"
        constraints = [
            models.UniqueConstraint(fields=["round", "application"],
                                    name="participation_unique"),
        ]
        indexes = [models.Index(fields=["round", "outcome"],
                                name="participation_round_idx")]

    def __str__(self) -> str:
        return f"r{self.round_id} app{self.application_id} {self.outcome}"


# -- Offers and placement records (PC-UC-005, PC-BR-013/014/015) ---------------
class Offer(TimeStampedModel, UserScopedModel):
    STATUS = [("issued", "Issued"), ("accepted", "Accepted"),
              ("declined", "Declined"), ("revoked", "Revoked"),
              ("superseded", "Superseded"), ("expired", "Expired")]

    application = models.OneToOneField(Application, on_delete=models.PROTECT,
                                       related_name="offer")
    posting = models.ForeignKey(JobPosting, on_delete=models.PROTECT,
                                related_name="offers")
    ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tier_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    is_dream = models.BooleanField(default=False)

    status = models.CharField(max_length=12, choices=STATUS, default="issued")
    respond_by = models.DateTimeField()                # PC-BR-013, always set
    responded_at = models.DateTimeField(null=True, blank=True)

    # Machine-readable justification, so an appeal has a reason.
    policy_decision = models.JSONField(default=dict, blank=True)

    issued_by_user_id = models.IntegerField(null=True, blank=True)
    issued_by_recruiter = models.ForeignKey(
        RecruiterAccount, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+")
    letter = models.ForeignKey(ProfileDocument, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "placement_offer"
        indexes = [
            models.Index(fields=["user_id", "status"], name="offer_user_idx"),
            models.Index(fields=["posting", "status"], name="offer_posting_idx"),
            models.Index(fields=["status", "respond_by"], name="offer_expiry_idx"),
        ]

    def __str__(self) -> str:
        return f"offer#{self.pk} u{self.user_id} {self.status}"


class PlacementRecord(TimeStampedModel, UserScopedModel):
    """Written when an offer is accepted (PC-BR-014).

    The partial unique index is the backstop: even bypassing the service, a
    student cannot hold two active placements in one season.
    """

    policy = models.ForeignKey(PlacementPolicy, on_delete=models.PROTECT,
                               related_name="records")
    offer = models.OneToOneField(Offer, on_delete=models.PROTECT,
                                 related_name="record")
    company = models.ForeignKey(Company, on_delete=models.PROTECT,
                                related_name="records")
    posting = models.ForeignKey(JobPosting, on_delete=models.PROTECT,
                                related_name="records")
    ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    kind = models.CharField(max_length=12, default="fte")
    is_active = models.BooleanField(default=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "placement_record"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "policy"], condition=Q(is_active=True),
                name="one_active_placement_per_student_per_season",
            ),
        ]
        indexes = [
            models.Index(fields=["policy", "company"], name="record_season_idx"),
            models.Index(fields=["user_id", "is_active"], name="record_user_idx"),
        ]

    def __str__(self) -> str:
        return f"placed u{self.user_id} @{self.company_id}"


# -- Announcements and notifications (PC-UC-013/020, PC-BR-017/018/021) --------
class Announcement(TimeStampedModel):
    """PC-BR-017 bounds the topics. PC-BR-018 keeps history, so withdrawal
    sets a flag rather than deleting."""

    TOPIC = [("drive", "Placement drive"), ("company_visit", "Company visit"),
             ("training", "Training session"), ("workshop", "Workshop"),
             ("internship", "Internship programme"), ("general", "General")]
    AUDIENCE = [("students", "All students"),
                ("registered", "Registered students"),
                ("alumni", "Alumni"), ("all", "Everyone")]

    title = models.CharField(max_length=200)
    body = models.TextField()
    topic = models.CharField(max_length=20, choices=TOPIC, default="general")
    audience = models.CharField(max_length=12, choices=AUDIENCE, default="students")
    placement_year = models.CharField(max_length=12, blank=True, db_index=True)

    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    published_by_role = models.CharField(max_length=60, blank=True)
    is_withdrawn = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "placement_announcement"
        indexes = [
            models.Index(fields=["-published_at"], name="announcement_recent_idx"),
            models.Index(fields=["audience", "is_withdrawn"],
                         name="announcement_audience_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class NotificationOutbox(TimeStampedModel):
    """A notification PCMS decided to send (PC-BR-021).

    Written in the same transaction as the event that caused it and drained by
    a separate worker, so an offer and its email commit together or not at all.
    `dedupe_key` makes redelivery idempotent.
    """

    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"),
              ("suppressed", "Suppressed")]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)

    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_email = models.EmailField(blank=True)

    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="outbox_pending_idx"),
            models.Index(fields=["recipient_user_id", "-created_at"],
                         name="outbox_recipient_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id or self.recipient_email}"


class PlacementStatsSnapshot(TimeStampedModel):
    """Materialised aggregate for the statistics screens (PC-UC-011/012).

    Reports read snapshots, never transactional tables, so a busy stats page
    cannot slow down an application deadline.
    """

    policy = models.ForeignKey(PlacementPolicy, on_delete=models.CASCADE,
                               related_name="snapshots")
    dimension = models.CharField(max_length=32)      # overall | discipline | company
    dimension_value = models.CharField(max_length=120, blank=True)

    registered = models.IntegerField(default=0)
    placed = models.IntegerField(default=0)
    offers = models.IntegerField(default=0)
    companies_participated = models.IntegerField(default=0)
    median_ctc = models.DecimalField(max_digits=8, decimal_places=2,
                                     null=True, blank=True)
    mean_ctc = models.DecimalField(max_digits=8, decimal_places=2,
                                   null=True, blank=True)
    max_ctc = models.DecimalField(max_digits=8, decimal_places=2,
                                  null=True, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "placement_stats_snapshot"
        constraints = [
            models.UniqueConstraint(fields=["policy", "dimension", "dimension_value"],
                                    name="snapshot_unique_dimension"),
        ]

    def __str__(self) -> str:
        return f"{self.policy_id} {self.dimension}={self.dimension_value}"
