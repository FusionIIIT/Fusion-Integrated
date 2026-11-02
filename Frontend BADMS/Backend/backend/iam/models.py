"""IAM tables. These live in system_db, NOT in the ERP.

Why a token table of our own instead of reusing rest_framework.authtoken:
that model has a ForeignKey to AUTH_USER_MODEL, which the router sends to
system_db — the *operator* pool. The people signing in here are the ~3,277 ERP
users in a different database entirely, so their sessions cannot FK to anything.
`erp_user_id` is therefore a plain integer, matching how Fusion-Integrated
references people.
"""
import binascii
import hashlib
import os
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone


def _make_key() -> str:
    """Unused: kept only because migration 0001 names it as a field default."""
    return binascii.hexlify(os.urandom(24)).decode()


class IamToken(models.Model):
    """A session for an ERP user. `key` is the SHA-256 of the bearer token,
    so a dump of system_db yields no usable session."""

    key = models.CharField(max_length=64, primary_key=True)
    erp_user_id = models.IntegerField(db_index=True)
    username = models.CharField(max_length=150, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    #: Set in memory by `issue()`, never persisted.
    raw_key: str = ""

    class Meta:
        db_table = "iam_token"
        indexes = [
            models.Index(fields=["erp_user_id", "-created_at"],
                         name="iamtoken_user_recent_idx"),
        ]

    @staticmethod
    def hash_raw(raw: str) -> str:
        # A plain digest: CSPRNG input, so nothing for a slow KDF to protect.
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, *, erp_user_id: int, username: str, ttl_hours: int = 12):
        """Mint a session. The raw token is on `.raw_key`, once."""
        raw = secrets.token_urlsafe(32)
        token = cls.objects.create(
            key=cls.hash_raw(raw), erp_user_id=erp_user_id, username=username,
            expires_at=timezone.now() + timedelta(hours=ttl_hours),
        )
        token.raw_key = raw
        return token

    @classmethod
    def resolve(cls, raw: str) -> "IamToken | None":
        if not raw:
            return None
        return cls.objects.filter(key=cls.hash_raw(raw)).first()

    @property
    def is_live(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def touch(self) -> None:
        """Record use, at most once a minute — an unconditional save here is a
        DB write per request, which is what slowed the legacy app."""
        now = timezone.now()
        if self.last_used_at and (now - self.last_used_at) < timedelta(minutes=1):
            return
        type(self).objects.filter(pk=self.pk).update(last_used_at=now)

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])


class IamServiceToken(models.Model):
    """A credential for another *service*, not a person.

    Fusion-Integrated reads the directory server-to-server: a report listing
    300 applicants by name has no user session behind it.

    Stored as a SHA-256 digest — the raw value is shown once at creation, so a
    dump of system_db yields no working credential. Narrow by design: it
    authenticates on the directory endpoints only and cannot reach /me,
    because there is no person for it to be.
    """

    PREFIX = "fsvc_"          # makes the value greppable in a leak or a log

    name = models.CharField(max_length=64, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iam_service_token"
        ordering = ["name"]

    @staticmethod
    def hash_raw(raw: str) -> str:
        # A plain digest, not a password hash: the input is 32 bytes of CSPRNG
        # output, so there is nothing for a slow KDF to protect against.
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, name: str) -> tuple["IamServiceToken", str]:
        """Returns (row, raw). The raw value is never persisted."""
        raw = cls.PREFIX + secrets.token_urlsafe(32)
        return cls.objects.create(name=name, token_hash=cls.hash_raw(raw)), raw

    def rotate(self) -> str:
        """New secret under the same name; the old value stops working at once."""
        raw = type(self).PREFIX + secrets.token_urlsafe(32)
        self.token_hash = type(self).hash_raw(raw)
        self.is_active = True
        self.last_used_at = None
        self.save(update_fields=["token_hash", "is_active", "last_used_at"])
        return raw

    @classmethod
    def resolve(cls, raw: str) -> "IamServiceToken | None":
        if not raw or not raw.startswith(cls.PREFIX):
            return None
        return cls.objects.filter(token_hash=cls.hash_raw(raw),
                                  is_active=True).first()

    def touch(self) -> None:
        """Record use, but at most once a minute.

        A write per request is exactly the pattern that made the legacy app slow
        (SESSION_SAVE_EVERY_REQUEST); minute granularity answers "is this token
        still in use?" just as well.
        """
        now = timezone.now()
        if self.last_used_at and (now - self.last_used_at) < timedelta(minutes=1):
            return
        type(self).objects.filter(pk=self.pk).update(last_used_at=now)

    def __str__(self) -> str:
        return f"{self.name}{'' if self.is_active else ' (revoked)'}"


