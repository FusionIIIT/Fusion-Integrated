import django.core.files.storage
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GymkhanaNotificationOutbox",
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
                ("recipient_user_id", models.IntegerField(db_index=True)),
                ("topic", models.CharField(max_length=100)),
                ("subject", models.CharField(max_length=250)),
                ("body", models.TextField()),
                ("status", models.CharField(default="pending", max_length=20)),
            ],
            options={
                "db_table": "gymkhana_notification_outbox",
            },
        ),
        migrations.CreateModel(
            name="PollChoice",
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
                ("text", models.CharField(max_length=200)),
                ("votes_count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "db_table": "gymkhana_poll_choice",
            },
        ),
        migrations.CreateModel(
            name="Club",
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
                ("name", models.CharField(max_length=150, unique=True)),
                ("category", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True)),
                ("faculty_councillor_id", models.IntegerField(db_index=True)),
                ("status", models.CharField(default="open", max_length=20)),
            ],
            options={
                "db_table": "gymkhana_club",
                "indexes": [
                    models.Index(
                        fields=["status", "category"], name="gym_club_status_cat_idx"
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("category__in", ["Technical", "Sports", "Cultural"])
                        ),
                        name="gymkhana_club_valid_category",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("status__in", ["open", "confirmed"])),
                        name="gymkhana_club_valid_status",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="VotingPoll",
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
                ("title", models.CharField(max_length=250)),
                ("description", models.TextField(blank=True)),
                ("target_batches", models.JSONField(default=list)),
                ("target_branches", models.JSONField(default=list)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("created_by_id", models.IntegerField(db_index=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polls",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_poll",
            },
        ),
        migrations.CreateModel(
            name="PollVote",
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
                ("student_id", models.IntegerField(db_index=True)),
                (
                    "choice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="votes",
                        to="gymkhana.pollchoice",
                    ),
                ),
                (
                    "poll",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="votes",
                        to="gymkhana.votingpoll",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_poll_vote",
            },
        ),
        migrations.AddField(
            model_name="pollchoice",
            name="poll",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="choices",
                to="gymkhana.votingpoll",
            ),
        ),
        migrations.CreateModel(
            name="ClubBooking",
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
                ("booking_type", models.CharField(max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("venue", models.CharField(max_length=100)),
                ("date", models.DateField()),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("description", models.TextField(blank=True)),
                (
                    "poster",
                    models.FileField(
                        blank=True,
                        storage=django.core.files.storage.FileSystemStorage(
                            base_url=None,
                            location="/Users/amanraj4115/.local/share/fusion-integrated/uploads",
                        ),
                        upload_to="posters/",
                    ),
                ),
                ("created_by_id", models.IntegerField(db_index=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_booking",
                "indexes": [
                    models.Index(
                        fields=["venue", "date"], name="gym_book_venue_date_idx"
                    ),
                    models.Index(
                        fields=["club", "date"], name="gym_book_club_date_idx"
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("start_time__lt", models.F("end_time"))),
                        name="gymkhana_booking_valid_time_range",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("booking_type__in", ["session", "event"])),
                        name="gymkhana_booking_valid_type",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "venue__in",
                                [
                                    "L-101",
                                    "L-102",
                                    "CC1",
                                    "CC2",
                                    "Hall-1",
                                    "Sports Ground",
                                    "Auditorium",
                                ],
                            )
                        ),
                        name="gymkhana_booking_valid_venue",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ClubBudgetRequest",
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
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("purpose", models.CharField(max_length=250)),
                ("description", models.TextField()),
                (
                    "supporting_file",
                    models.FileField(
                        storage=django.core.files.storage.FileSystemStorage(
                            base_url=None,
                            location="/Users/amanraj4115/.local/share/fusion-integrated/uploads",
                        ),
                        upload_to="budgets/",
                    ),
                ),
                ("status", models.CharField(default="open", max_length=20)),
                ("submitted_by_id", models.IntegerField(db_index=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="budget_requests",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_budget_request",
                "indexes": [
                    models.Index(
                        fields=["club", "status"], name="gym_budget_club_status_idx"
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("amount__gte", 0)),
                        name="gymkhana_budget_non_negative",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ClubEventReport",
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
                ("description", models.TextField()),
                ("student_incharge_id", models.IntegerField(db_index=True)),
                ("event_name", models.CharField(max_length=200)),
                ("event_datetime", models.DateTimeField()),
                (
                    "report_file",
                    models.FileField(
                        storage=django.core.files.storage.FileSystemStorage(
                            base_url=None,
                            location="/Users/amanraj4115/.local/share/fusion-integrated/uploads",
                        ),
                        upload_to="reports/",
                    ),
                ),
                ("submitted_by_id", models.IntegerField(db_index=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_reports",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_event_report",
                "indexes": [
                    models.Index(
                        fields=["club", "created_at"],
                        name="gym_report_club_created_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ClubLeadership",
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
                ("student_id", models.IntegerField(db_index=True)),
                ("role", models.CharField(max_length=30)),
                ("is_current", models.BooleanField(db_index=True, default=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leaderships",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_leadership",
                "indexes": [
                    models.Index(
                        fields=["club", "is_current"], name="gym_lead_club_curr_idx"
                    ),
                    models.Index(
                        fields=["student_id", "is_current"],
                        name="gym_lead_stud_curr_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("role__in", ["coordinator", "co_coordinator"])
                        ),
                        name="gymkhana_lead_valid_role",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("is_current", True)),
                        fields=("club", "role"),
                        name="gymkhana_unique_current_club_role",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ClubMembership",
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
                ("student_id", models.IntegerField(db_index=True)),
                ("status", models.CharField(default="open", max_length=20)),
                ("remarks", models.TextField(blank=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="gymkhana.club",
                    ),
                ),
            ],
            options={
                "db_table": "gymkhana_membership",
                "indexes": [
                    models.Index(
                        fields=["club", "status"], name="gym_mem_club_status_idx"
                    ),
                    models.Index(
                        fields=["student_id", "status"], name="gym_mem_stud_status_idx"
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("club", "student_id"),
                        name="gymkhana_unique_student_club_membership",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("status__in", ["open", "confirmed"])),
                        name="gymkhana_membership_valid_status",
                    ),
                ],
            },
        ),
        migrations.AddIndex(
            model_name="votingpoll",
            index=models.Index(
                fields=["club", "expires_at"], name="gym_poll_club_exp_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="pollvote",
            constraint=models.UniqueConstraint(
                fields=("poll", "student_id"), name="gymkhana_unique_student_poll_vote"
            ),
        ),
        migrations.AddIndex(
            model_name="pollchoice",
            index=models.Index(fields=["poll"], name="gym_choice_poll_idx"),
        ),
    ]
