"""Leave Management data models.

All fields are syntactically valid Django fields. Models contain all data needed
by the provided leave workflows, policy/calendar/hierarchy configuration,
balances, audit, notifications, SLA and year-end processing.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel

LeaveCategory = Literal[
    "CL",  # Casual Leave
    "RH",  # Restricted Holiday
    "SCL", # Special Casual Leave
    "EL",  # Earned Leave
    "COL", # Commuted Leave
    "VL",  # Vacation Leave
]

LeaveStatus = Literal[
    "DRAFT",
    "AWAITING_SUBSTITUTE",
    "AWAITING_UNIT_HEAD",
    "AWAITING_ESTABLISHMENT",
    "AWAITING_FINAL_SANCTION",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
    "EXTENSION_PENDING",
    "EXTENDED",
    "RESUMPTION_PENDING",
    "RESUMPTION_REVIEWED",
    "WITHDRAWN",
]

ResumptionType = Literal["NORMAL", "EARLY", "LATE"]


class LeavePolicy(TimeStampedModel):
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    CL_DAYS = models.IntegerField(default=8, verbose_name="Casual Leave days")
    RH_DAYS = models.IntegerField(default=2, verbose_name="Restricted Holiday days")
    SCL_MAX_DAYS = models.IntegerField(default=15, verbose_name="Special Casual Leave max days")
    EL_DAYS = models.IntegerField(default=30, verbose_name="Earned Leave days (non-faculty)")
    COL_DAYS = models.IntegerField(default=20, verbose_name="Commuted Leave days")
    VL_DAYS = models.IntegerField(default=60, verbose_name="Vacation Leave days (faculty)")
    VL_TO_EL_RATIO = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal("0.5"), verbose_name="VL to EL conversion ratio (2:1)")

    class Meta:
        verbose_name = "Leave Policy"
        verbose_name_plural = "Leave Policies"


class HolidayCalendar(TimeStampedModel):
    """Currently effective published holiday/RH calendar."""
    year = models.IntegerField(unique=True, verbose_name="Year")
    is_effective = models.BooleanField(default=False, verbose_name="Is currently effective")
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")

    class Meta:
        verbose_name = "Holiday Calendar"
        ordering = ["-year"]


class Holiday(TimeStampedModel):
    """Individual holiday or Restricted Holiday entry."""
    calendar = models.ForeignKey(
        "HolidayCalendar",
        on_delete=models.CASCADE,
        related_name="holidays",
        verbose_name="Calendar",
    )
    date = models.DateField(unique=True, verbose_name="Date")
    type = models.CharField(max_length=20, choices=[("HOLIDAY", "Holiday"), ("RH", "Restricted Holiday")], verbose_name="Type")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    class Meta:
        verbose_name = "Holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_calendar_date")
        ]


class VacationPeriod(TimeStampedModel):
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year = models.IntegerField(verbose_name="Year")
    start_date = models.DateField(verbose_name="Start date")
    end_date = models.DateField(verbose_name="End date")
    name = models.CharField(max_length=100, verbose_name="Name")

    class Meta:
        verbose_name = "Vacation Period"
        ordering = ["year", "start_date"]


class OrganizationalUnit(TimeStampedModel):
    """Department, Section, or Office."""
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    name = models.CharField(max_length=200, verbose_name="Name")
    parent_unit_id = models.IntegerField(null=True, blank=True, verbose_name="Parent unit ID", db_index=True)
    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")

    class Meta:
        verbose_name = "Organizational Unit"
        ordering = ["code"]


class LeaveHierarchy(TimeStampedModel):
    """Configured hierarchy for leave sanctioning paths."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        verbose_name = "Leave Hierarchy"
        ordering = ["name"]


