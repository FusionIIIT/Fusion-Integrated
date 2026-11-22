from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.patents.domain import state_machine as sm


class PatentApplication(TimeStampedModel, UserScopedModel):
    application_number = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    description = models.TextField()
    claims = models.TextField()
    status = models.CharField(max_length=32, db_index=True, default=sm.DRAFT)
    domain_category = models.CharField(max_length=100, blank=True, default="")
    assigned_director_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_attorney_id = models.IntegerField(null=True, blank=True, db_index=True)
    external_filing_id = models.CharField(max_length=100, blank=True, default="")
    filing_date = models.DateField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    renewal_due_date = models.DateField(null=True, blank=True)
    renewal_decided_at = models.DateTimeField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=50, default="IN")
    decision_date = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "patents_application"
        constraints = [
            models.CheckConstraint(
                name="patents_app_version_positive",
                condition=models.Q(version__gte=1),
            ),
        ]

    @property
    def applicant_user_id(self) -> int:
        return self.user_id


class CoInventor(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="co_inventors",
    )
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    consent_granted = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "patents_coinventor"
        constraints = [
            models.CheckConstraint(
                name="patents_coinventor_share_bounds",
                condition=models.Q(share_percentage__gt=0) & models.Q(share_percentage__lte=100),
            ),
        ]


class ApplicationDocument(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10, default="pdf")
    file_size_bytes = models.BigIntegerField()
    storage_path = models.CharField(max_length=500)
    sensitivity_level = models.CharField(max_length=30, default="confidential")
    version = models.PositiveIntegerField(default=1)
    uploaded_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "patents_document"
        constraints = [
            models.CheckConstraint(
                name="patents_doc_size_bounds",
                condition=models.Q(file_size_bytes__gt=0) & models.Q(file_size_bytes__lte=52428800),
            ),
        ]


class ReviewDecision(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    director_user_id = models.IntegerField(db_index=True)
    decision = models.CharField(max_length=20)
    justification = models.TextField()
    assigned_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patents_review_decision"


class AppealRecord(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="appeals",
    )
    applicant_user_id = models.IntegerField(db_index=True)
    grounds = models.TextField()
    status = models.CharField(max_length=30, default="SUBMITTED")
    director_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    decision_notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "patents_appeal_record"
