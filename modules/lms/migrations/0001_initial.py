# Generated for the LMS Course Workspace foundation.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(db_index=True, max_length=32, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("syllabus", models.TextField(blank=True)),
                ("schedule", models.CharField(blank=True, max_length=200)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="published", max_length=16)),
            ],
            options={
                "db_table": "lms_course",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="CourseMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("role", models.CharField(choices=[("faculty", "Faculty"), ("student", "Student"), ("ta", "Teaching Assistant"), ("observer", "Observer")], max_length=16)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="lms.course")),
            ],
            options={
                "db_table": "lms_course_membership",
                "ordering": ["course", "role", "user_id"],
            },
        ),
        migrations.AddIndex(
            model_name="coursemembership",
            index=models.Index(fields=["user_id", "role"], name="lms_mem_user_role_idx"),
        ),
        migrations.AddIndex(
            model_name="coursemembership",
            index=models.Index(fields=["course", "role"], name="lms_mem_course_role_idx"),
        ),
        migrations.AddConstraint(
            model_name="coursemembership",
            constraint=models.UniqueConstraint(fields=("course", "user_id"), name="lms_membership_unique"),
        ),
    ]