class LeaveHierarchyStep(TimeStampedModel):
    """Step in a leave sanctioning hierarchy."""
    hierarchy = models.ForeignKey(
        "LeaveHierarchy",
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Hierarchy",
    )
    order = models.IntegerField(verbose_name="Order")
    role_code = models.CharField(max_length=50, verbose_name="Role code")
    is_establishment_step = models.BooleanField(default=False, verbose_name="Is establishment step")

    class Meta:
        verbose_name = "Hierarchy Step"
        ordering = ["hierarchy", "order"]
        constraints = [
            models.UniqueConstraint(fields=["hierarchy", "order"], name="unique_hierarchy_order")
        ]


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave application record.

Not modified in place after submission. Changes require withdrawal and new application.
"""
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_FINAL_SANCTION", "Awaiting Final Sanction Decision"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("EXTENSION_PENDING", "Extension Pending"),
        ("EXTENDED", "Extended"),
        ("RESUMPTION_PENDING", "Resumption Pending"),
        ("RESUMPTION_REVIEWED", "Resumption Reviewed"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    category = models.CharField(max_length=3, choices=[
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ], verbose_name="Leave Category")

    user_id = models.IntegerField(db_index=True, verbose_name="Applicant user ID")

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    purpose = models.TextField(verbose_name="Purpose/Reason")
    station_leave_required = models.BooleanField(default=False, verbose_name="Station Leave Required")
    station_leave_details = models.JSONField(blank=True, default=dict, verbose_name="Station Leave Details")

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Substitute user ID")
    substitute_consent_given = models.BooleanField(default=False, verbose_name="Substitute Consent Given")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT", verbose_name="Status")

    unit_head_user_id = models.IntegerField(db_index=True, verbose_name="Unit Head user ID")
    hierarchy_step_order = models.IntegerField(verbose_name="Hierarchy Step Order")

    final_decision_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Final Decision User ID")
    final_decision_date = models.DateField(null=True, blank=True, verbose_name="Final Decision Date")
    final_decision_type = models.CharField(max_length=20, choices=[
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ], null=True, blank=True, verbose_name="Final Decision Type")

    # Extension fields
    original_application_id = models.IntegerField(null=True, blank=True, verbose_name="Original Application ID")
    extension_incremental_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Extension Incremental Days")

    # Resumption fields
    actual_resumption_date = models.DateField(null=True, blank=True, verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], null=True, blank=True, verbose_name="Resumption Type")

    # Audit fields
    created_by_user_id = models.IntegerField(db_index=True, verbose_name="Created by user ID")
    updated_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Updated by user ID")
    submitted_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Submitted by user ID")
    withdrawn_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Withdrawn by user ID")
    cancelled_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Cancelled by user ID")

    class Meta:
        verbose_name = "Leave Application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="idx_leave_user_status"),
            models.Index(fields=["start_date", "end_date"], name="idx_leave_dates"),
        ]

    def __str__(self):
        return f"{self.category} {self.start_date} to {self.end_date} ({self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Employee leave balance snapshot.

Maintained per employee. Updated on approval, cancellation, year-end processing,
and VL-to-EL conversion.
"""
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")
    effective_date = models.DateField(verbose_name="Effective Date", db_index=True)

    cl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="CL Balance")
    rh_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="RH Balance")
    scl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="SCL Balance")
    el_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="EL Balance")
    col_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="COL Balance")
    vl_balance = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"), verbose_name="VL Balance (faculty only)")

    class Meta:
        verbose_name = "Leave Balance"
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["user_id", "effective_date"], name="idx_balance_user_date"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.effective_date}: CL={self.cl_balance}, EL={self.el_balance}, COL={self.col_balance}, VL={self.vl_balance}"


