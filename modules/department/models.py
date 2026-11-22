from django.contrib.postgres.fields import ArrayField
from django.db import models


class Announcement(models.Model):
    department = models.CharField(max_length=200)
    content = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    target_roles = ArrayField(models.CharField(max_length=80), default=list, blank=True)
    target_programmes = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    target_batch_years = ArrayField(models.PositiveSmallIntegerField(), default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(department=""), name="dept_announcement_has_scope",
            ),
            models.CheckConstraint(
                condition=~models.Q(content=""), name="dept_announcement_has_content",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "-id"], condition=models.Q(is_active=True),
                         name="dept_announcement_active_idx"),
        ]

    def __str__(self):
        return f"Announcement {self.pk} ({self.department})"


class StockItem(models.Model):
    department = models.CharField(max_length=200)
    name = models.CharField(max_length=160)
    quantity = models.PositiveBigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="dept_unique_stock_name"),
        ]

    def __str__(self):
        return self.name


class StockRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending HOD approval"
        APPROVED = "approved", "Approved for issuance"
        REJECTED = "rejected", "Rejected"
        ISSUED = "issued", "Issued"

    item = models.ForeignKey(StockItem, on_delete=models.PROTECT)
    user_id = models.PositiveIntegerField(db_index=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="dept_stock_request_positive",
            ),
        ]

    def __str__(self):
        return f"Stock request {self.pk}"


class StockMovement(models.Model):
    item = models.ForeignKey(StockItem, on_delete=models.PROTECT)
    request = models.OneToOneField(StockRequest, on_delete=models.PROTECT, null=True)
    actor_id = models.PositiveIntegerField()
    delta = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(request__isnull=True, delta__gt=0)
                | models.Q(request__isnull=False, delta__lt=0),
                name="dept_stock_movement_direction",
            ),
        ]

    def __str__(self):
        return f"Stock movement {self.pk}"


class Feedback(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Under review"
        CLOSED = "closed", "Closed"
        RESOLVED = "resolved", "Resolved"

    department = models.CharField(max_length=200, db_index=True)
    user_id = models.PositiveIntegerField()
    content = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True)
    reviewed_by_id = models.PositiveIntegerField(null=True)
    disposed_at = models.DateTimeField(null=True)
    disposed_by_id = models.PositiveIntegerField(null=True)

    def __str__(self):
        return f"Feedback {self.pk}"


class Notice(models.Model):
    department = models.CharField(max_length=200, db_index=True)
    message = models.CharField(max_length=200)
    announcement = models.OneToOneField(Announcement, on_delete=models.CASCADE, null=True)
    user_id = models.PositiveIntegerField(null=True)
    audience = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(announcement__isnull=False, user_id__isnull=True, audience="")
                           | models.Q(announcement__isnull=True, user_id__isnull=False, audience="")
                           | models.Q(announcement__isnull=True, user_id__isnull=True,
                                      audience__in=["hod", "admin"])),
                name="dept_notice_one_audience",
            ),
        ]

    def __str__(self):
        return f"Department notice {self.pk}"
