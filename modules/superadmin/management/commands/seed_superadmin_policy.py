from __future__ import annotations

from django.core.management.base import BaseCommand

from fusion_auth.client import IamSession
from fusion_auth.principal import Principal
from modules.superadmin.domain.constants import DEFAULT_POLICY_VALUES, PERMITTED_CONFIG_KEYS
from modules.superadmin.selectors.config import get_active_policy_param
from modules.superadmin.services.config import supersede_policy_param

_SEED_PERMS = frozenset(
    {
        "superadmin.policy.view",
        "superadmin.policy.change",
    }
)


def _seed_principal() -> Principal:
    # Synthetic principal for management-command audit attribution — no IAM call
    session = IamSession(
        user_id=0,
        username="seed_superadmin_policy",
        display_name="System Seed",
        kind="staff",
        active_role="super_admin",
        roles=("super_admin",),
        permissions=_SEED_PERMS,
        modules=("superadmin",),
    )
    return Principal.from_session(session)


class Command(BaseCommand):
    help = "Seed the initial SystemPolicyParameter rows using DEFAULT_POLICY_VALUES (idempotent)."

    def handle(self, *args, **options) -> None:
        principal = _seed_principal()
        seeded = 0
        skipped = 0
        for key in sorted(PERMITTED_CONFIG_KEYS):
            existing = get_active_policy_param(key)
            if existing is not None:
                self.stdout.write(
                    self.style.WARNING(f"  skip  {key} (already seeded at v{existing.version})")
                )
                skipped += 1
                continue
            default_value = DEFAULT_POLICY_VALUES[key]
            supersede_policy_param(
                principal,
                key=key,
                value=str(default_value),
                description="Initial system seed from DEFAULT_POLICY_VALUES.",
            )
            self.stdout.write(self.style.SUCCESS(f"  seeded {key} = {default_value}"))
            seeded += 1
        self.stdout.write(self.style.SUCCESS(f"Done: {seeded} seeded, {skipped} skipped."))
