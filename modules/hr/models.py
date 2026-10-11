"""HR domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database.

Fresh domain design — the deprecated establishment/hr2 apps are not ported.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

class Department(TimeStampedModel):
    """An organisational unit within the institute."""

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="children",
    )
    head_user_id = models.IntegerField(null=True, blank=True)  # no FK across boundaries
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hr_department"
        indexes = [
            models.Index(fields=["is_active", "name"], name="dept_active_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Employment contracts
# ---------------------------------------------------------------------------

class EmploymentContract(TimeStampedModel):
    """One contract between the institute and a person.

    A person may hold multiple contracts over time (e.g. temporary → permanent).
    Only one may be *active* at a time — enforced by a partial unique index.
    """

    KIND = [
        ("permanent",   "Permanent"),
        ("temporary",   "Temporary"),
        ("contractual", "Contractual"),
        ("intern",      "Intern / Trainee"),
    ]
    STATUS = [
        ("active",    "Active"),
        ("ended",     "Ended"),
        ("suspended", "Suspended"),
    ]

    user_id    = models.IntegerField(db_index=True)   # IAM erp_user_id — NO FK
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="contracts",
    )
    title      = models.CharField(max_length=120)
    kind       = models.CharField(max_length=20, choices=KIND, default="permanent")
    status     = models.CharField(max_length=20, choices=STATUS, default="active")

    starts_on  = models.DateField()
    ends_on    = models.DateField(null=True, blank=True)

    # Attribution — who ended or suspended it (IAM erp_user_id, NO FK)
    ended_by_user_id   = models.IntegerField(null=True, blank=True)
    end_reason         = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "hr_employment_contract"
        constraints = [
            # Only one active contract per person at a time.
            models.UniqueConstraint(
                fields=["user_id"],
                condition=Q(status="active"),
                name="contract_one_active_per_user",
            ),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(ends_on__gte=models.F("starts_on")),
                name="contract_dates_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["active", "ended", "suspended"]),
                name="contract_status_valid",
            ),
            # An ended contract must record who ended it.
            models.CheckConstraint(
                condition=~Q(status="ended") | Q(ended_by_user_id__isnull=False),
                name="contract_ended_is_attributed",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"],   name="contract_user_idx"),
            models.Index(fields=["department", "status"], name="contract_dept_idx"),
            models.Index(fields=["status", "-starts_on"], name="contract_status_recent_idx"),
        ]

    def __str__(self) -> str:
        return f"contract u{self.user_id} ({self.kind}, {self.status})"
