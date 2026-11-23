"""Keep pre-filing substates in their workflow records, not application status."""

from django.db import migrations, models

LEGACY_PREFILING_STATUSES = (
    "assignment_offered",
    "attorney_assigned",
    "pending_review",
    "budget_approved",
    "budget_rejected",
    "escalated",
    "escalation_tracked",
    "pre_filing_satisfied",
)


def normalize_application_statuses(apps, schema_editor):
    application = apps.get_model("pms", "PatentApplication")
    application.objects.filter(status__in=LEGACY_PREFILING_STATUSES).update(status="approved")


class Migration(migrations.Migration):
    dependencies = [("pms", "0002_seed_pms_configuration")]

    operations = [
        migrations.RunPython(normalize_application_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="patentapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "DRAFT"),
                    ("submitted", "SUBMITTED"),
                    ("under_review", "UNDER_REVIEW"),
                    ("approved", "APPROVED"),
                    ("needs_revision", "NEEDS_REVISION"),
                    ("resubmitted", "RESUBMITTED"),
                    ("rejected", "REJECTED"),
                    ("expired", "EXPIRED"),
                    ("appeal_submitted", "APPEAL_SUBMITTED"),
                    ("rejection_upheld", "REJECTION_UPHELD"),
                    ("remanded_for_amendment", "REMANDED_FOR_AMENDMENT"),
                    ("decision_modified", "DECISION_MODIFIED"),
                    ("filed", "FILED"),
                    ("office_action_recorded", "OFFICE_ACTION_RECORDED"),
                    ("awaiting_applicant_approval", "AWAITING_APPLICANT_APPROVAL"),
                    ("applicant_approved", "APPLICANT_APPROVED"),
                    ("response_ready", "RESPONSE_READY"),
                    ("response_submitted", "RESPONSE_SUBMITTED"),
                    ("granted", "GRANTED"),
                    ("renewal_decision_requested", "RENEWAL_DECISION_REQUESTED"),
                    ("renewal_approved", "RENEWAL_APPROVED"),
                    ("do_not_renew", "DO_NOT_RENEW"),
                    ("renewed", "RENEWED"),
                    ("withdrawn", "WITHDRAWN"),
                ],
                db_index=True,
                default="submitted",
                max_length=32,
            ),
        ),
    ]
