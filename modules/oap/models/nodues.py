"""Domain model and clearance checks for institutional no-dues procedures."""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class NoDuesReason(models.TextChoices):
    GRADUATION = "GRADUATION", "Graduation / Convocation"
    WITHDRAWAL = "WITHDRAWAL", "Program Withdrawal"
    MIGRATION = "MIGRATION", "Institute Migration / Transfer"


class NoDuesOverallStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Departmental Sign-offs"
    CLEARED = "CLEARED", "Fully Cleared"
    REJECTED = "REJECTED", "Rejected / Outstanding Dues"


class DepartmentType(models.TextChoices):
    LIBRARY = "LIBRARY", "Central Library"
    HOSTEL = "HOSTEL", "Hall of Residence"
    ACCOUNTS = "ACCOUNTS", "Accounts & Finance Section"
    SPORTS = "SPORTS", "Sports Officer / Gymkhana"
    LABORATORY = "LABORATORY", "Departmental Laboratories"
    DISCIPLINE = "DISCIPLINE", "Proctorial / Disciplinary Committee"


class DepartmentSignoffStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Clearance"
    CLEARED = "CLEARED", "No Dues Outstanding"
    DUES_PENDING = "DUES_PENDING", "Dues / Fine Owed"


class NoDuesRequest(models.Model):
    student_id = models.CharField(max_length=32, unique=True, db_index=True)
    reason = models.CharField(
        max_length=32, choices=NoDuesReason.choices, default=NoDuesReason.GRADUATION
    )
    overall_status = models.CharField(
        max_length=32,
        choices=NoDuesOverallStatus.choices,
        default=NoDuesOverallStatus.PENDING,
    )
    clearance_certificate_number = models.CharField(
        max_length=64, unique=True, null=True, blank=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.CharField(max_length=32, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oap_no_dues_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"NoDues {self.student_id} ({self.overall_status})"

    def check_and_finalize(self, admin_id: str) -> bool:
        """If all departmental sign-offs are CLEARED, transition to CLEARED."""
        total_depts = self.signoffs.count()
        cleared_depts = self.signoffs.filter(
            status=DepartmentSignoffStatus.CLEARED
        ).count()
        if total_depts > 0 and total_depts == cleared_depts:
            self.overall_status = NoDuesOverallStatus.CLEARED
            self.completed_at = timezone.now()
            self.finalized_by = admin_id
            self.clearance_certificate_number = (
                f"IIITDMJ/NODUES/{timezone.now().year}/{uuid.uuid4().hex[:8].upper()}"
            )
            self.save(
                update_fields=[
                    "overall_status",
                    "completed_at",
                    "finalized_by",
                    "clearance_certificate_number",
                ]
            )
            return True
        return False


class NoDuesDepartmentalSignoff(models.Model):
    no_dues_request = models.ForeignKey(
        NoDuesRequest, on_delete=models.CASCADE, related_name="signoffs"
    )
    department = models.CharField(max_length=32, choices=DepartmentType.choices)
    status = models.CharField(
        max_length=32,
        choices=DepartmentSignoffStatus.choices,
        default=DepartmentSignoffStatus.PENDING,
    )
    dues_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    remarks = models.TextField(default="", blank=True)
    signoff_by = models.CharField(max_length=32, default="", blank=True)
    signoff_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_no_dues_signoff"
        unique_together = ("no_dues_request", "department")

    def __str__(self):
        return f"{self.no_dues_request.student_id} - {self.department} ({self.status})"

    def record_signoff(
        self,
        status: str,
        signoff_by: str,
        dues_amount: Decimal = Decimal("0.00"),
        remarks: str = "",
    ):
        self.status = status
        self.signoff_by = signoff_by
        self.dues_amount = dues_amount
        self.remarks = remarks
        self.signoff_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "signoff_by",
                "dues_amount",
                "remarks",
                "signoff_at",
            ]
        )
