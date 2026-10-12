"""Publish the canonical ELM policy and hierarchy if none is published. Idempotent."""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.elm.domain.policy import DEFAULT_PARAMS
from modules.elm.models import PolicyVersion
from modules.elm.models.config import PUBLISHED
from modules.elm.registry import DEFAULT_HIERARCHY
from modules.elm.services.config import validate_policy


class Command(BaseCommand):
    help = "Seed and publish the default ELM leave policy and hierarchy"

    def add_arguments(self, parser):
        parser.add_argument("--effective-from", default=None,
                            help="ISO date; defaults to 1 January of this year")

    @transaction.atomic
    def handle(self, *args, **opts):
        if PolicyVersion.objects.filter(status=PUBLISHED).exists():
            self.stdout.write("a published ELM policy already exists; nothing to do")
            return
        eff = (date.fromisoformat(opts["effective_from"]) if opts["effective_from"]
               else date(timezone.localdate().year, 1, 1))
        validate_policy(DEFAULT_PARAMS, DEFAULT_HIERARCHY)
        pv = PolicyVersion.objects.create(
            name="Canonical ELM policy", params=DEFAULT_PARAMS,
            hierarchy=DEFAULT_HIERARCHY, effective_from=eff, status=PUBLISHED,
            published_at=timezone.now())
        self.stdout.write(self.style.SUCCESS(f"published policy #{pv.pk} from {eff}"))
