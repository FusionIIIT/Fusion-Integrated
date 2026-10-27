"""Replace generic leave closure with explicit resumption-review outcomes."""
from django.db import migrations, models


def migrate_legacy_closed(apps, schema_editor):
    LeaveApplication = apps.get_model("leave", "LeaveApplication")
    db_alias = schema_editor.connection.alias
    # The prior service stamped resumption_reviewed_at but forgot to leave the
    # resumption_submitted state. Treat those rows as already reviewed too, or the
    # next review would apply the same balance adjustment again.
    from django.db.models import Q

    rows = LeaveApplication.objects.using(db_alias).filter(
        Q(status="closed")
        | Q(status="resumption_submitted", resumption_reviewed_at__isnull=False)
    ).only("id", "end_date", "resumption_date", "resumption_reviewed_at")
    for row in rows.iterator():
        if row.resumption_date is None or row.end_date is None or row.resumption_date == row.end_date:
            outcome = "no_adjustment"
        elif row.resumption_date < row.end_date:
            outcome = "early_return_synchronized"
        else:
            outcome = "late_return_synchronized"
        LeaveApplication.objects.using(db_alias).filter(pk=row.pk).update(
            status="resumption_reviewed", resumption_outcome=outcome
        )


def restore_legacy_closed(apps, schema_editor):
    LeaveApplication = apps.get_model("leave", "LeaveApplication")
    db_alias = schema_editor.connection.alias
    rows = LeaveApplication.objects.using(db_alias).filter(status="resumption_reviewed").only(
        "id", "resumption_reviewed_at"
    )
    for row in rows.iterator():
        # Before this migration, the implemented review service left completed rows
        # in resumption_submitted with a timestamp. Preserve that legacy shape on rollback.
        restored_status = "resumption_submitted" if row.resumption_reviewed_at else "closed"
        LeaveApplication.objects.using(db_alias).filter(pk=row.pk).update(
            status=restored_status, resumption_outcome=""
        )


class Migration(migrations.Migration):
    dependencies = [("leave", "0003_fractional_el_balances")]

    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="resumption_outcome",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not reviewed"),
                    ("no_adjustment", "No adjustment"),
                    ("early_return_synchronized", "Early return synchronized"),
                    ("late_return_synchronized", "Late return synchronized"),
                ],
                default="",
                max_length=32,
            ),
        ),
        migrations.RunPython(migrate_legacy_closed, restore_legacy_closed),
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("substitute_pending", "Pending Substitute Consent"),
                    ("under_review", "Under Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    ("cancel_requested", "Cancellation Requested"),
                    ("cancelled", "Cancelled"),
                    ("extension_requested", "Extension Requested"),
                    ("resumption_submitted", "Resumption Submitted"),
                    ("resumption_reviewed", "Resumption Reviewed"),
                ],
                default="substitute_pending",
                max_length=30,
            ),
        ),
    ]
