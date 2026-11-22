"""Import explicitly approved HR policies via an authenticated IAM HR operator."""

import json
import os
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.api.exceptions import DomainError
from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.principal import Principal
from modules.hreis.models import HRPolicyVersion
from modules.hreis.services.policies import create_policy

_FIELDS = frozenset({"family", "version", "effective_from", "effective_until", "parameters"})


def _validated_policy(row):
    if not isinstance(row, dict) or set(row) != _FIELDS:
        raise CommandError(
            "Each policy must provide only family, version, effective_from, "
            "effective_until and parameters."
        )
    try:
        start = datetime.fromisoformat(row["effective_from"])
        end = (
            datetime.fromisoformat(row["effective_until"])
            if row["effective_until"] is not None
            else None
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError("Policy dates must be ISO-8601 values with timezones.") from exc
    return {**row, "effective_from": start, "effective_until": end}


def _operator(token_env):
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise CommandError(
            f"Set {token_env} to an authorized IAM token; never pass the token on the command line."
        )
    try:
        session = get_client().resolve_session(auth_token=token)
    except IamUnavailable as exc:
        raise CommandError("IAM is unavailable; no policy was imported.") from exc
    if session is None:
        raise CommandError("IAM rejected the operator token; no policy was imported.")
    actor = Principal.from_session(session)
    if not (
        actor.active_role == "hradmin"
        and actor.has_module("hreis")
        and actor.has_permission("hreis.policy.manage")
    ):
        raise CommandError("The authenticated active HR Administrator needs hreis.policy.manage.")
    return actor


def _policy_rows(policy_file):
    path = Path(policy_file)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError("Cannot read institutional policy JSON.") from exc
    rows = payload.get("policies") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise CommandError("The policy JSON must contain a nonempty policies list.")
    if len(rows) > 100:
        raise CommandError("Import at most 100 policy revisions per file.")
    return rows


class Command(BaseCommand):
    help = (
        "Import source-approved HR-EIS policy JSON using a live IAM HR "
        "administrator token in an environment variable; never invent defaults."
    )

    def add_arguments(self, parser):
        parser.add_argument("--policy-file", required=True)
        parser.add_argument(
            "--token-env",
            default="HREIS_OPERATOR_IAM_TOKEN",
            help="Environment variable holding the authenticated IAM token.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        actor = _operator(options["token_env"])
        rows = _policy_rows(options["policy_file"])
        created = 0
        for raw in rows:
            policy = _validated_policy(raw)
            existing = HRPolicyVersion.objects.filter(
                family=policy["family"],
                version=policy["version"],
            ).first()
            if existing is not None:
                if not all(
                    getattr(existing, name) == policy[name]
                    for name in ("effective_from", "effective_until", "parameters")
                ):
                    raise CommandError(
                        "Policy version already exists with different immutable fields."
                    )
                continue
            try:
                create_policy(
                    actor,
                    **policy,
                    idempotency_key=(
                        f"trusted-policy-import-{policy['family']}-{policy['version']}"
                    ),
                )
            except DomainError as exc:
                raise CommandError(
                    f"Cannot import policy {policy['family']} v{policy['version']}: {exc}"
                ) from exc
            created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"HR-EIS: {created} approved version(s) imported; "
                f"{len(rows) - created} identical version(s) already existed."
            )
        )
