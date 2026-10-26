"""Import published external academic vacation data; ELM does not author it."""

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.elm.models import VacationPeriod


def validate_periods(data):
    if not isinstance(data, list) or not data:
        raise ValueError("Expected a nonempty list.")
    result = []
    for row in data:
        start = date.fromisoformat(row["start_date"])
        end = date.fromisoformat(row["end_date"])
        reference = row["source_reference"].strip()
        if end < start or not reference:
            raise ValueError("Invalid dates or missing publication reference.")
        result.append((reference, start, end))
    return result


class Command(BaseCommand):
    help = "Import published vacation JSON with source_reference, start_date and end_date."

    def add_arguments(self, parser):
        parser.add_argument("path")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options["path"]).read_text(encoding="utf-8-sig"))
            rows = validate_periods(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
        for reference, start, end in rows:
            VacationPeriod.objects.update_or_create(
                source_reference=reference, start_date=start, defaults={"end_date": end}
            )
        self.stdout.write(f"Imported {len(rows)} published vacation periods.")
