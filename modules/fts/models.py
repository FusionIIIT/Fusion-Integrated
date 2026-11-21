"""Fusion Clean Architecture - File Tracking System domain models."""

from django.db import models


class FTSFile(models.Model):
    """A file item for tracking documents or materials through business workflow stages."""

    uin = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    subject = models.CharField(max_length=255)

    description = models.TextField(blank=True, default="")

    priority = models.CharField(
        max_length=16,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        default="medium",
    )

    category = models.CharField(max_length=64, default="general")

    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("in_transit", "In Transit"),
            ("received", "Received"),
            ("returned", "Returned"),
            ("archived", "Archived"),
        ],
        default="draft",
    )

    creator_id = models.CharField(max_length=64, db_index=True)

    creator_role = models.CharField(max_length=64, blank=True, default="")

    current_holder_id = models.CharField(max_length=64, db_index=True)

    current_holder_role = models.CharField(max_length=64, blank=True, default="")

    is_draft = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "uin"]
        verbose_name = "File"
        verbose_name_plural = "Files"

    def __str__(self) -> str:
        return f"{self.uin} - {self.subject}"


class FTSMovement(models.Model):
    """Records a movement event when a file changes hands or status in the system."""

    FILE_CHOICES = [
        ("created", "Created"),
        ("forwarded", "Forwarded"),
        ("returned", "Returned"),
        ("archived", "Archived"),
    ]

    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name="movements")
    from_user_id = models.CharField(max_length=64)
    from_role = models.CharField(max_length=64, blank=True, default="")
    to_user_id = models.CharField(max_length=64)
    to_role = models.CharField(max_length=64, blank=True, default="")
    action = models.CharField(
        max_length=20,
        choices=FILE_CHOICES,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "file"]
        verbose_name = "Movement"
        verbose_name_plural = "Movements"

    def __str__(self) -> str:
        return f"{self.action} by {self.from_user_id} to {self.to_user_id}"


class FTSComment(models.Model):
    """Comments or remarks on a file's movement."""

    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name="comments")
    movement = models.ForeignKey(
        FTSMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    author_id = models.CharField(max_length=64)
    author_role = models.CharField(max_length=64, blank=True, default="")
    remarks = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self) -> str:
        return f"{self.author_id}: {self.remarks[:50]}..."


class FTSAttachment(models.Model):
    """Attachments related to a file movement."""

    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name="attachments")
    movement = models.ForeignKey(
        FTSMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
    uploaded_by_id = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self) -> str:
        return self.file_name
