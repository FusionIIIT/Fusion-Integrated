from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("vms", "0002_visitor_document")]
    operations = [
        migrations.CreateModel(
            name="EventGuestBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("idempotency_key", models.CharField(max_length=100, unique=True)),
                ("created_by_user_id", models.IntegerField()),
                ("row_count", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="guest_batches", to="vms.eventrecord")),
            ],
            options={"db_table": "vms_event_guest_batch", "indexes": [
                models.Index(fields=["event", "-created_at"], name="vms_event_batch_idx")]},
        ),
        migrations.CreateModel(
            name="EventGuestBatchRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("submitted_visit_id", models.PositiveBigIntegerField()),
                ("status", models.CharField(choices=[("accepted", "Accepted"),
                    ("rejected", "Rejected")], max_length=12)),
                ("reason", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="rows", to="vms.eventguestbatch")),
                ("request", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="event_batch_rows", to="vms.visitrequest")),
            ],
            options={"db_table": "vms_event_guest_batch_row", "constraints": [
                models.UniqueConstraint(fields=("batch", "submitted_visit_id"),
                                        name="vms_event_batch_visit_uq")]},
        ),
    ]
