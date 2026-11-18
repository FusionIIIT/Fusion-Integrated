from django.core.management.base import BaseCommand
from modules.elm.domain.policy import DEFAULT_PARAMS
from modules.elm.models import LeavePolicy

class Command(BaseCommand):
    help = "Create the current ELM policy parameters if missing; no policy version lifecycle is used."
    def handle(self, *args, **options):
        policy, created = LeavePolicy.objects.get_or_create(key="current", defaults={
            "params": DEFAULT_PARAMS,
            "hierarchy": {"unit_heads": {}, "sanctioning": {}, "default_sanctioning": []},
        })
        if not policy.params:
            policy.params = DEFAULT_PARAMS
        if not policy.hierarchy:
            policy.hierarchy = {"unit_heads": {}, "sanctioning": {}, "default_sanctioning": []}
        if not created:
            policy.save(update_fields=["params", "hierarchy", "updated_at"])
        self.stdout.write(self.style.SUCCESS("Current ELM policy defaults are present; institute hierarchy remains explicitly unconfigured."))
