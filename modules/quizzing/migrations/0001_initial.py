import uuid
from decimal import Decimal
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="QuestionBank",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("course_code", models.CharField(db_index=True, max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("created_by", models.CharField(db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"db_table": "quizzing_question_bank"},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("question_text", models.TextField()),
                ("question_type", models.CharField(default="MCQ_SINGLE", max_length=32)),
                ("difficulty", models.CharField(default="MEDIUM", max_length=16)),
                ("options", models.JSONField(blank=True, default=list)),
                ("correct_answer", models.JSONField(blank=True, default=dict)),
                ("default_marks", models.DecimalField(decimal_places=2, default=Decimal("1.0"), max_digits=5)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("bank", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="questions", to="quizzing.questionbank")),
            ],
            options={"db_table": "quizzing_question"},
        ),
        migrations.CreateModel(
            name="Quiz",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("course_code", models.CharField(db_index=True, max_length=32)),
                ("created_by", models.CharField(db_index=True, max_length=64)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("duration_minutes", models.PositiveIntegerField(default=30)),
                ("status", models.CharField(db_index=True, default="DRAFT", max_length=16)),
                ("total_marks", models.DecimalField(decimal_places=2, default=Decimal("0.0"), max_digits=6)),
                ("answer_key_released", models.BooleanField(default=False)),
                ("grades_released", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"db_table": "quizzing_quiz"},
        ),
        migrations.CreateModel(
            name="QuizQuestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order", models.PositiveIntegerField(default=1)),
                ("marks", models.DecimalField(decimal_places=2, default=Decimal("1.0"), max_digits=5)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="quizzing.question")),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_questions", to="quizzing.quiz")),
            ],
            options={"db_table": "quizzing_quiz_question"},
        ),
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("student_user_id", models.CharField(db_index=True, max_length=64)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(db_index=True, default="IN_PROGRESS", max_length=16)),
                ("total_score", models.DecimalField(decimal_places=2, default=Decimal("0.0"), max_digits=6)),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="quizzing.quiz")),
            ],
            options={"db_table": "quizzing_attempt"},
        ),
        migrations.CreateModel(
            name="StudentAnswer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("submitted_answer", models.JSONField(blank=True, default=dict)),
                ("autograded_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("override_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("feedback", models.TextField(blank=True, default="")),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="quizzing.quizattempt")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="quizzing.question")),
            ],
            options={"db_table": "quizzing_student_answer"},
        ),
        migrations.CreateModel(
            name="AttemptIntegrityLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=64)),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("details", models.TextField(blank=True, default="")),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integrity_logs", to="quizzing.quizattempt")),
            ],
            options={"db_table": "quizzing_integrity_log"},
        ),
    ]
