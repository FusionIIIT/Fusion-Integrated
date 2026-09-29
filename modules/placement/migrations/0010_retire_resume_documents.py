"""Resumes are maintained on the ERP portal, so the copies here are retired."""
from django.db import migrations


def retire(apps, schema_editor):
    Document = apps.get_model("placement", "ProfileDocument")
    Offer = apps.get_model("placement", "Offer")
    Record = apps.get_model("placement", "PlacementRecord")

    # A referenced row is left alone: it is evidence of what was sent.
    referenced = set(Offer.objects.exclude(letter__isnull=True)
                     .values_list("letter_id", flat=True))
    referenced |= set(Record.objects.exclude(offer_letter__isnull=True)
                      .values_list("offer_letter_id", flat=True))

    Document.objects.filter(kind="resume").exclude(pk__in=referenced).delete()


class Migration(migrations.Migration):

    dependencies = [("placement", "0009_remove_profiledocument_profile_and_more")]

    operations = [migrations.RunPython(retire, migrations.RunPython.noop)]
