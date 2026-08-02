from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    """A row belonging to a person.

    `user_id` is the IAM user id. It is a plain integer and NOT a ForeignKey —
    there is no user table in this database, and cross-boundary references must
    stay unconstrained so a module can be extracted later without schema
    surgery.
    """

    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True
