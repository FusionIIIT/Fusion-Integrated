"""Record of leave already sanctioned offline (blueprint Step 3.2).

BR-EL-029: only leave already sanctioned through an authorized offline/paper
process is recorded retrospectively, with the sanction reference captured. Such
a record creates ledger entries but starts **no** approval task — that is a
service-layer obligation (Step 4) and is not enforced here.

Shape is PROVISIONAL.
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.models.policy import LEAVE_TYPE_CHOICES


class OfflineLeaveRecord(TimeStampedModel):
    """A retrospectively recorded sanctioned leave — PROVISIONAL shape."""

    subject_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    #: The paper/offline sanction the record is reconciled against (BR-EL-029).
    sanction_reference = models.CharField(max_length=160)
    evidence = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_offline_record"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_offline_window_valid",
            ),
        ]
        indexes = [models.Index(fields=["subject_user_id", "leave_type"],
                                name="leave_offline_subject_idx")]

    def __str__(self) -> str:
        return f"offline u{self.subject_user_id} {self.leave_type}"