class LeaveTransaction(TimeStampedModel, UserScopedModel):
    """Leave account transaction record.

Records all balance changes: approvals, cancellations, year-end lapses/conversions,
extensions, and resumption adjustments.
"""
    TRANSACTION_TYPE_CHOICES = [
        ("APPROVAL", "Approval"),
        ("CANCELLATION", "Cancellation"),
        ("YEAR_END_LAPSE", "Year End Lapse"),
        ("YEAR_END_CONVERSION", "Year End Conversion"),
        ("EXTENSION_APPROVAL", "Extension Approval"),
        ("RESUMPTION_ADJUSTMENT", "Resumption Adjustment"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Related Application",
        null=True,
        blank=True,
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Transaction Type")
    category = models.CharField(max_length=2, verbose_name="Leave Category")
    quantity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Quantity")
    balance_before = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance Before")
    balance_after = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Balance After")

    reference_application_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Application ID")
    reference_transaction_id = models.IntegerField(null=True, blank=True, verbose_name="Reference Transaction ID")

    processed_by_user_id = models.IntegerField(db_index=True, verbose_name="Processed by user ID")
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name="Processed At")

    class Meta:
        verbose_name = "Leave Transaction"
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["user_id", "transaction_type"], name="idx_txn_user_type"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.transaction_type} {self.category}: {self.quantity}"


class WorkflowTask(TimeStampedModel, UserScopedModel):
    """Actionable workflow task with SLA tracking.

Used for Unit Head review, Establishment routing, Final Sanction, and SLA reminders/escalations.
"""
    TASK_TYPE_CHOICES = [
        ("UNIT_HEAD_REVIEW", "Unit Head Review"),
        ("ESTABLISHMENT_ROUTING", "Establishment Routing"),
        ("FINAL_SANCTION", "Final Sanction"),
        ("RESUMPTION_REVIEW", "Resumption Review"),
    ]

    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Related Application",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="Task Type")

    assigned_to_user_id = models.IntegerField(db_index=True, verbose_name="Assigned to user ID")
    role_code = models.CharField(max_length=50, verbose_name="Role Code")

    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("COMPLETED", "Completed")], default="PENDING", verbose_name="Status")

    reminder_threshold_seconds = models.IntegerField(default=3600, verbose_name="Reminder Threshold (seconds)")
    escalation_threshold_seconds = models.IntegerField(default=7200, verbose_name="Escalation Threshold (seconds)")

    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Reminder Sent")
    last_escalation_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Escalation Sent")

    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    completed_by_user_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name="Completed by user ID")

    class Meta:
        verbose_name = "Workflow Task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to_user_id", "status"], name="idx_task_assigned_status"),
            models.Index(fields=["application", "status"], name="idx_task_app_status"),
        ]

    def __str__(self):
        return f"{self.application} {self.task_type} for {self.assigned_to_user_id}"


class SLAEventLog(TimeStampedModel, UserScopedModel):
    """SLA reminder and escalation event log."""
    EVENT_TYPE_CHOICES = [
        ("REMINDER", "Reminder"),
        ("ESCALATION", "Escalation"),
    ]

    task = models.ForeignKey(
        "WorkflowTask",
        on_delete=models.CASCADE,
        related_name="sla_events",
        verbose_name="Related Task",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name="Event Type")

    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Triggered At")
    threshold_seconds = models.IntegerField(verbose_name="Threshold (seconds)")
    message = models.TextField(verbose_name="Message")

    class Meta:
        verbose_name = "SLA Event Log"
        ordering = ["-triggered_at"]


class ResumptionRecord(TimeStampedModel, UserScopedModel):
    """Resumption record for EL/COL/VL.

Captures actual return date and details reviewed by Sanctioning Authority.
"""
    application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="resumptions",
        verbose_name="Related Application",
    )
    user_id = models.IntegerField(db_index=True, verbose_name="User ID")

    actual_resumption_date = models.DateField(verbose_name="Actual Resumption Date")
    resumption_type = models.CharField(max_length=10, choices=[
        ("NORMAL", "Normal"),
        ("EARLY", "Early"),
        ("LATE", "Late"),
    ], verbose_name="Resumption Type")

    reviewed_by_user_id = models.IntegerField(db_index=True, verbose_name="Reviewed by user ID")
    reviewed_at = models.DateTimeField(auto_now_add=True, verbose_name="Reviewed At")

    balance_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), verbose_name="Balance Adjustment")

    class Meta:
        verbose_name = "Resumption Record"
        ordering = ["-reviewed_at"]
