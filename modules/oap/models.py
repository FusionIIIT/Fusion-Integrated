"""Persistence models for Other Academic Procedures."""
from django.db import models


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True


class LeaveApplication(Timestamped):
    student_user_id = models.IntegerField(db_index=True)
    details = models.TextField()
    supporting_document_url = models.URLField(blank=True)
    status = models.CharField(max_length=12, default="submitted", choices=[(x, x) for x in ("submitted", "approved", "rejected")])
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class BonafideRequest(Timestamped):
    student_user_id = models.IntegerField(db_index=True)
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=12, default="submitted", choices=[(x, x) for x in ("submitted", "approved", "rejected")])
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)


class NoDuesRequest(Timestamped):
    student_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, default="in_progress", choices=[(x, x) for x in ("in_progress", "finalized")])
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)


class NoDuesClearance(Timestamped):
    DOMAINS = ("library", "hostel", "mess", "department", "lab", "academic_section", "student_section")
    request = models.ForeignKey(NoDuesRequest, on_delete=models.CASCADE, related_name="clearances")
    domain = models.CharField(max_length=20, choices=[(x, x) for x in DOMAINS])
    status = models.CharField(max_length=16, default="pending", choices=[(x, x) for x in ("pending", "cleared", "dues_outstanding")])
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    class Meta: constraints = [models.UniqueConstraint(fields=("request", "domain"), name="oap_one_clearance_per_domain")]


class ThesisSupervisorAssignment(Timestamped):
    student_user_id = models.IntegerField(unique=True)
    supervisor_user_id = models.IntegerField()


class TaSupervisorAssignment(Timestamped):
    student_user_id = models.IntegerField(unique=True)
    supervisor_user_id = models.IntegerField()
    subject = models.CharField(max_length=160, blank=True)


class AssistantshipClaim(Timestamped):
    student_user_id = models.IntegerField(db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=24, default="submitted", choices=[(x, x) for x in ("submitted", "awaiting_department", "forwarded_to_hod", "approved", "rejected", "disbursed")])
    thesis_supervisor_user_id = models.IntegerField()
    ta_supervisor_user_id = models.IntegerField()
    thesis_decision = models.CharField(max_length=10, blank=True)
    ta_decision = models.CharField(max_length=10, blank=True)
    thesis_decided_at = models.DateTimeField(null=True, blank=True)
    ta_decided_at = models.DateTimeField(null=True, blank=True)
    department_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    hod_decided_by_user_id = models.IntegerField(null=True, blank=True)
    disbursed_by_user_id = models.IntegerField(null=True, blank=True)


class GraduateSeminar(Timestamped):
    student_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=12, default="requested", choices=[("requested", "requested"), ("scheduled", "scheduled")])
    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    venue = models.CharField(max_length=255, blank=True)