class RolePermission(models.Model):
    """Designation name -> one permission code.

    The ERP has designations and a module-access table, but no concept of a
    permission. Rather than invent a parallel role system, this maps the
    designations that already exist onto the permission codes the platform
    checks. The platform owns the mapping; seed_iam_permissions stores it.
    """

    designation = models.CharField(max_length=155, db_index=True)
    permission = models.CharField(max_length=100)

    class Meta:
        db_table = "iam_role_permission"
        constraints = [
            models.UniqueConstraint(fields=["designation", "permission"],
                                    name="iam_role_permission_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.designation}:{self.permission}"


class LoginAttempt(models.Model):
    """Recorded for every attempt, including ones against usernames that do not
    exist — that is precisely the signal for enumeration and stuffing."""

    username = models.CharField(max_length=150, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    outcome = models.CharField(max_length=24)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "iam_login_attempt"
        indexes = [models.Index(fields=["username", "-at"],
                                name="iamattempt_user_recent_idx")]


# ---------------------------------------------------------------------------
# The identity projection (Phase 1 of ADR-0014).
#
# A synced copy of who exists, held in system_db. Today the ERP is the source
# of truth and these tables are downstream of it; in Phase 2 the arrow flips
# and these become authoritative, with the ERP receiving a projection instead.
# The schema does not change when that happens — only the direction of sync.
#
# Which is why these are NOT named *_cache: they are the destination.
# ---------------------------------------------------------------------------
class IamUser(models.Model):
    """A person, projected from the ERP's auth_user + extrainfo + student/faculty."""

    KINDS = [("student", "Student"), ("faculty", "Faculty"),
             ("staff", "Staff"), ("compounder", "Compounder"),
             # The ERP has nothing on which to classify this account.
             ("unknown", "Unclassified")]

    erp_user_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=300, blank=True)
    email = models.CharField(max_length=254, blank=True)
    kind = models.CharField(max_length=20, choices=KINDS, default="unknown",
                            db_index=True)
    is_active = models.BooleanField(default=True)

    # Copied so login does not need the ERP. If it goes stale (a reset done in
    # the ERP), authenticate() falls back to a live check and re-syncs — see
    # iam/sync.py.
    password_hash = models.CharField(max_length=128, blank=True)

    department = models.CharField(max_length=100, blank=True)
    programme = models.CharField(max_length=40, blank=True)
    discipline = models.CharField(max_length=40, blank=True, db_index=True)
    batch_year = models.IntegerField(null=True, blank=True)

    #: Maintained on the portal's profile page, so every service reads one resume.
    resume_link = models.CharField(max_length=500, blank=True)
    profile_completed = models.BooleanField(default=False)

    #: Which designation they chose to work as. Not an authorisation input.
    last_selected_role = models.CharField(max_length=155, blank=True)

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iam_user"
        indexes = [
            models.Index(fields=["kind", "discipline"], name="iamuser_kind_disc_idx"),
            models.Index(fields=["is_active"], name="iamuser_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.username}({self.erp_user_id})"


class IamUserDesignation(models.Model):
    """Which designations a person currently works as.

    Projected from globals_holdsdesignation filtered on `working` — the field
    the ERP's own model docstring says to use for permissions.
    """

    erp_user_id = models.IntegerField(db_index=True)
    designation = models.CharField(max_length=155, db_index=True)

    class Meta:
        db_table = "iam_user_designation"
        constraints = [
            models.UniqueConstraint(fields=["erp_user_id", "designation"],
                                    name="iam_user_designation_unique"),
        ]


class IamDesignationModule(models.Model):
    """Which modules a designation may enter.

    Every service publishes its own modules and owns those rows alone. Without
    a publisher, the second writer's rows look like stale rows to the first and
    a seed silently revokes a working module. Reads are the union across
    publishers — a grant from any of them is a grant.
    """

    #: Rows written before manifests were attributed to a publisher.
    MANIFEST = "manifest"
    MANIFEST_PREFIX = "manifest:"

    designation = models.CharField(max_length=155, db_index=True)
    module_code = models.CharField(max_length=48)
    #: "manifest:<publisher>" — one value per writer, never shared.
    source = models.CharField(max_length=32)

    @classmethod
    def manifest_source(cls, publisher: str) -> str:
        return f"{cls.MANIFEST_PREFIX}{publisher}"

    class Meta:
        db_table = "iam_designation_module"
        constraints = [
            models.UniqueConstraint(
                fields=["designation", "module_code", "source"],
                name="iam_designation_module_unique"),
        ]


class IamUserAcademic(models.Model):
    """A student's academic standing at their most recently DECLARED semester.

    Placement eligibility needs a CGPA (PC-BR-004) and the ERP has no readable
    one — `academic_information_student.cpi` is permanently 0.0 and the real
    number is recomputed per request. So it is computed here by a replica of
    the ERP's algorithm (iam/grades.py) and projected alongside identity.

    "Declared" is the whole point: an undeclared student has NO ROW rather
    than a zero, so eligibility fails closed instead of reading them as very
    weak. The sync is the only writer.
    """

    erp_user_id = models.IntegerField(primary_key=True)
    roll_no = models.CharField(max_length=32, db_index=True)

    cpi = models.DecimalField(max_digits=4, decimal_places=1)
    earned_credits = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    cpi_denominator_credits = models.DecimalField(max_digits=7, decimal_places=2,
                                                  default=0)
    active_backlogs = models.IntegerField(default=0)
    courses_counted = models.IntegerField(default=0)

    # Provenance. A CPI without its semester is unusable: the placement UI must
    # render "8.1 · Sem 5 (Odd)" so nobody argues about a stale number.
    semester = models.IntegerField()
    semester_type = models.CharField(max_length=20, blank=True)
    declared_seq = models.IntegerField(db_index=True)
    erp_announcement_id = models.IntegerField(null=True, blank=True)

    programme = models.CharField(max_length=40, blank=True)
    computed_by = models.CharField(max_length=64, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iam_user_academic"
        indexes = [
            models.Index(fields=["cpi"], name="iamacad_cpi_idx"),
            models.Index(fields=["active_backlogs"], name="iamacad_backlog_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.roll_no} cpi={self.cpi} sem={self.semester}"


class SyncRun(models.Model):
    """One execution of the ERP -> IAM projection. Observability, and the
    answer to "how stale is this?"."""

    STATUS = [("running", "Running"), ("succeeded", "Succeeded"),
              ("failed", "Failed")]

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="running")
    users_seen = models.IntegerField(default=0)
    users_written = models.IntegerField(default=0)
    designations_written = models.IntegerField(default=0)
    module_grants_written = models.IntegerField(default=0)
    role_violations = models.IntegerField(default=0)
    academics_written = models.IntegerField(default=0)
    deactivated = models.IntegerField(default=0)
    #: Usernames the ERP moved to a new account, freed from their old holder.
    usernames_released = models.IntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "iam_sync_run"
        ordering = ["-started_at"]

    @property
    def duration_seconds(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()


class IamRole(models.Model):
    """The role catalogue: what a designation IS, and who may hold it.

    Fusion has one *basic* role per person — student, faculty or staff — which
    comes from the ERP and nobody assigns. Everything else is held on top of it,
    and a person may hold several: a faculty member is an Associate Professor and
    a HOD and the Dean Academic at once.

    What the ERP cannot express is that the two kinds are not interchangeable.
    `globals_holdsdesignation` is a plain join table, so nothing stops a student
    being made Dean Academic — and in the live data, one is. This table is the
    missing half: each role says which basic roles may hold it.
    """

    BASIC = "basic"
    RANK = "rank"
    OFFICE = "office"
    FUNCTIONAL = "functional"
    CATEGORIES = [
        (BASIC, "Basic role — what a person is"),
        (RANK, "Academic rank"),
        (OFFICE, "Office held"),
        (FUNCTIONAL, "Functional role"),
    ]

    code = models.CharField(max_length=155, unique=True)
    label = models.CharField(max_length=155, blank=True)
    category = models.CharField(max_length=16, choices=CATEGORIES)
    #: Basic roles that may hold this one. Stored sorted and comma-joined; a
    #: list column would need a JSONField for three short words.
    allowed_kinds = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "iam_role"
        ordering = ["category", "code"]

    def __str__(self) -> str:
        return self.code

    @property
    def kinds(self) -> set[str]:
        return {k for k in self.allowed_kinds.split(",") if k}

    def may_be_held_by(self, kind: str) -> bool:
        return kind in self.kinds


class IamRoleViolation(models.Model):
    """A held role its holder's basic role does not permit.

    Rewritten on every sync, so the table is always the current picture rather
    than a log. Reported by default and only refused once the policy is switched
    to enforce — the catalogue is a claim about institute practice, and refusing
    on day one would lock out whoever the claim is wrong about.
    """

    erp_user_id = models.IntegerField(db_index=True)
    username = models.CharField(max_length=150)
    kind = models.CharField(max_length=20)
    designation = models.CharField(max_length=155)
    enforced = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iam_role_violation"
        ordering = ["username", "designation"]
        constraints = [
            models.UniqueConstraint(fields=["erp_user_id", "designation"],
                                    name="iam_role_violation_unique"),
        ]


class IamModule(models.Model):
    """A module's sidebar entry, published by the service that owns it.

    The grants say which modules you may enter; these say what they are called
    and where they live. Held here so one sidebar can span every Fusion app
    rather than each app drawing only the modules it happens to implement.
    """

    STATUS = [("planned", "Planned"), ("active", "Active"),
              ("deprecated", "Deprecated")]

    code = models.CharField(max_length=48, db_index=True)
    label = models.CharField(max_length=80)
    icon = models.CharField(max_length=48, default="FaCircle")
    base_path = models.CharField(max_length=80)
    nav_section = models.CharField(max_length=48, default="Modules")
    sort_order = models.PositiveSmallIntegerField(default=100)
    status = models.CharField(max_length=16, choices=STATUS, default="planned")
    #: Which app serves these paths; the client turns it into a base URL.
    app = models.CharField(max_length=32)
    source = models.CharField(max_length=32)

    class Meta:
        db_table = "iam_module"
        ordering = ["nav_section", "sort_order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["code", "source"],
                                    name="iam_module_unique_per_publisher"),
        ]

    def __str__(self) -> str:
        return self.code


class IamNavItem(models.Model):
    """A link inside a module, hidden unless the caller holds its permission."""

    module = models.ForeignKey(IamModule, on_delete=models.CASCADE,
                               related_name="nav_items")
    code = models.CharField(max_length=80)
    label = models.CharField(max_length=80)
    icon = models.CharField(max_length=48, default="FaCircle")
    to = models.CharField(max_length=160)
    required_permission = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    source = models.CharField(max_length=32)

    class Meta:
        db_table = "iam_nav_item"
        ordering = ["sort_order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["code", "source"],
                                    name="iam_nav_item_unique_per_publisher"),
        ]

    def __str__(self) -> str:
        return self.code
