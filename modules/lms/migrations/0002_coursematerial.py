# Generated for LMS Course Materials implementation.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseMaterial",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "material_type",
                    models.CharField(
                        choices=[("file", "File"), ("link", "Link"), ("note", "Note")],
                        default="file",
                        max_length=16,
                    ),
                ),
                (
                    "section_type",
                    models.CharField(
                        choices=[("module", "Module"), ("week", "Weekly Section")],
                        default="module",
                        max_length=16,
                    ),
                ),
                ("section_title", models.CharField(db_index=True, max_length=100)),
                (
                    "file",
                    models.FileField(
                        blank=True, null=True, upload_to="lms/materials/%Y/%m/"
                    ),
                ),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("file_size", models.BigIntegerField(blank=True, null=True)),
                ("link_url", models.CharField(blank=True, max_length=500)),
                ("content", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("scheduled", "Scheduled"),
                        ],
                        default="published",
                        max_length=16,
                    ),
                ),
                (
                    "release_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("order", models.IntegerField(default=0)),
                ("created_by_user_id", models.IntegerField(db_index=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materials",
                        to="lms.course",
                    ),
                ),
            ],
            options={
                "db_table": "lms_course_material",
                "ordering": ["section_title", "order", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="coursematerial",
            index=models.Index(
                fields=["course", "status"], name="lms_mat_course_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="coursematerial",
            index=models.Index(
                fields=["course", "section_title"], name="lms_mat_course_sec_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="coursematerial",
            index=models.Index(
                fields=["status", "release_at"], name="lms_mat_status_rel_idx"
            ),
        ),
    ]
