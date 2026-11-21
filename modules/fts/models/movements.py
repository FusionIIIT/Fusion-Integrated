from django.db import models

from core.db.mixins import TimeStampedModel


class FileMovement(TimeStampedModel):
    MOVEMENT_TYPES = [
        ("CREATION", "Creation"),
        ("FORWARD", "Forward"),
        ("RETURN", "Return"),
        ("ARCHIVE", "Archive"),
    ]

    file = models.ForeignKey("fts.File", on_delete=models.PROTECT, related_name="movements")
    sequence = models.PositiveIntegerField()
    movement_type = models.CharField(max_length=32, choices=MOVEMENT_TYPES)

    from_user_id = models.IntegerField(db_index=True)
    from_username = models.CharField(max_length=150)
    from_role = models.CharField(max_length=100)

    to_user_id = models.IntegerField(db_index=True)
    to_username = models.CharField(max_length=150)
    to_role = models.CharField(max_length=100)

    class Meta:
        db_table = "fts_movement"
        constraints = [
            models.UniqueConstraint(fields=["file", "sequence"], name="fts_mov_file_seq_uniq"),
        ]
        indexes = [
            models.Index(fields=["file", "sequence"], name="fts_mov_file_seq_idx"),
            models.Index(fields=["from_user_id", "created_at"], name="fts_mov_from_idx"),
            models.Index(fields=["to_user_id", "created_at"], name="fts_mov_to_idx"),
        ]

    def __str__(self) -> str:
        return f"Movement #{self.sequence} on {self.file_id}: {self.from_username}"
