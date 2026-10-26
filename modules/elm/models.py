"""ELM data model.

People are referenced by IAM user_id only. Names, kind (faculty/staff) and
department come from modules.directory.contracts, never from its models.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class PublishState(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    RETIRED = "retired", "Retired"


class LeavePolicy(TimeStampedModel):
    """Versioned policy parameters (BR-EL-030). Only one published version is in force."""
    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=PublishState.choices,
                              default=PublishState.DRAFT, db_index=True)
    effective_from = models.DateField(null=True, blank=True)
    # e.g. {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "VL": 60}
    params = models.JSONField(default=dict)  #


class HolidayCalendar(TimeStampedModel):
    """Versioned holiday / RH / vacation calendar (BR-EL-031)."""
    year = models.PositiveIntegerField(db_index=True)
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=PublishState.choices,
                              default=PublishState.DRAFT, db_index=True)

    class Meta:
        unique_together = [("year", "version")]


class CalendarDay(TimeStampedModel):
    KIND_CHOICES = [("holiday", "Closed holiday"), ("rh", "Restricted holiday"),
                    ("vacation", "Vacation period day")]
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="days")
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("calendar", "date", "kind")]


class LeaveAccount(TimeStampedModel):
    """One balance per employee, year and leave type."""
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveIntegerField()
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        unique_together = [("user_id", "year", "leave_type")]


class LeaveRequest(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_SUBSTITUTE = "awaiting_substitute", "Awaiting Substitute Response"
        AWAITING_UNIT_HEAD = "awaiting_unit_head", "Awaiting Unit Head Review"
        AWAITING_ESTABLISHMENT = "awaiting_establishment", "Awaiting Establishment Routing"
        AWAITING_FINAL = "awaiting_final", "Awaiting Final Sanction Decision"
        AWAITING_DIRECTOR_SELF = "awaiting_director_self", "Awaiting Director Self-Sanction"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLATION_PENDING = "cancellation_pending", "Cancellation Pending"
        CANCELLED = "cancelled", "Cancelled"
        AWAITING_RESUMPTION = "awaiting_resumption", "Awaiting Resumption"
        CLOSED = "closed", "Closed"

    class Kind(models.TextChoices):
        ORIGINAL = "original", "Original"
        EXTENSION = "extension", "Extension"
        CANCELLATION = "cancellation", "Cancellation"

    class Half(models.TextChoices):
        NONE = "", "Full day"
        FIRST = "first", "First half"
        SECOND = "second", "Second half"

    applicant_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.ORIGINAL)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="children")
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    half = models.CharField(max_length=6, choices=Half.choices, blank=True, default="")
    reason = models.TextField()
    days = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # chargeable days
    status = models.CharField(max_length=24, choices=Status.choices,
                              default=Status.DRAFT, db_index=True)
    substitute_required = models.BooleanField(default=False)
    # Station Leave lives on the same application (BR-EL-013), not a separate request.
    outside_station = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True)
    station_contact = models.CharField(max_length=64, blank=True)
    medical_evidence_ref = models.CharField(max_length=255, blank=True)  # COL (BR-EL-009)


class SubstituteAssignment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        SUPERSEDED = "superseded", "Superseded"

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="substitutes")
    nominee_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)


class WorkflowTask(TimeStampedModel):
    class Stage(models.TextChoices):
        SUBSTITUTE = "substitute", "Substitute response"
        UNIT_HEAD = "unit_head", "Unit Head review"
        ESTABLISHMENT = "establishment", "Establishment routing"
        FINAL = "final", "Final sanction"
        VERIFY_RESUMPTION = "verify_resumption", "Verify resumption"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"
        SUPERSEDED = "superseded", "Superseded"
        CANCELLED = "cancelled", "Cancelled"

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="tasks")
    stage = models.CharField(max_length=20, choices=Stage.choices)
    assignee_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.OPEN, db_index=True)


class Decision(TimeStampedModel):
    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RECOMMENDED = "recommended", "Recommended"
        NOT_RECOMMENDED = "not_recommended", "Not Recommended"

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="decisions")
    task = models.ForeignKey(WorkflowTask, null=True, blank=True, on_delete=models.SET_NULL)
    actor_id = models.IntegerField()
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    remarks = models.TextField(blank=True)


class LeaveTransaction(TimeStampedModel):
    """Append-only ledger. Balances change only by adding a row here."""
    class Kind(models.TextChoices):
        CREDIT = "credit", "Annual credit"
        DEBIT = "debit", "Approved leave"
        RESTORE = "restore", "Restored after early resumption"
        LAPSE = "lapse", "Year-end lapse"
        CONVERT_OUT = "convert_out", "VL converted"
        CONVERT_IN = "convert_in", "EL from VL conversion"
        CARRY_FORWARD = "carry_forward", "Carry forward"
        OFFLINE = "offline", "Offline-sanctioned entry"

    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT, related_name="transactions")
    kind = models.CharField(max_length=14, choices=Kind.choices)
    amount = models.DecimalField(max_digits=7, decimal_places=2)  # signed
    request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True)



class HierarchyRule(TimeStampedModel):
    """Who acts at each stage of the approval path (BR-EL-019).

    IAM has no 'unit head of X' lookup, so ELM holds the effective hierarchy itself.
    A blank unit, applicant_kind or leave_type means 'any'. Only published rules apply.
    """
    class Stage(models.TextChoices):
        UNIT_HEAD = "unit_head", "Unit Head"
        ESTABLISHMENT = "establishment", "Establishment role"
        FINAL = "final", "Final sanctioning authority"
        DIRECTOR = "director", "Director (self-sanction rule)"

    status = models.CharField(max_length=12, choices=PublishState.choices,
                              default=PublishState.DRAFT, db_index=True)
    stage = models.CharField(max_length=14, choices=Stage.choices)
    unit = models.CharField(max_length=80, blank=True)            # department / section / office
    applicant_kind = models.CharField(max_length=16, blank=True)  # faculty | staff | blank
    leave_type = models.CharField(max_length=3, blank=True, choices=LeaveType.choices)
    approver_id = models.IntegerField(db_index=True)              # IAM user id

    class Meta:
        indexes = [models.Index(fields=["status", "stage"], name="elm_hier_status_stage_idx")]


class Resumption(TimeStampedModel):
    """Return to duty after EL/COL/VL (BR-EL-027, BR-EL-028)."""
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting verification"
        VERIFIED = "verified", "Verified"

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="resumptions")
    actual_date = models.DateField()          # first day back at work
    details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    verifier_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    unused_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)



class OfflineRecord(TimeStampedModel):
    """Evidence for leave already sanctioned on paper (BR-EL-029). Not a second approval."""
    request = models.OneToOneField(LeaveRequest, on_delete=models.CASCADE,
                                   related_name="offline_record")
    recorded_by = models.IntegerField()
    reference = models.CharField(max_length=255)       # order / file number
    sanctioned_by = models.CharField(max_length=120)
    sanctioned_on = models.DateField()


class SlaLog(TimeStampedModel):
    """One row per reminder or escalation actually issued (SRS-EL-106)."""
    class Action(models.TextChoices):
        REMINDER = "reminder", "Reminder"
        ESCALATION = "escalation", "Escalation"

    task = models.ForeignKey(WorkflowTask, on_delete=models.CASCADE, related_name="sla_logs")
    action = models.CharField(max_length=12, choices=Action.choices)
    notified_id = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("task", "action")]    # at most one of each per task
