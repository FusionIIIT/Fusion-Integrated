from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("vms", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="VisitorDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(max_length=32)),
                ("storage_key", models.CharField(max_length=80, unique=True)),
                ("filename", models.CharField(max_length=160)),
                ("content_type", models.CharField(max_length=80)),
                ("size_bytes", models.PositiveIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("scan_status", models.CharField(choices=[("pending", "Pending"),
                    ("clean", "Clean"), ("infected", "Infected"), ("failed", "Failed")],
                    db_index=True, default="pending", max_length=12)),
                ("scan_detail", models.CharField(blank=True, max_length=160)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("scanned_at", models.DateTimeField(blank=True, null=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="identity_documents", to="vms.visitrequest")),
                ("visitor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="identity_documents", to="vms.visitorprofile")),
            ],
            options={"db_table": "vms_visitor_document", "indexes": [
                models.Index(fields=["request", "scan_status"], name="vms_doc_request_idx")]},
        ),
    ]
