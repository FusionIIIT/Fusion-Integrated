from django.db import models


class Application(models.Model):
    application_no = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=200)
    domain = models.CharField(max_length=80, blank=True)
    abstract = models.TextField(blank=True)
    description = models.TextField(blank=True)
    claims = models.TextField(blank=True)

    applicant_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=32, default="draft", db_index=True)

    director_user_id = models.IntegerField(null=True, blank=True)
    review_due_on = models.DateField(null=True, blank=True)
    decision_justification = models.TextField(blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    revision_count = models.PositiveIntegerField(default=0)

    attorney_user_id = models.IntegerField(null=True, blank=True)
    attorney_status = models.CharField(max_length=16, blank=True)  # offered | accepted
    opinion_recommendation = models.CharField(max_length=32, blank=True)
    opinion_text = models.TextField(blank=True)

    budget_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # pending | approved | rejected | escalated
    budget_status = models.CharField(max_length=16, blank=True)

    external_filing_id = models.CharField(max_length=64, blank=True)
    filing_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.application_no} {self.title}"


class ApplicationEvent(models.Model):
    """Append-only audit trail (PS 2.3.20)."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="events")
    action = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    from_state = models.CharField(max_length=32, blank=True)
    to_state = models.CharField(max_length=32, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.application_id}: {self.action}"


class Inventor(models.Model):
    """Co-inventor with an ownership share (PS 2.3.12)."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="inventors")
    user_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    ownership_pct = models.DecimalField(max_digits=5, decimal_places=2)
    consent_given = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.ownership_pct}%)"


class Document(models.Model):
    """A logical document; its contents live in DocumentVersion rows (PS 2.3.14)."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=40)
    sensitivity = models.CharField(max_length=16, default="internal")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.kind} for application {self.application_id}"


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField()
    file_name = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_by_user_id = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version_no"]
        unique_together = [("document", "version_no")]

    def __str__(self) -> str:
        return f"{self.file_name} v{self.version_no}"


class Notification(models.Model):
    """In-app notice; e-mail delivery is a separate integration (PS 2.3.19)."""

    recipient_user_id = models.IntegerField(db_index=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=40)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.kind} for {self.recipient_user_id}"
